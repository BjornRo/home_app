from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.middleware.authentication import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from litestar.middleware.base import DefineMiddleware

from internal.internal_services.token_service import InternalTokenService


class __JWTInternalAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        token_service: InternalTokenService = connection.app.state.internal_token_service
        if res := await token_service.authenticate_connection(connection):
            user, claims = res
            return AuthenticationResult(user=user, auth=claims)

        raise NotAuthorizedException


JWTInternalAuthMiddleware = DefineMiddleware(__JWTInternalAuthenticationMiddleware, exclude="schema")
