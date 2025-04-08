import time
from datetime import timedelta
from typing import Any, TypedDict

import db.internal.queries as internal_queries
import jwt
from db.internal.models import (
    InternalRolesEnum,
    InternalUserAPIRegistration,
    InternalUserRoles,
)
from litestar.connection import ASGIConnection
from litestar.datastructures import Headers
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler
from litestar.middleware.authentication import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from litestar.middleware.base import DefineMiddleware
from mytypes import MyConnection, MyRequest, UserID, UserID_Result
from utils import check_password_b64, get_token_str, secrets

token_expiry = int(timedelta(days=90).total_seconds())
token_secret = secrets[2]
token_algo = ["HS384"]


class Token(TypedDict):
    iat: int
    exp: int
    sub: str


type InternalAuthConnection = MyConnection[UserID_Result[InternalUserRoles], Token]
type InternalAuthRequest = MyRequest[UserID_Result[InternalUserRoles], Token]


def api_guard(connection: InternalAuthConnection, _: BaseRouteHandler) -> None:
    try:
        if connection.user[1].has_any_roles((InternalRolesEnum.API, InternalRolesEnum.ROOT)):
            return None
    except:
        pass
    raise PermissionDeniedException


def verify_token(token_str: str) -> Token:
    return jwt.decode(token_str, key=token_secret, algorithms=token_algo)


def generate_token(user_id: UserID) -> str:
    time_now = int(time.time())
    payload: dict[str, Any] = Token(exp=time_now + token_expiry, iat=time_now, sub=user_id)  # type: ignore
    return jwt.encode(payload=payload, key=token_secret, algorithm=token_algo[0])


async def verify_password(name: str, pwd: str) -> UserID_Result[InternalUserAPIRegistration]:
    if (user := await internal_queries.get_internal_userlogin(name)) and user[1]["enabled"]:
        hash_pwd = user[1]["pwd"]
    else:
        hash_pwd = None
    if await check_password_b64(pwd, hash_pwd) and user:
        return user
    raise NotAuthorizedException


async def get_jwt_auth_result(headers: Headers) -> tuple[UserID_Result[InternalUserRoles], Token] | None:
    if token_str := get_token_str(headers):
        try:
            claims = verify_token(token_str)
            user_id = claims["sub"]
            roles = await internal_queries.get_internal_user_roles_cache(user_id)
            if roles:
                return (user_id, roles), claims
        except:
            pass
    return None


# exclude_from_auth=True,
class JWTInternalAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        if res := await get_jwt_auth_result(connection.headers):
            user_id_roles, claims = res
            return AuthenticationResult(user=user_id_roles, auth=claims)

        raise NotAuthorizedException


jwt_internal_middleware = DefineMiddleware(JWTInternalAuthenticationMiddleware, exclude="schema")
