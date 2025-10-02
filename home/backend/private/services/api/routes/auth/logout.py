from typing import Annotated

from core import constants
from core.constants import SECURITY_TAG
from litestar import get
from litestar.connection import Request
from litestar.controller import Controller
from litestar.datastructures.cookie import Cookie
from litestar.exceptions import ClientException, NotAuthorizedException
from litestar.params import Body
from litestar.response import Response
from services.token_service import TokenService


class LogoutController(Controller):
    path = "/logout"
    tags = ["auth"]

    @get(path="/null_access", status_code=204, description="sets cookies to null")
    async def nullify_access(self) -> Response[None]:
        return Response(
            None,
            cookies=[
                Cookie(key=constants.REFRESH_TOKEN, path="/auth", value="null", httponly=True, secure=True),
                Cookie(key=constants.ACCESS_TOKEN, path="/", value="null", httponly=True, secure=True),
            ],
        )

    @get(
        path="/logout",
        security=(SECURITY_TAG.access_token, SECURITY_TAG.refresh_token),
        status_code=204,
        raises=[NotAuthorizedException, ClientException],
    )
    async def logout(
        self,
        request: Request,
        token_service: TokenService,
        logout_all: Annotated[
            bool,
            Body(
                title="Logout all",
                description="Updates when all tokens are valid from, which invalidates all tokens",
            ),
        ] = False,
    ) -> Response[None]:
        if refresh_token := request.cookies.get(constants.REFRESH_TOKEN):
            claims = await token_service.validate_token(refresh_token, access_token=False)
        else:
            if auth_header := request.headers.get("Authorization"):
                parts = auth_header.strip().split(" ", 2)
                if len(parts) != 2 or parts[0].lower() != "bearer":
                    raise ClientException("Malformed Authorization-header")
                access_token = parts[1]
            else:
                access_token = request.cookies.get(constants.ACCESS_TOKEN)
                if access_token is None:
                    raise ClientException("No token supplied")
            claims = await token_service.validate_token(access_token, access_token=True)

        if claims is None:
            raise NotAuthorizedException("Invalid token")

        if logout_all:
            await token_service.revoke_tokens(claims.sub)
        return Response(
            None,
            cookies=[  # Short-lived cookie such that it runs out quickly, either just throw away at the endpoint
                Cookie(key=constants.REFRESH_TOKEN, path="/auth", value="null", expires=5, httponly=True, secure=True),
                Cookie(key=constants.ACCESS_TOKEN, path="/", value="null", expires=5, httponly=True, secure=True),
            ],
        )
