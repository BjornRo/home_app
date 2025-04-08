import db.queries as queries
import modules.myjwt as myjwt
from db.models import UserACL
from litestar import post
from litestar.controller import Controller
from litestar.exceptions import PermissionDeniedException
from msgspec import Struct

from ._utils import InternalAuthRequest, api_guard, jwt_internal_middleware

type Resource = str
type ReadWriteExecute = int
type ResourceRWX = dict[Resource, ReadWriteExecute]


def get_rwx(acl_list: list[UserACL], acl_name: Resource) -> int:
    for acl in acl_list:
        if acl.resource == acl_name:
            return acl.rwx
    return 0


class ACLRequest(Struct):
    token: str
    acl: list[UserACL]


class InternalACLController(Controller):
    path = "/acl"
    tags = ["internal_acl"]
    guards = [api_guard]
    middleware = [jwt_internal_middleware]

    @post(
        path="/verify",
        description="Return std-rwx-linux for AppUser, 0 means no access. Raises 403 if user token is invalid",
        raises=[PermissionDeniedException],
    )
    async def verify_app_user(self, acl_request: ACLRequest, request: InternalAuthRequest) -> ResourceRWX:
        # user_id = request.user
        # roles = request.auth
        if token := await myjwt.validate(token_str=acl_request.token, access_token=True):
            resp = await queries.get_user_acl(token["sub"])
            return {acl.resource: get_rwx(resp, acl.resource) for acl in acl_request.acl}
        raise PermissionDeniedException("Invalid user token")
