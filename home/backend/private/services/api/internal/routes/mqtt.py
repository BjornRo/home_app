from typing import TypedDict

from internal import internal_types
from internal.internal_services.user_service import InternalUserService
from litestar import post
from litestar.controller import Controller
from litestar.exceptions import NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler
from utils import helpers

from appdata import internal_shared, shared  # type: ignore

"""
Handles MQTT authentication requests

Instead of using password file, we can centralize authentication and authorization

ACL not implemented.
"""


def mqtt_guard(connection: internal_types.InternalAuthConnection, _: BaseRouteHandler) -> None:
    try:
        required_roles = (
            internal_shared.InternalRolesEnum.MQTT,
            internal_shared.InternalRolesEnum.API,
        )
        if connection.user.has_all_roles(required_roles):
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


__ok_resp = MQTTResp(Ok=True, Error="")
__err_resp = MQTTResp(Ok=False, Error="-")


class InternalMqttAuthController(Controller):
    path = "/mqtt"
    tags = ["internal_mqtt"]
    guards = [mqtt_guard]

    @post(
        path=["/", "/{path:path}"],
        description="If messenger is not eligible for accessing this, not authorized. Else result is the user challenge.",
    )
    async def auth(
        self,
        internal_user_service: InternalUserService,
        data: UserAuth,
        path: str | None = None,
    ) -> MQTTResp:
        if path:
            if len(path) > 30:
                return __err_resp
            roles = internal_shared.InternalRolesEnum.convert(path[1:].lower().split("/", maxsplit=3))
            if len(roles) >= 3:
                return __err_resp
        else:
            roles = ()

        if user := await internal_user_service.get_user_auth(data["username"]):
            if await helpers.check_password_b64_threaded(data["password"], user.pwd):
                user_roles = shared.UserRolesBaseStruct[internal_shared.InternalRolesEnum](
                    roles=await internal_user_service.get_user_roles(user.user_id)
                )
                if user_roles.has_all_roles(roles):
                    return __ok_resp
        else:
            await helpers.check_password_b64_threaded(data["password"], None)

        return __err_resp

    @post(path="/acl_jwt", status_code=200, description="Always allows")
    async def acl_jwt(self) -> MQTTResp:
        return __ok_resp


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
