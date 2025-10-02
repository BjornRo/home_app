from core import enums, types
from core.constants import SECURITY_TAG
from guards.guards import root_or_local_guard
from litestar import get
from litestar.controller import Controller
from middleware.middlewares import JWTAuthenticationMiddleware
from services.role_service import RoleService
from services.user_service import UserService


class RolesController(Controller):
    path = "/roles"
    tags = ["roles"]
    security = [SECURITY_TAG.access_token]
    guards = [root_or_local_guard]
    middleware = [JWTAuthenticationMiddleware]
    # exclude_from_auth=True

    @get(path="/")
    async def get_all_roles(self, role_service: RoleService) -> list[enums.UserRoles]:
        return role_service.get_all_roles()

    @get(path="/{role:str}/users")
    async def get_all_users_by_role(self, user_service: UserService, role: enums.UserRoles) -> list[types.UserID]:
        return await user_service.find_user_ids_by_role(role)
