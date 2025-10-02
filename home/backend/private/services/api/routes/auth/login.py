import asyncio
from typing import Literal, TypedDict

from core import jwt_config, types
from core.constants import SECURITY_TAG
from litestar import post
from litestar.controller import Controller
from litestar.exceptions import (
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.response import Response
from middleware.middlewares import JWTAuthenticationMiddleware
from services.auth_service import AuthService
from utils import http_helpers, jwt_helpers


class UserLoginOpt(TypedDict):
    pwd: str


class LoginResponse(TypedDict):
    access_token: str
    token_type: Literal["Bearer"]
    expires_in: int
    refresh_token: str
    refresh_token_expires_in: int


class LoginController(Controller):
    path = "/login"
    tags = ["auth"]

    @post(
        path="/verify",
        status_code=204,
        description="Verify an authenticated user given their user id",
        middleware=[JWTAuthenticationMiddleware],
        security=[SECURITY_TAG.access_token],
        # guards=[root_or_local_guard],
        raises=[NotAuthorizedException],
    )
    async def auth(self, request: types.AuthRequest, auth_service: AuthService, data: UserLoginOpt) -> None:
        if await auth_service.verify_user(request.auth.sub, data["pwd"]):
            return None
        raise NotAuthorizedException

    @post(
        path="/",
        status_code=200,
        description="Name can also be mail",
        raises=[NotAuthorizedException],
    )
    async def login(self, auth_service: AuthService, data: types.Credentials) -> Response[LoginResponse]:
        if user_id := await auth_service.login_user(data["login"], password=data["pwd"]):
            (access_token, _expiry), refresh_token = await asyncio.gather(
                jwt_helpers.gen_access_token(user_id),
                jwt_helpers.gen_refresh_token(user_id),
            )
            return Response(
                LoginResponse(
                    access_token=access_token,
                    token_type="Bearer",
                    expires_in=jwt_config.ACCESS_TIMEDELTA,
                    refresh_token=refresh_token,
                    refresh_token_expires_in=jwt_config.REFRESH_TIMEDELTA,
                ),
                cookies=[
                    http_helpers.create_access_cookie(access_token, jwt_config.ACCESS_TIMEDELTA),
                    http_helpers.create_refresh_cookie(refresh_token, jwt_config.REFRESH_TIMEDELTA),
                ],
            )

        raise NotAuthorizedException
