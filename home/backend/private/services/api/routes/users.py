from typing import Annotated, Any, TypedDict

import msgspec
from core import enums, exceptions, models, types
from core.constants import SECURITY_TAG
from guards.guards import root_guard, root_or_local_guard, self_userid_or_root_guard
from litestar import Request, delete, get, patch, post
from litestar.controller import Controller
from litestar.exceptions import (
    ClientException,
    InternalServerException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from litestar.params import Parameter
from middleware.middlewares import JWTAuthenticationMiddleware
from services.user_service import UserProfileUpdateFields, UserService, UserUpdateFields
from storage.db import tables
from typing_extensions import Annotated
from utils import time_helpers


def cache_key_builder(request: Request) -> str:
    return request.url.path + request.headers.get("Authorization", "")




class ACLPayload(msgspec.Struct):
    service_name: str
    rwx: Annotated[int, Parameter(ge=0, le=7, description="Value as Linux RWX value 0-7")]
    valid_from_date: types.DateTimeStr | types.Unixtime | None
    valid_to_date: types.DateTimeStr | types.Unixtime | None


class RolePayload(msgspec.Struct):
    role: enums.UserRoles
    valid_from_date: types.DateTimeStr | types.Unixtime | None
    valid_to_date: types.DateTimeStr | types.Unixtime | None


class ReplaceRolePayload(msgspec.Struct):
    old_role: enums.UserRoles
    new_role: enums.UserRoles


class UpdateUserServiceFieldPayload(TypedDict, total=False):
    rwx: Annotated[int, Parameter(ge=0, le=7, description="Value as Linux RWX value 0-7")]
    valid_from_date: types.DateTimeStr | types.Unixtime | None
    valid_to_date: types.DateTimeStr | types.Unixtime | None


class CreateUser(msgspec.Struct):
    name: str
    mail: str | None
    password: str


class UserController(Controller):
    path = "/users"
    tags = ["users"]
    security = [SECURITY_TAG.access_token]
    guards = [root_or_local_guard]
    middleware = [JWTAuthenticationMiddleware]
    # exclude_from_auth=True

    @post(
        path="/",
        guards=[root_guard],
        status_code=200,
        description="Returns [user_id] of created user",
        raises=[ValidationException, types.AlreadyExists],
    )
    async def create_user(
        self,
        request: types.AuthRequest,
        user_service: UserService,
        data: CreateUser,
    ) -> types.UserID:
        try:
            return await user_service.create_user(
                login_name=data.name,
                login_mail=data.mail,
                password=data.password,
                enable=True,
                created_by=request.user.user_id,
            )
        except exceptions.ValidationError as e:
            raise ValidationException(str(e))
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e))

    @get(
        path="/{user_id:str}",
        raises=[NotFoundException],
        cache=True,
        cache_key_builder=cache_key_builder,
        guards=[self_userid_or_root_guard],
    )
    async def get_user_dto(self, user_service: UserService, user_id: str) -> models.UserDataDTO:
        try:
            return await user_service.get_userdata_dto(user_id)
        except exceptions.NotFoundError:
            raise NotFoundException

    @get(
        path="/",
        guards=[root_guard],
        description="Use of [query], changes to search mode for login_name or login_mail",
    )
    async def all_users(
        self,
        user_service: UserService,
        limit: int = 10,
        offset: int = 0,
        asc: bool = True,
        query: str | None = None,  # Search for username
    ) -> list[models.AllUserView]:
        if query:
            return await user_service.search_user(query, limit=limit, offset=offset)
        return await user_service.get_alluserview(limit=limit, offset=offset, asc=asc)

    @patch(
        path="/{user_id:str}/account",
        raises=[ClientException, types.AlreadyExists, ValidationException],
        guards=[self_userid_or_root_guard],
    )
    async def update_user_account(self, user_service: UserService, user_id: str, data: UserUpdateFields) -> None:
        try:
            await user_service.update_user(user_id, **data)
        except exceptions.UserInputError as e:
            raise ClientException(str(e))
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e))
        except exceptions.ValidationError as e:
            raise ValidationException(str(e))

    @patch(
        path="/{user_id:str}/profile",
        raises=[ClientException, types.AlreadyExists, ValidationException],
        guards=[self_userid_or_root_guard],
    )
    async def update_user_profile(self, user_service: UserService, user_id: str, data: UserProfileUpdateFields) -> None:
        try:
            await user_service.update_user_profile(user_id, **data)
        except exceptions.UserInputError as e:
            raise ClientException(str(e))
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e))
        except exceptions.ValidationError as e:
            raise ValidationException(str(e))

    @delete(
        path="/{user_id:str}",
        raises=[ClientException, types.AlreadyExists, ValidationException],
        guards=[self_userid_or_root_guard],
    )
    async def delete_user(self, user_service: UserService, user_id: str) -> None:
        await user_service.delete_user(user_id)

    @get(path="/me")
    async def get_me(self, request: types.AuthRequest, user_service: UserService) -> models.UserDataDTO:
        return await user_service.get_userdata_dto(request.user.user_id)

    # region: Roles

    @get(path="/{user_id:str}/roles", guards=[root_guard])
    async def get_user_roles(self, user_service: UserService, user_id: str) -> list[tables.Has_Role]:
        return await user_service.get_user_roles(user_id=user_id)

    @get(path="/{user_id:str}/valid_roles", guards=[root_guard])
    async def get_user_valid_roles(self, user_service: UserService, user_id: str) -> list[enums.UserRoles]:
        return await user_service.get_user_valid_roles(user_id=user_id)

    @post(
        path="/{user_id:str}/roles",
        guards=[root_guard],
        raises=[ValidationException, types.AlreadyExists],
        description="Dates can be int for unixtimestamps",
    )
    async def give_user_role(
        self,
        request: types.AuthRequest,
        user_service: UserService,
        user_id: str,
        data: RolePayload,
    ) -> None:
        try:
            await user_service.add_role(
                user_id=user_id,
                role=data.role,
                valid_from=time_helpers.parse_date(data.valid_from_date),
                valid_to=time_helpers.parse_date(data.valid_to_date),
                given_by=request.user.user_id,
            )
        except ValueError as e:
            raise ValidationException(str(e))
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e))

    @patch(
        path="/{user_id:str}/roles",
        guards=[root_guard],
        raises=[types.AlreadyExists],
    )
    async def replace_user_role(
        self,
        request: types.AuthRequest,
        user_service: UserService,
        user_id: str,
        data: ReplaceRolePayload,
    ) -> None:
        try:
            await user_service.replace_role(
                user_id=user_id,
                old_role=data.old_role,
                new_role=data.new_role,
                given_by=request.user.user_id,
            )
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e))

    @delete(
        path="/{user_id:str}/roles/{role:str}",
        guards=[root_guard],
        raises=[PermissionDeniedException],
    )
    async def delete_user_role(
        self,
        user_service: UserService,
        user_id: str,
        role: enums.UserRoles,
    ) -> None:
        if role == enums.UserRoles.ROOT:
            raise PermissionDeniedException("Not allowed to delete root role here")
        await user_service.delete_role(user_id, role)

    # endregion
    # region: Acl

    @get(path="/{user_id:str}/acl", guards=[root_guard])
    async def get_user_services(self, user_service: UserService, user_id: str) -> list[tables.Has_Service]:
        return await user_service.get_user_acl(user_id=user_id)

    @get(path="/{user_id:str}/valid_acl", guards=[root_guard])
    async def get_user_valid_services(self, user_service: UserService, user_id: str) -> models.AppUserACL:
        return await user_service.get_user_valid_acl(user_id=user_id)

    @post(
        path="/{user_id:str}/acl",
        guards=[root_guard],
        raises=[ValidationException, types.AlreadyExists],
        description="Dates can be int for unixtimestamps",
    )
    async def give_user_acl(
        self,
        request: types.AuthRequest,
        user_service: UserService,
        user_id: str,
        data: ACLPayload,
    ) -> None:
        try:
            await user_service.add_acl(
                user_id=user_id,
                service_name=data.service_name,
                rwx=types.RWX.from_int(data.rwx),
                valid_from=time_helpers.parse_date(data.valid_from_date),
                valid_to=time_helpers.parse_date(data.valid_to_date),
                given_by=request.user.user_id,
            )
        except ValueError as e:
            raise ValidationException(str(e))
        except exceptions.IntegrityError as e:
            raise types.AlreadyExists(str(e))

    @patch(path="/{user_id:str}/acl/{service_name:str}")
    async def update_user_acl(
        self,
        user_service: UserService,
        user_id: types.UserID,
        service_name: str,
        data: UpdateUserServiceFieldPayload,
    ) -> None:

        new_data: dict[str, Any] = {}
        if value := data.get("rwx"):
            new_data["rwx"] = types.RWX.from_int(value)
        if value := data.get("valid_to_date"):
            new_data["valid_to"] = time_helpers.parse_date(value)
        if value := data.get("valid_from_date"):
            new_data["valid_from"] = time_helpers.parse_date(value)

        await user_service.update_acl(user_id=user_id, service_name=service_name, **new_data)

    @delete(
        path="/{user_id:str}/acl/{service_name:str}",
        guards=[root_guard],
        raises=[PermissionDeniedException],
    )
    async def delete_user_acl(
        self,
        user_service: UserService,
        user_id: str,
        service_name: str,
    ) -> None:
        await user_service.delete_acl(user_id, service_name)

    # endregion


# class ReturnUserDTO(MsgspecDTO[tables.User]):
#     config = DTOConfig(
#         exclude={
#             "login.pwd",
#             "acl",
#         }
#     )


# class ReturnAllUserViewDTO(MsgspecDTO[models.AllUserView]):
#     config = DTOConfig(
#         exclude={
#             "login.pwd",
#         }
#     )


# class ACLPayload(TypedDict):
#     start_date: NotRequired[str]
#     end_date: NotRequired[str]
#     rwx: Annotated[int, Parameter(ge=0, le=7, description="Value as Linux RWX value 0-7")]
