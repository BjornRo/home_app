from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated, Literal, NotRequired, TypedDict

import db.distlock as dl
import db.queries as queries
import modules.myjwt as myjwt
from constants import DEFAULT_SECURITY_TAG as SECTAG
from constants import (
    LOGGING_ONLINE_EXPIRY_SEC,
    MAX_LOGIN_ATTEMPS_PER_IP,
    MAX_LOGIN_TIMEOUT,
)
from db.models import LoginTEnum, UserRolesEnum
from litestar import get, post
from litestar.connection import Request
from litestar.controller import Controller
from litestar.datastructures.cookie import Cookie
from litestar.exceptions import (
    InternalServerException,
    NotAuthorizedException,
    PermissionDeniedException,
    TooManyRequestsException,
)
from litestar.params import Body
from litestar.response import Response
from modules.guards import root_or_local_guard
from mytypes import NamePWD, UserID
from utils import check_password_b64, fire_forget_coro


class UserLoginOpt(TypedDict):
    name: NotRequired[str]
    pwd: str


@dataclass
class NewToken:
    access_token: str
    expires_in: int
    token_type = "Bearer"


class LoginResponse(TypedDict):
    access_token: str
    token_type: Literal["Bearer"]
    expires_in: int
    refresh_token: str
    refresh_token_expires_in: int


def create_refresh_cookie(refresh_token: str):
    return Cookie(
        key=myjwt.REFRESH_TOKEN,
        value=refresh_token,
        expires=myjwt.REFRESH_TIMEDELTA,
        path="/auth/",
        httponly=True,
        secure=True,
        samesite="lax",
    )


def create_access_cookie(access_token: str):
    return Cookie(
        key=myjwt.ACCESS_TOKEN,
        value=access_token,
        expires=myjwt.ACCESS_TIMEDELTA,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )


async def get_verify_password(
    name_or_mail: str, pwd: str, filter_roles: Iterable[UserRolesEnum], disjunctive_select: bool = False
) -> UserID:
    login_type = LoginTEnum.MAIL if "@" in name_or_mail else LoginTEnum.NAME
    if user := await queries.get_userid_roles_pwd(name_or_mail, login_type, filter_roles, disjunctive_select):
        hash_pwd = user[1][0]
    else:
        hash_pwd = None
    if await check_password_b64(pwd, hash_pwd) and user:
        return user[0]
    raise NotAuthorizedException


class AuthedController(Controller):
    path = "/auth"
    tags = ["auth"]

    @get(path="/null_access", status_code=204, description="sets cookies to null")
    async def nullify_access(self) -> Response[None]:
        return Response(
            None,
            cookies=[
                Cookie(key=myjwt.REFRESH_TOKEN, path="/auth", value="null", httponly=True, secure=True),
                Cookie(key=myjwt.ACCESS_TOKEN, path="/", value="null", httponly=True, secure=True),
            ],
        )

    @post(
        path="/auth",
        status_code=204,
        middleware=[myjwt.jwt_middleware],
        security=SECTAG,
        guards=[root_or_local_guard],
        raises=[PermissionDeniedException, InternalServerException],
    )
    async def auth(
        self,
        request: myjwt.AuthRequest,
        data: Annotated[
            UserLoginOpt,
            Body(
                title="Verify user login again",
                description="If user is specified, then check guessed user and db user is equal along with password",
            ),
        ],
    ) -> None:
        """If login is attached, then validate against the login/name, otherwise only pwd"""
        user_id = request.auth["sub"]
        name = data.get("name")
        if not name:
            name = await queries.get_user_name(user_id)
            if not name:
                raise InternalServerException
        elif await queries.get_user_id(name) != user_id:  # User trying other usernames
            await check_password_b64("timing_compute_me", None)
            raise PermissionDeniedException

        if user_cred := await queries.get_userid_roles_pwd(name, LoginTEnum.NAME, (UserRolesEnum.USER,), False):
            pwd = user_cred[1][0]
        else:
            pwd = None
        if await check_password_b64(data["pwd"], pwd):
            return None
        raise PermissionDeniedException

    @post(
        path="/login",
        status_code=200,
        description="Name can also be mail",
        raises=[NotAuthorizedException, TooManyRequestsException],
    )
    async def login(self, request: Request, data: NamePWD) -> Response[LoginResponse]:
        new_data = {**data, "filter_roles": (UserRolesEnum.USER,), "disjunctive_select": False}
        new_data["name_or_mail"] = new_data.pop("name")
        if ip := request.headers.get("X-Real-IP"):
            _, attempts = await dl.count_login_attempts.set(ip, MAX_LOGIN_TIMEOUT, None)
            if int.from_bytes(attempts) >= MAX_LOGIN_ATTEMPS_PER_IP:
                raise TooManyRequestsException(f"{int.from_bytes(attempts)}, {ip}")
            user_id = await get_verify_password(**new_data)
            fire_forget_coro(dl.count_login_attempts.delete(ip))
        else:
            user_id = await get_verify_password(**new_data)

        fire_forget_coro(dl.online_users.set(user_id, LOGGING_ONLINE_EXPIRY_SEC, None))
        access_token = myjwt.gen_access_token(user_id)[0]
        refresh_token = myjwt.gen_refresh_token(user_id)
        return Response(
            LoginResponse(
                access_token=access_token,
                token_type="Bearer",
                expires_in=myjwt.ACCESS_TIMEDELTA,
                refresh_token=refresh_token,
                refresh_token_expires_in=myjwt.REFRESH_TIMEDELTA,
            ),
            cookies=[
                create_access_cookie(access_token),
                create_refresh_cookie(refresh_token),
            ],
        )

    @get(
        path="/logout",
        security=[*SECTAG, {"RefreshToken": []}],
        status_code=204,
        raises=[NotAuthorizedException],
    )
    async def logout(
        self,
        request: Request,
        logout_all: Annotated[
            bool,
            Body(
                title="Logout all",
                description="Updates when all tokens are valid from, which invalidates all tokens",
            ),
        ] = False,
    ) -> Response[None]:
        access_token = None
        refresh_token = request.cookies.get(myjwt.REFRESH_TOKEN)
        if refresh_token is None:
            access_token = request.headers.get("Authorization")
            if access_token and access_token[:6].lower() == "bearer":
                access_token = access_token[7:].strip()
            else:
                access_token = request.cookies.get(myjwt.ACCESS_TOKEN)
                if access_token is None:
                    raise NotAuthorizedException

        claims = None
        if refresh_token:
            claims = await myjwt.validate(refresh_token, access_token=False)
        if not claims and access_token:
            claims = await myjwt.validate(access_token, access_token=True)

        if claims is None:
            raise NotAuthorizedException

        fire_forget_coro(myjwt.delete_all_cache(claims["sub"]))
        fire_forget_coro(queries.delete_all_db_cache(claims["sub"]))
        if logout_all:
            fire_forget_coro(queries.upsert_token_valid_from_date(claims["sub"]))
        return Response(
            None,
            cookies=[  # Short-lived cookie such that it runs out quickly, either just throw away at the endpoint
                Cookie(
                    key=myjwt.REFRESH_TOKEN, path="/auth", value="null", expires=5, httponly=True, secure=True
                ),
                Cookie(key=myjwt.ACCESS_TOKEN, path="/", value="null", expires=5, httponly=True, secure=True),
            ],
        )

    @get(
        path="/token",
        security=[{"RefreshToken": []}],
        raises=[NotAuthorizedException],
        description="Get new access token from refresh token using cookies, returns expiry delta of new token",
        exclude_from_auth=True,
    )
    async def token(self, request: Request) -> Response[int]:
        """Get new access token from refresh token.
        Client sends refresh token in cookie $REFRESH_TOKEN.

        Server validates
        """
        try:
            if claims := await myjwt.validate(request.cookies[myjwt.REFRESH_TOKEN], access_token=False):
                uid = claims["sub"]
                if await queries.jwt_exists_user_cache(uid):
                    new_token, expiry = myjwt.gen_access_token(uid)
                    return Response(
                        content=expiry,
                        cookies=[
                            create_access_cookie(new_token),
                        ],
                    )
        except:
            pass
        raise NotAuthorizedException
