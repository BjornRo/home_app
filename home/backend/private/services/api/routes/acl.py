import msgspec
from core import exceptions, types
from core.constants import SECURITY_TAG
from guards import guards
from litestar import delete, get, patch, post
from litestar.controller import Controller
from litestar.exceptions import ClientException
from services.acl_service import AclService
from services.user_service import UserService
from storage.db import tables
from storage.db.repositories.user_acl_repository import UpdateServiceFields


class RegisterServicePayload(msgspec.Struct):
    service_name: str
    url: str | None
    description: str


class AclController(Controller):
    path = "/acl"
    tags = ["acl"]
    security = [SECURITY_TAG.access_token]
    guards = [guards.root_or_local_jwt_guard]
    # middleware = [JWTAuthenticationMiddleware]
    # exclude_from_auth=True

    @get(path="/")
    async def get_all_services(self, acl_service: AclService) -> list[tables.Service]:
        return await acl_service.get_all_services()

    @get(path="/service_names")
    async def get_all_service_names(self, acl_service: AclService) -> list[str]:
        return await acl_service.get_all_service_names()

    @get(path="/{service_name:str}")
    async def get_service(self, acl_service: AclService, service_name: str) -> tables.Service | None:
        return await acl_service.get_service(service_name=service_name)

    @get(path="/{service_name:str}/users")
    async def get_all_users_by_service(self, user_service: UserService, service_name: str) -> list[types.UserID]:
        return await user_service.find_user_ids_by_acl(service_name=service_name)

    @post(path="/")
    async def register_service(self, acl_service: AclService, data: RegisterServicePayload) -> None:
        await acl_service.register_service(
            service_name=data.service_name,
            url=data.url,
            description=data.description,
        )

    @patch(path="/{service_name:str}")
    async def update_service(self, acl_service: AclService, service_name: str, data: UpdateServiceFields) -> None:
        try:
            await acl_service.update_service(service_name=service_name, **data)
        except exceptions.UserInputError as e:
            raise ClientException(str(e)) from e
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e)) from e

    @delete(path="/{service_name:str}")
    async def unregister_service(self, acl_service: AclService, service_name: str) -> None:
        await acl_service.unregister_service(service_name=service_name)
