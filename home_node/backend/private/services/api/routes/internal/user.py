import db.internal.queries as internal_queries
from db.internal.models import (
    InternalRolesEnum,
    InternalUserAPIRegistration,
    InternalUserUpdate,
)
from db.strategy.surreal import TableInternal
from litestar import delete, patch, post
from litestar.controller import Controller
from litestar.exceptions import NotFoundException, PermissionDeniedException
from modules.guards import root_guard
from modules.myjwt import AuthRequest, jwt_middleware
from utils import hash_password_b64


class InternalUserController(Controller):
    path = "/user"
    tags = ["internal_user"]
    middleware = [jwt_middleware]
    guards = [root_guard]

    @post(path="/", status_code=201, raises=[PermissionDeniedException])
    async def create(self, request: AuthRequest, data: InternalUserAPIRegistration) -> None:
        # appuser = request.user
        user_id = request.auth["sub"]
        if not await internal_queries.insert_internal_user(
            name=data["name"],
            hash_b64_pwd=await hash_password_b64(data["pwd"]),
            created_by_user_id=f"{TableInternal.USER}:{user_id}",
            enabled=data["enabled"],
        ):
            raise PermissionDeniedException("Could not insert user")

    @patch(path="/{name_or_user_id:str}", status_code=201, raises=[NotFoundException])
    async def update(self, name_or_user_id: str, data: InternalUserUpdate) -> None:
        if not await internal_queries.update_internal_user(name_or_user_id, data):
            raise NotFoundException("User does not exist")

    @delete(path="/{name_or_user_id:str}", status_code=201, raises=[NotFoundException])
    async def delete(self, name_or_user_id: str) -> None:
        if not await internal_queries.delete_internal_user(name_or_user_id):
            raise NotFoundException("User does not exist")

    @post(path="/{name_or_user_id:str}/addrole/{role_name:str}", status_code=201, raises=[PermissionDeniedException])
    async def insert_role(self, request: AuthRequest, name_or_user_id: str, role_name: str) -> None:
        try:
            role = InternalRolesEnum(role_name)
        except:
            raise PermissionDeniedException("Invalid role")

        user_id = request.auth["sub"]
        if not await internal_queries.insert_internal_userrole(name_or_user_id, role, given_by_user_id=user_id):
            raise PermissionDeniedException("Role exists for user or user does not exist")
