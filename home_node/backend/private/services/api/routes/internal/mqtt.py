from typing import TypedDict

import db.internal.queries as internal_queries
from constants import DEFAULT_SECURITY_TAG as SECTAG
from db.internal.models import InternalRolesEnum
from litestar import post
from litestar.controller import Controller
from litestar.exceptions import NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler
from utils import check_password_b64

from ._utils import InternalAuthConnection, api_guard, jwt_internal_middleware

"""
Handles MQTT authentication requests

Instead of using password file, we can centralize authentication and authorization

ACL not implemented.
"""


def mqtt_guard(connection: InternalAuthConnection, _: BaseRouteHandler) -> None:
    try:
        if connection.user[1].has_role(InternalRolesEnum.MQTT):
            return None
    except:
        pass
    raise NotAuthorizedException


class UserAuth(TypedDict):
    clientid: str
    username: str
    password: str


class MQTTResp(TypedDict):
    Ok: bool
    Error: str


class InternalMqttAuthController(Controller):
    path = "/mqtt"
    tags = ["internal_mqtt"]
    security = SECTAG
    middleware = [jwt_internal_middleware]
    guards = [mqtt_guard, api_guard]
    _ok_resp = MQTTResp(Ok=True, Error="")
    _err_resp = MQTTResp(Ok=False, Error="-")

    @post(
        path=["/auth_jwt", "/auth_jwt/{path:path}"],
        description="If messenger is not eligible for accessing this, not authorized. Else result is the user challenge.",
    )
    async def auth_jwt(self, data: UserAuth, path: str | None = None) -> MQTTResp:
        if path:
            if len(path) > 30:
                return self._err_resp
            roles = InternalRolesEnum.convert(path[1:].lower().split("/", maxsplit=3))
            if len(roles) >= 3:
                return self._err_resp
        else:
            roles = ()

        if user_creds := await internal_queries.get_internal_userlogin(data["username"]):
            user_id, user_data = user_creds
            if await check_password_b64(data["password"], user_data["pwd"]) and user_data["enabled"]:
                if not roles:
                    return self._ok_resp
                user = await internal_queries.get_internal_userroles(user_id)
                if user.has_all_roles(roles):
                    return self._ok_resp
        else:
            # Check password to stop timing attacks
            await check_password_b64(data["password"], None)

        return self._err_resp

    @post(path="/acl_jwt", status_code=200, description="Always allows")
    async def acl_jwt(self) -> MQTTResp:
        return self._ok_resp


"""
class Access(IntEnum):
    READ = 1
    WRITE = 2
    READWRITE = 3
    SUBSCRIBE = 4
class UserAcl(BaseModel):
    clientid: str
    acc: Access
    topic: str
    username: str
"""
