import msgspec
from core import exceptions, types
from internal import internal_models
from internal.internal_services.token_service import InternalTokenService
from internal.internal_services.user_service import InternalUserService
from internal.storage import internal_tables
from litestar import delete, get, patch, post
from litestar.controller import Controller
from litestar.exceptions import (
    ClientException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from services.acl_service import AclService

from appdata import internal_shared  # type: ignore

# rate_limit = RateLimitConfig(rate_limit=("minute", 3), store="valkey_store")


class AdminController(Controller):
    path = "/admin"
    tags = ["internal_admin"]

    @post(path="/", raises=[ValidationException, types.AlreadyExists])
    async def create_user(
        self,
        internal_user_service: InternalUserService,
        data: internal_tables.User,
    ) -> None:
        try:
            await internal_user_service.create_user(**msgspec.to_builtins(data))
        except exceptions.ValidationError as e:
            raise ValidationException(str(e)) from e
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e)) from e

    @get(path="/")
    async def get_users(self, internal_user_service: InternalUserService) -> list[internal_tables.User]:
        return await internal_user_service.get_users()

    @get(path="/all_users", cache=60)
    async def get_users_view(
        self,
        internal_user_service: InternalUserService,
        search: str | None = None,
    ) -> list[internal_models.AllUserView]:
        if search:
            return await internal_user_service.search_user(search)
        return await internal_user_service.get_all_users_view()

    @get(path="/{username:str}")
    async def get_user_view(
        self,
        internal_user_service: InternalUserService,
        username: str,
    ) -> internal_models.AllUserView | None:
        return await internal_user_service.get_all_user_view(username)

    @get(path="/{username:str}/app")
    async def get_appuser(
        self,
        internal_user_service: InternalUserService,
        username: str,
    ) -> internal_models.InternalAppUser | None:
        return await internal_user_service.get_appuser(username)

    @get(path="/{username:str}/logout")
    async def force_logout_user(self, internal_token_service: InternalTokenService, username: str) -> None:
        await internal_token_service.revoke_tokens(username)

    @get(path="/{username:str}/auth")
    async def get_user(self, internal_user_service: InternalUserService, username: str) -> internal_tables.User | None:
        return await internal_user_service.get_user_auth(username)

    @get(path="/{username:str}/serving")
    async def get_user_serving(self, internal_user_service: InternalUserService, username: str) -> list[str]:
        return await internal_user_service.get_user_serving_service(username)

    @get(path="/{username:str}/role")
    async def get_user_roles(
        self,
        internal_user_service: InternalUserService,
        username: str,
    ) -> list[internal_tables.Has_Role]:
        return await internal_user_service.get_user_has_roles(username)

    @post(path="/{username:str}/role/{role:str}", raises=[types.AlreadyExists])
    async def insert_user_role(
        self,
        internal_user_service: InternalUserService,
        username: str,
        role: internal_shared.InternalRolesEnum,
    ) -> None:
        try:
            await internal_user_service.insert_user_role(username, role)
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e)) from e

    @post(path="/{username:str}/serving/{service_name:str}", raises=[PermissionDeniedException, types.AlreadyExists])
    async def insert_user_service_serving(
        self,
        internal_user_service: InternalUserService,
        username: str,
        service_name: str,
    ) -> None:
        try:
            await internal_user_service.insert_user_service_serving(username, service_name)
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e)) from e
        except exceptions.NotFoundError as e:
            raise NotFoundException(str(e)) from e

    @patch(path="/{username:str}", raises=[ValidationException, types.AlreadyExists, ClientException])
    async def update_user(
        self,
        internal_user_service: InternalUserService,
        internal_token_service: InternalTokenService,
        username: str,
        data: internal_models.InternalUserUpdate,
    ) -> None:
        try:
            await internal_user_service.update_user(username, **data)
            if (enabled := data.get("enabled")) is not None and not enabled:
                await internal_token_service.revoke_tokens(username)
        except exceptions.ValidationError as e:
            raise ValidationException(str(e)) from e
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e)) from e
        except exceptions.UserInputError as e:
            raise ClientException(str(e)) from e

    @delete(path="/{user_id:str}")
    async def delete_user(
        self,
        internal_user_service: InternalUserService,
        username: str,
    ) -> None:
        await internal_user_service.delete_user(username)

    @delete(path="/{username:str}/role/{role:str}")
    async def delete_role(
        self,
        internal_user_service: InternalUserService,
        username: str,
        role: internal_shared.InternalRolesEnum,
    ) -> None:
        await internal_user_service.delete_user_role(username, role)

    @delete(path="/{username:str}/serving/{service_name:str}")
    async def delete_service_serving(
        self,
        internal_user_service: InternalUserService,
        username: str,
        service_name: str,
    ) -> None:
        await internal_user_service.delete_user_service_serving(username, service_name)
