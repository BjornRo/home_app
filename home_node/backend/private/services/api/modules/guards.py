from litestar.connection import ASGIConnection
from litestar.exceptions import PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler
from utils import is_local_request

from .myjwt import AuthConnection, jwt_auth_req

type ConnType = AuthConnection | ASGIConnection


def root_guard(connection: ConnType, _: BaseRouteHandler) -> None:
    try:
        if connection.user.is_root:
            return None
    except:
        pass
    raise PermissionDeniedException


def mod_guard(connection: ConnType, _: BaseRouteHandler) -> None:
    try:
        if connection.user.is_mod or connection.user.is_root:
            return None
    except:
        pass
    raise PermissionDeniedException


def local_access_guard(connection: AuthConnection, _: BaseRouteHandler) -> None:
    if not is_local_request(connection):
        raise PermissionDeniedException


def root_or_local_guard(connection: ConnType, _: BaseRouteHandler) -> None:
    if is_local_request(connection):
        return None
    try:
        if connection.user.is_root:
            return None
    except:
        pass
    raise PermissionDeniedException


async def root_or_local_jwt_guard(connection: ASGIConnection, br: BaseRouteHandler) -> None:
    if is_local_request(connection):
        return None
    return await root_api_jwt_guard(connection, br)


async def root_api_jwt_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    if (res := await jwt_auth_req(connection)) and res[0].is_root:
        return None
    raise PermissionDeniedException
