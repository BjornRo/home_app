from litestar import Request
from litestar.connection import ASGIConnection
from litestar.enums import ScopeType
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.middleware import AbstractMiddleware
from litestar.middleware.authentication import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from litestar.middleware.base import DefineMiddleware
from litestar.types import Receive, Scope, Send
from services.token_service import TokenService

# middleware = [
#     DefineMiddleware(my_jwt.JWTAuthenticationMiddleware, exclude="schema"),
# ] exclude_from_auth=True,


# class ElevatedAccessMiddleware(AbstractMiddleware):
#     scopes = {ScopeType.HTTP}
#     exclude_opt_key = "all_access"

#     async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
#         request = Request(scope)
#         appuser = cast(AppUser, request.user)
#         # token = cast(JWTToken, request.user)
#         if not appuser.is_root:
#             raise PermissionDeniedException
#         await self.app(scope, receive, send)


class __JWTAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        token_service: TokenService = connection.app.state.token_service
        if res := await token_service.authenticate_access_token_connection(connection):
            user, claims = res
            return AuthenticationResult(user=user, auth=claims)
        raise NotAuthorizedException


JWTAuthenticationMiddleware = DefineMiddleware(__JWTAuthenticationMiddleware, exclude="schema")
