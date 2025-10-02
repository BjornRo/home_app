from typing import Unpack

import msgspec
from storage.db.repositories.user_acl_repository import (
    UpdateServiceFields,
    UserACLRepository,
)


class AclService(msgspec.Struct):
    repo_acl: UserACLRepository

    async def register_service(self, service_name: str, url: str | None, description: str):
        """
        Does not raise. If conflict it ignores.
        """
        await self.repo_acl.register_service(service_name, url=url, description=description)

    async def unregister_service(self, service_name: str):
        await self.repo_acl.unregister_service(service_name)

    async def update_service(self, service_name: str, **fields: Unpack[UpdateServiceFields]):
        """
        Raises:
            UserInputError: No fields given
            IntegrityError
        """
        await self.repo_acl.update_service(service_name=service_name, **fields)

    async def get_service(self, service_name: str):
        return await self.repo_acl.get_service(service_name=service_name)

    async def get_all_services(self):
        return await self.repo_acl.get_all_services()

    async def get_all_service_names(self):
        return await self.repo_acl.get_all_service_names()
