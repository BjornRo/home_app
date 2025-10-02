import asyncio

from core import paths, settings
from litestar import Litestar
from services.acl_service import AclService
from services.auth_service import AuthService
from services.ban_service import BanService
from services.meta_service import MetaService
from services.registration_service import RegistrationService
from services.role_service import RoleService
from services.token_service import TokenService
from services.user_service import UserService
from storage.cache.valkeyCacheClient import ValkeyCacheClient
from storage.db.repositories.user_account_repository import UserAccountRepository
from storage.db.repositories.user_acl_repository import UserACLRepository
from storage.db.repositories.user_ban_repository import UserBanRepository
from storage.db.repositories.user_meta_repository import UserMetaRepository
from storage.db.repositories.user_profile_repository import UserProfileRepository
from storage.db.repositories.user_role_repository import UserRoleRepository
from storage.db.sql.sqlite import SQLite
from valkey.asyncio import Valkey

from appdata import shared  # type: ignore

__db_app_client = SQLite(dbfile=paths.DATA_PATH + paths.DB_APP, pool_size=10)
__cache_app_client = Valkey(unix_socket_path="/mem/cache_app")  # Used as an attribute
__cache_api_client = Valkey(unix_socket_path="/mem/cache_api")  # Used as an attribute
__cache_online_users_counter_client = Valkey(unix_socket_path="/mem/cache_data", db=1)  # Used as an attribute
__cache_data_client = shared.ValkeyBasic(unix_socket_path="/mem/cache_data")

# Repositories
__repo_account = UserAccountRepository(__db_app_client)
__repo_acl = UserACLRepository(__db_app_client)
__repo_ban = UserBanRepository(__db_app_client)
__repo_meta = UserMetaRepository(__db_app_client, __cache_online_users_counter_client)
__repo_profile = UserProfileRepository(__db_app_client)
__repo_role = UserRoleRepository(__db_app_client)

_cache_app = ValkeyCacheClient(__cache_app_client, prefix="app", default_ttl=settings.CACHE_DEFAULT_EXPIRY)
_cache_token = ValkeyCacheClient(__cache_app_client, prefix="tok", default_ttl=settings.CACHE_DEFAULT_EXPIRY)


def get_api_cache_client() -> Valkey:
    return __cache_api_client


async def provide_data_cache() -> shared.ValkeyBasic:
    return __cache_data_client


async def start(app: Litestar):
    pass


async def close():
    await asyncio.gather(
        __db_app_client.close(),
        __cache_app_client.aclose(),
        __cache_data_client.aclose(),
        __cache_api_client.aclose(),
        __cache_online_users_counter_client.aclose(),
    )


async def provide_acl_service() -> AclService:
    return AclService(repo_acl=__repo_acl)


async def provide_auth_service() -> AuthService:
    return AuthService(user_service=await provide_user_service(), repo_ban=__repo_ban)


async def provide_ban_service() -> BanService:
    return BanService(token_service=await provide_token_service(), repo_ban=__repo_ban)


async def provide_meta_service() -> MetaService:
    return MetaService(repo_meta=__repo_meta)


async def provide_registration_service() -> RegistrationService:
    return RegistrationService(user_service=await provide_user_service(), repo_meta=__repo_meta)


async def provide_role_service() -> RoleService:
    return RoleService(repo_role=__repo_role)


async def provide_token_service() -> TokenService:
    return TokenService(
        user_service=await provide_user_service(),
        repo_meta=__repo_meta,
        cache_token=_cache_token,
        cache_online_users=__cache_online_users_counter_client,
    )


async def provide_user_service() -> UserService:
    return UserService(
        repo_account=__repo_account,
        repo_acl=__repo_acl,
        repo_profile=__repo_profile,
        repo_role=__repo_role,
        cache_app=_cache_app,
    )
