import asyncio
from datetime import timedelta
from typing import Any, TypedDict

import msgspec
from appdata.internal_shared import InternalRolesEnum  # type: ignore
from jwcrypto import common, jwk, jwt
from litestar.connection import ASGIConnection
from litestar.datastructures import Headers
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler
from litestar.middleware.authentication import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from litestar.middleware.base import DefineMiddleware

from core import constants, types
from utils import cache_helpers, helpers, http_helpers, time_helpers

from . import internal_types

token_expiry = int(timedelta(days=7).total_seconds())
token_key_sign = jwk.JWK(kty="oct", k=constants.SECRETS[0][:48].hex())
token_key_encrypt = jwk.JWK(kty="oct", k=constants.SECRETS[1][:32].hex())
token_decoder = msgspec.json.Decoder(internal_types.Token).decode


def api_guard(connection: internal_types.InternalAuthConnection, route_handler: BaseRouteHandler) -> None:
    if route_handler.opt.get("exclude_api_guard", False):
        return None

    try:
        if connection.user.has_role(InternalRolesEnum.API):
            return None
    except:
        pass
    raise PermissionDeniedException


def decrypt_token(token_str: str):
    return jwt.JWT(key=token_key_encrypt, jwt=token_str, expected_type="JWE")


def verify_token(token_str: str) -> internal_types.Token:
    encrypted_token = decrypt_token(token_str)
    signed_token = jwt.JWT(key=token_key_sign, jwt=encrypted_token.claims)
    return token_decoder(signed_token.claims)


def generate_token(user_id: str) -> str:
    time_now = time_helpers.unixtime()
    payload = internal_types.Token(exp=time_now + token_expiry, iat=time_now, sub=user_id)

    token = jwt.JWT(header={"alg": "HS384"}, claims=msgspec.to_builtins(payload))
    token.make_signed_token(token_key_sign)

    Etoken = jwt.JWT(header={"alg": "A256KW", "enc": "A256GCM"}, claims=token.serialize())
    Etoken.make_encrypted_token(token_key_encrypt)

    return Etoken.serialize()


async def verify_token_threaded(token_str: str):
    return await helpers.pool_runner(verify_token, token_str)


async def generate_token_threaded(user_id: str):
    return await helpers.pool_runner(generate_token, user_id)
