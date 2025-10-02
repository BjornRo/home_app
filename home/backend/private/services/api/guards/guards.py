from core import types
from litestar.connection import ASGIConnection
from litestar.exceptions import PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler
from services.token_service import TokenService
from utils import http_helpers

type ConnType = types.AuthConnection | ASGIConnection


def disabled_guard(connection: ConnType, _: BaseRouteHandler) -> None:
    raise PermissionDeniedException


def self_userid_or_root_guard(connection: ConnType, br: BaseRouteHandler) -> None:
    """Checks self user_id if it is equal to authed user user_id"""
    try:
        if connection.path_params["user_id"] == connection.user.user_id:
            return None
        elif connection.user.is_root:
            return None
    except:
        pass
    raise PermissionDeniedException


# Middleware hydrates user if it is logged in, otherwise it is None
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


def local_access_guard(connection: types.AuthConnection, _: BaseRouteHandler) -> None:
    if not http_helpers.is_local_request(connection):
        raise PermissionDeniedException


def root_or_local_guard(connection: ConnType, _: BaseRouteHandler) -> None:
    if http_helpers.is_local_request(connection):
        return None
    try:
        if connection.user.is_root:
            return None
    except:
        pass
    raise PermissionDeniedException


async def root_or_local_jwt_guard(connection: ASGIConnection, br: BaseRouteHandler) -> None:
    if http_helpers.is_local_request(connection):
        return None
    return await root_api_jwt_guard(connection, br)


async def root_api_jwt_guard(connection: ASGIConnection, br: BaseRouteHandler) -> None:
    try:
        service: TokenService = await br.dependencies["token_service"]()  # type: ignore
        if (res := await service.authenticate_access_token_connection(connection)) and res[0].is_root:
            return None
    except:
        pass
    raise PermissionDeniedException
