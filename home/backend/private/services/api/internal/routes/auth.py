from core import types
from internal import internal_types, internal_utils
from internal.internal_services.token_service import InternalTokenService
from internal.internal_services.user_service import InternalUserService
from internal.internal_utils import api_guard
from internal.middlewares import JWTInternalAuthMiddleware
from litestar import get, post
from litestar.controller import Controller
from litestar.exceptions import NotAuthorizedException
from utils import helpers


class InternalAuthController(Controller):
    path = "/auth"
    tags = ["internal_auth"]
    guards = [api_guard]
    middleware = [JWTInternalAuthMiddleware]

    @post(
        path="/login",
        status_code=200,
        raises=[NotAuthorizedException],
        exclude_from_auth=True,
        opt={"exclude_api_guard": True},
    )
    async def login(
        self,
        internal_user_service: InternalUserService,
        data: types.Credentials,
    ) -> internal_types.NewToken:
        if user := await internal_user_service.get_user_auth(data["login"]):
            if await helpers.check_password_b64_threaded(data["pwd"], user.pwd):
                return internal_types.NewToken(
                    access_token=await internal_utils.generate_token_threaded(user_id=user.user_id),
                    expires_in=internal_utils.token_expiry,
                )
        else:
            await helpers.check_password_b64_threaded(data["pwd"], None)
        raise NotAuthorizedException

    @get(
        path="/logout",
        description="Invalidates all tokens from this date",
        status_code=204,
    )
    async def logout(
        self,
        internal_token_service: InternalTokenService,
        request: internal_types.InternalAuthRequest,
    ) -> None:
        await internal_token_service.revoke_tokens(request.user.user_id)

    # @get(
    #     path="/token",
    #     description="Get new token from token",
    # )
    # async def token(self, request: internal_types.InternalAuthRequest) -> internal_types.NewToken:
    #     return internal_types.NewToken(
    #         access_token=await internal_utils.generate_token_threaded(user_id=request.user.user_id),
    #         expires_in=internal_utils.token_expiry,
    #     )
