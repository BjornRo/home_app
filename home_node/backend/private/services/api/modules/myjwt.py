import time
from asyncio import gather
from datetime import UTC, datetime, timedelta
from functools import partial
from os import environ
from typing import Any, Callable, NamedTuple, TypedDict

import constants
import db.distlock as dl
import jwt
from constants import HOSTNAME
from db.models import AppUser, UserRolesEnum
from db.queries import get_app_user_cache, get_token_valid_from_date
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.middleware.authentication import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from litestar.middleware.base import DefineMiddleware
from mytypes import MyConnection, MyRequest
from utils import (
    datetime_to_isoformat,
    fire_forget_coro,
    get_token_str,
    load_jwtkeys_json,
)

REFRESH_TOKEN = "refresh_token"
ACCESS_TOKEN = "access_token"

ACCESS_KEYDATA = load_jwtkeys_json("/certs/api/api_refresh.json")
REFRESH_KEYDATA = load_jwtkeys_json("/certs/api/api_access.json")

REFRESH_TIMEDELTA = int(timedelta(days=int(environ["REFRESH_JWT_DAYS"])).total_seconds())
ACCESS_TIMEDELTA = int(timedelta(minutes=int(environ["ACCESS_JWT_MINUTES"])).total_seconds())

CACHE_EXPIRY = int(timedelta(days=7).total_seconds())
ALGORITHMS = ["ES384"]

ISS = f"https://api.{HOSTNAME}/auth"
AUD = {"api": f"https://api.{HOSTNAME}", "root": f"https://{HOSTNAME}"}

type AuthRequest = MyRequest[AppUser, JWTToken]
type AuthConnection = MyConnection[AppUser, JWTToken]


class JWTToken(TypedDict):
    exp: int
    iat: int
    sub: str
    iss: str
    aud: list[str]


class JWTEncDec(NamedTuple):
    encode: Callable[[dict[str, Any]], str]
    decode: Callable[[str], JWTToken]


def gen_refresh_token(user_id: str):
    _time = int(time.time())
    tok: Any = JWTToken(exp=_time + REFRESH_TIMEDELTA, iat=_time, sub=user_id, iss=ISS, aud=[ISS])
    return _jwt_refresh.encode(tok)


def gen_access_token(user_id: str, aud: list[str] = list(AUD.values())):
    _time = int(time.time())
    expiry = _time + ACCESS_TIMEDELTA
    tok: Any = JWTToken(exp=expiry, iat=_time, sub=user_id, iss=ISS, aud=aud)
    return _jwt_access.encode(tok), expiry


def _decode(token: str, is_access: bool, opts: dict[str, bool] | None = {"verify_aud": False}):
    if is_access:
        res: JWTToken = jwt.decode(jwt=token, key=ACCESS_KEYDATA.keys.public, algorithms=ALGORITHMS, options=opts)
        if AUD["api"] in res["aud"]:
            return res
    else:
        res = jwt.decode(jwt=token, key=REFRESH_KEYDATA.keys.public, algorithms=ALGORITHMS, options=opts)
        if ISS == res["aud"][0]:
            return res
    raise jwt.InvalidAudienceError


_jwt_refresh = JWTEncDec(
    encode=partial(jwt.encode, key=REFRESH_KEYDATA.keys.private, algorithm=ALGORITHMS[0]),
    decode=partial(_decode, is_access=False),
)
_jwt_access = JWTEncDec(
    encode=partial(jwt.encode, key=ACCESS_KEYDATA.keys.private, algorithm=ALGORITHMS[0]),
    decode=partial(_decode, is_access=True),
)


async def jwt_auth_req(connection: ASGIConnection) -> tuple[AppUser, JWTToken] | None:
    tok = connection.cookies[ACCESS_TOKEN] if ACCESS_TOKEN in connection.cookies else get_token_str(connection.headers)
    if tok and (claims := await validate(tok, True)):
        if user := await get_app_user_cache(claims["sub"], (UserRolesEnum.USER,), False):
            fire_forget_coro(dl.online_users.set(claims["sub"], constants.LOGGING_ONLINE_EXPIRY_SEC, None))
            return user, claims
    return None


class JWTAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        if res := await jwt_auth_req(connection):
            user, claims = res
            return AuthenticationResult(user=user, auth=claims)
        raise NotAuthorizedException


jwt_middleware = DefineMiddleware(JWTAuthenticationMiddleware, exclude="schema")


async def delete_all_cache(user_id: str) -> None:
    await gather(
        dl.auth_jwt.delete(user_id),
    )


async def validate(token_str: str, access_token=True) -> JWTToken | None:
    try:
        claims = (_jwt_access.decode if access_token else _jwt_refresh.decode)(token_str)
        # Check tokens are valid from this date. Ex: log out all tokens, i.e move the date forward.
        user_id = claims["sub"]
        ok, dt_bytes = await dl.auth_jwt.get(user_id)
        if ok:
            date = datetime.fromisoformat(dt_bytes.decode())
        else:
            date = await get_token_valid_from_date(user_id)
            fire_forget_coro(dl.auth_jwt.set(user_id, CACHE_EXPIRY, datetime_to_isoformat(date).encode()))
        if date.fromtimestamp(claims["iat"], tz=UTC) >= date:
            return claims
    except:
        pass
    return None
