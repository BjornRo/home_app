from typing import Annotated

import msgspec
from internal import internal_types
from litestar import post
from litestar.controller import Controller
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.params import Parameter
from services.token_service import TokenService

type JWTTokenStr = str


class AccessRequest(msgspec.Struct):
    token: JWTTokenStr
    service_name: str


class InternalServiceController(Controller):
    path = "/service"
    tags = ["internal_service"]

    @post(
        path="/",
        status_code=200,
        raises=[PermissionDeniedException, NotAuthorizedException],
        description="If request successful, return RWX access",
    )
    async def request(
        self,
        request: internal_types.InternalAuthRequest,
        token_service: TokenService,
        data: AccessRequest,
    ) -> Annotated[int, Parameter(ge=0, le=7, description="Value as unix RWX value 0-7")]:
        data.service_name = data.service_name.lower()
        if data.service_name not in request.user.services:
            raise PermissionDeniedException("Service is not allowed to service this service")

        try:
            if appuser := await token_service.authenticate_access_token(data.token):
                if rwx := appuser[0].services.get(data.service_name):
                    return rwx.to_int()
                raise PermissionDeniedException
        except:
            pass
        raise NotAuthorizedException
