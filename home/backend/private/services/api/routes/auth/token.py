from core import constants, jwt_config
from litestar import get
from litestar.connection import Request
from litestar.controller import Controller
from litestar.exceptions import NotAuthorizedException
from litestar.response import Response
from services.token_service import TokenService
from utils import http_helpers, jwt_helpers


class TokenController(Controller):
    path = "/token"
    tags = ["auth"]

    @get(
        path="/token",
        security=[{"RefreshToken": []}],
        raises=[NotAuthorizedException],
        description="Get new access token from refresh token using cookies, returns expiry delta of new token",
        # exclude_from_auth=True,
    )
    async def token(self, request: Request, token_service: TokenService) -> Response[int]:
        """Get new access token from refresh token.
        Client sends refresh token in cookie $REFRESH_TOKEN.

        Server validates
        """
        try:
            if claims := await token_service.validate_token(
                request.cookies[constants.REFRESH_TOKEN],
                access_token=False,
            ):
                new_token, expiry = await jwt_helpers.gen_access_token(claims.sub)
                return Response(
                    content=expiry,
                    cookies=[
                        http_helpers.create_access_cookie(new_token, jwt_config.ACCESS_TIMEDELTA),
                    ],
                )
        except:
            pass
        raise NotAuthorizedException
