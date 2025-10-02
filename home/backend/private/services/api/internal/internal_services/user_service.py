import asyncio
from typing import Unpack

import msgspec
from internal import internal_models
from internal.storage.repositories.internal_user_repository import (
    InternalUserRepository,
)
from storage.cache.valkeyCacheClient import ValkeyCacheClient
from utils import cache_helpers

from appdata import internal_shared  # type: ignore

__encode = msgspec.msgpack.Encoder().encode
__app_user_decode = msgspec.msgpack.Decoder(type=internal_models.InternalAppUser).decode


class InternalUserService(msgspec.Struct):
    repo_user: InternalUserRepository
    cache_app: ValkeyCacheClient

    # region: User Operations
    async def create_user(self, username: str, pwd: str, enabled: bool):
        """
        Raises:
            IntegrityError
            ValidationError
        """
        await self.repo_user.create_user(username, pwd, enabled)

    async def get_appuser(self, username: str):
        versioned_key = await cache_helpers.get_version_key(self.cache_app, username)

        if cached := await self.cache_app.get(versioned_key):
            return __app_user_decode(cached)

        if user := await self.repo_user.get_all_user_view(username):
            await self.cache_app.set(versioned_key, __encode(user))
            return internal_models.InternalAppUser(
                user_id=user.user_id,
                roles=user.roles,
                services=user.services,
            )

    async def get_users(self):
        return await self.repo_user.get_users()

    async def get_user_auth(self, username: str):
        if user := await self.repo_user.get_user(username):
            if user.enabled:
                return user

    async def search_user(self, search_term: str):
        return await self.repo_user.search_user(search_term)

    async def get_all_users_view(self):
        return await self.repo_user.get_all_users_view()

    async def get_all_user_view(self, username: str):
        return await self.repo_user.get_all_user_view(username)

    async def update_user(self, username: str, **fields: Unpack[internal_models.InternalUserUpdate]):
        await self.repo_user.update_user(username, **fields)
        await cache_helpers.incr_version(self.cache_app, username)

    async def delete_user(self, username: str):
        await self.repo_user.delete_user(username)
        await cache_helpers.incr_version(self.cache_app, username)

    # endregion
    # region: User Meta Operations

    async def get_user_has_roles(self, username: str):
        return await self.repo_user.get_user_has_roles(username)

    async def get_user_roles(self, username: str):
        return await self.repo_user.get_user_roles(username)

    async def insert_user_role(self, username: str, role: internal_shared.InternalRolesEnum):
        await self.repo_user.insert_role(username, role)
        await cache_helpers.incr_version(self.cache_app, username)

    async def delete_user_role(self, username: str, role: internal_shared.InternalRolesEnum):
        await self.repo_user.delete_role(username, role)
        await cache_helpers.incr_version(self.cache_app, username)

    # endregion
    # region: Services

    async def get_user_serving_service(self, username: str):
        return await self.repo_user.get_serving_service(username)

    async def insert_user_service_serving(self, username: str, service_name: str):
        """
        Raises:
            IntegrityError
            NotFoundError
        """
        await self.repo_user.insert_service_serving(username, service_name)
        await cache_helpers.incr_version(self.cache_app, username)

    async def delete_user_service_serving(self, username: str, service_name: str):
        await self.repo_user.delete_service_serving(username, service_name)
        await cache_helpers.incr_version(self.cache_app, username)

    # endregion
