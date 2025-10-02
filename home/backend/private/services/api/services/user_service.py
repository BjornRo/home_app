import asyncio
from typing import Unpack

import msgspec
from core import enums, exceptions, models, types
from storage.cache.valkeyCacheClient import ValkeyCacheClient
from storage.db.repositories.user_account_repository import (
    UserAccountRepository,
    UserColumnFetch,
    UserUpdateFields,
)
from storage.db.repositories.user_acl_repository import (
    UpdateUserServiceField,
    UserACLRepository,
)
from storage.db.repositories.user_profile_repository import (
    UserProfileRepository,
    UserProfileUpdateFields,
)
from storage.db.repositories.user_role_repository import UserRoleRepository
from utils import cache_helpers, helpers, validation

from appdata import shared  # type: ignore

__encode = msgspec.msgpack.Encoder().encode
__app_user_decode = msgspec.msgpack.Decoder(type=models.AppUser).decode


class UserService(msgspec.Struct):
    repo_account: UserAccountRepository
    repo_acl: UserACLRepository
    repo_profile: UserProfileRepository
    repo_role: UserRoleRepository
    cache_app: ValkeyCacheClient

    # region: User Operations
    async def get_user(self, method: UserColumnFetch, value):
        try:
            return await self.repo_account.get_user(method, value)
        except:
            return None

    async def get_all_user_data(self, user_id: types.UserID):
        """
        Raises:
            NotFoundError: if user does not exist
        """
        user, registration, profile, roles, services = await asyncio.gather(
            self.repo_account.get_user("user_id", user_id),
            self.repo_account.get_user_registration(user_id),
            self.repo_profile.get_user_profile(user_id),
            self.repo_role.get_user_roles(user_id),
            self.repo_acl.get_user_services(user_id),
        )

        return models.UserFullData(
            user_id=user_id,
            account=user,
            registration=registration,
            profile=profile,
            roles=roles,
            acl=services,
        )

    async def get_userdata_dto(self, user_id: types.UserID):
        """
        Raises:
            NotFoundError: if name or mail does not exist
        """
        user, registration, profile = await asyncio.gather(
            self.repo_account.get_user("user_id", user_id),
            self.repo_account.get_user_registration(user_id),
            self.repo_profile.get_user_profile(user_id),
        )
        return models.UserDataDTO(
            user_id=user_id,
            login_name=user.login_name,
            login_mail=user.login_mail,
            display_name=profile.display_name,
            created_at=registration.created_date,
        )

    async def get_appuser(self, user_id: types.UserID):
        versioned_key = await cache_helpers.get_version_key(self.cache_app, user_id)

        if cached := await self.cache_app.get(versioned_key):
            return __app_user_decode(cached)

        profile, roles, services = await asyncio.gather(
            self.repo_profile.get_user_profile(user_id),
            self.repo_role.get_user_valid_roles(user_id),
            self.repo_acl.get_user_valid_services(user_id),
        )

        app_user = models.AppUser(
            user_id=user_id,
            roles=roles,
            display_name=profile.display_name,
            services=services,
        )
        await self.cache_app.set(versioned_key, __encode(app_user))
        return app_user

    async def create_user(
        self,
        login_name: str,
        login_mail: str | None,
        password: str,
        enable: bool,
        created_by: types.UserID | None = None,
    ):
        """
        Raises:
            ValidationError: if value(s) given are invalid
            IntegrityError: if value already exists
        """
        validation.validate_password(password)
        validation.validate_name(login_name)
        if login_mail:
            validation.validate_mail(login_mail)

        password_hash = await helpers.hash_password_b64_threaded(password)
        return await self.repo_account.create_user(login_name, login_mail, password_hash, enable, created_by)

    async def search_user(
        self,
        name_or_email: str,
        limit: int | None,
        offset: int | None = None,
        exact_match=False,
    ):
        """
        Raises:
            UserInputError: if value(s) given are invalid
        """
        if limit is not None and limit <= 0:
            raise exceptions.UserInputError("Invalid limit given")
        if offset is not None and offset < 0:
            raise exceptions.UserInputError("Invalid offset given")

        return await self.repo_account.search_user(name_or_email, limit, offset, exact_match)

    async def set_user_enabled(self, user_id: types.UserID, enable: bool):
        return await self.repo_account.update_user_enabled(user_id, enable)

    async def update_user_login_date(self, user_id: types.UserID):
        return await self.repo_account.update_user_login_date(user_id)

    async def update_user(self, user_id: types.UserID, **fields: Unpack[UserUpdateFields]):
        """
        Raises:
            UserInputError: if no fields are supplied
            IntegrityError: if value already exists
            ValidationError: if value is invalid
        """
        if field := fields.get("login_mail"):
            validation.validate_mail(field)
        if field := fields.get("login_name"):
            validation.validate_name(field)
        if field := fields.get("password"):
            validation.validate_password(field)
            fields["password"] = await helpers.hash_password_b64_threaded(field)

        await self.repo_account.update_user(user_id, **fields)
        await cache_helpers.incr_version(self.cache_app, user_id=user_id)

    async def delete_user(self, user_id: types.UserID):
        await self.repo_account.delete_user(user_id)
        await cache_helpers.incr_version(self.cache_app, user_id=user_id)

    # endregion
    # region: Profile Operations
    async def update_user_profile(self, user_id: types.UserID, **fields: Unpack[UserProfileUpdateFields]):
        """
        Raises:
            UserInputError: if no fields are supplied
            IntegrityError: if value already exists
            ValidationError: if value is invalid
        """
        await self.repo_profile.update_user_profile(user_id, **fields)
        await cache_helpers.incr_version(self.cache_app, user_id=user_id)

    # endregion
    # region: Role Operations
    async def get_user_roles(self, user_id: types.UserID):
        return await self.repo_role.get_user_roles(user_id)

    async def get_user_valid_roles(self, user_id: types.UserID):
        return await self.repo_role.get_user_valid_roles(user_id)

    async def find_user_ids_by_role(self, role: enums.UserRoles):
        return await self.repo_role.find_user_ids_by_role(role)

    async def add_role(
        self,
        user_id: types.UserID,
        role: enums.UserRoles,
        valid_from: shared.DateTimeUTC | None,
        valid_to: shared.DateTimeUTC | None,
        given_by: types.UserID | None = None,
    ):
        """
        Raises:
            IntegrityError: if value already exists
        """
        await self.repo_role.insert_user_role(user_id, role, valid_from, valid_to, given_by)
        await cache_helpers.incr_version(self.cache_app, user_id=user_id)

    async def replace_role(
        self,
        user_id: types.UserID,
        old_role: enums.UserRoles,
        new_role: enums.UserRoles,
        given_by: types.UserID | None = None,
    ):
        """
        Raises:
            IntegrityError: if value already exists
        """
        await self.repo_role.replace_role(user_id, old_role, new_role, given_by)
        await cache_helpers.incr_version(self.cache_app, user_id=user_id)

    async def delete_role(self, user_id: types.UserID, role: enums.UserRoles):
        await self.repo_role.delete_role(user_id, role)
        await cache_helpers.incr_version(self.cache_app, user_id=user_id)

    # endregion
    # region: Acl

    async def get_user_acl(self, user_id: types.UserID):
        return await self.repo_acl.get_user_services(user_id)

    async def get_user_valid_acl(self, user_id: types.UserID):
        return await self.repo_acl.get_user_valid_services(user_id)

    async def find_user_ids_by_acl(self, service_name: str):
        return await self.repo_acl.find_user_ids_by_service(service_name)

    async def add_acl(
        self,
        user_id: types.UserID,
        service_name: str,
        rwx: types.RWX,
        valid_from: shared.DateTimeUTC | None,
        valid_to: shared.DateTimeUTC | None,
        given_by: types.UserID | None = None,
    ):
        """
        Raises:
            IntegrityError: if value already exists
        """
        await self.repo_acl.insert_service(user_id, service_name, rwx, valid_from, valid_to, given_by)
        await cache_helpers.incr_version(self.cache_app, user_id=user_id)

    async def update_acl(self, user_id: types.UserID, service_name: str, **fields: Unpack[UpdateUserServiceField]):
        """
        Raises:
            UserInputError
        """
        await self.repo_acl.update_user_service(user_id, service_name=service_name, **fields)
        await cache_helpers.incr_version(self.cache_app, user_id=user_id)

    async def delete_acl(self, user_id: types.UserID, service_name: str):
        await self.repo_acl.delete_service_from_user(user_id, service_name)
        await cache_helpers.incr_version(self.cache_app, user_id=user_id)

    # endregion
    # region: Views
    async def get_alluserview(self, limit=10, offset=0, asc=True):
        if limit <= 0:
            raise exceptions.UserInputError("Invalid limit given")
        if offset < 0:
            raise exceptions.UserInputError("Invalid offset given")
        return await self.repo_account.get_alluserview(limit, offset, asc)

    # endregion
