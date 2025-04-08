from typing import cast

from db.models import AppUser
from litestar import Request
from litestar.enums import ScopeType
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.middleware import AbstractMiddleware
from litestar.types import Receive, Scope, Send

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
