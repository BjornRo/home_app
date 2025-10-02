import asyncio

import msgspec
from core import types
from internal import internal_types, internal_utils
from internal.internal_services.user_service import InternalUserService
from internal.storage.repositories.internal_meta_repository import (
    InternalMetaRepository,
)
from litestar.connection import ASGIConnection
from storage.cache.valkeyCacheClient import ValkeyCacheClient
from utils import cache_helpers, http_helpers, time_helpers

token_encoder = msgspec.msgpack.Encoder().encode
token_decoder = msgspec.msgpack.Decoder(internal_types.Token).decode


class InternalTokenService(msgspec.Struct):
    cache_token: ValkeyCacheClient
    user_service: InternalUserService
    repo_meta: InternalMetaRepository

    async def authenticate_connection(self, connection: ASGIConnection):
        if token_str := http_helpers.get_token_str(connection.headers):
            if res := await self.cache_token.get(token_str):
                claims = token_decoder(res)
                valid_token, appuser = await asyncio.gather(
                    self.validate_token_date(claims.sub, claims.iat, claims.exp),
                    self.user_service.get_appuser(claims.sub),
                )
                if valid_token and appuser:
                    return appuser, claims
            elif claims := await self.validate_token(token_str):
                ttl = claims.exp - time_helpers.unixtime()
                if 2 < ttl:
                    await self.cache_token.set(token_str, token_encoder(claims), ttl - 2)
                if appuser := await self.user_service.get_appuser(claims.sub):
                    return appuser, claims
        return None

    async def validate_token(self, token_str: str) -> internal_types.Token | None:
        try:
            claims = await internal_utils.verify_token_threaded(token_str)
            if await self.validate_token_date(claims.sub, claims.iat, claims.exp):
                return claims
        except:
            pass
        return None

    async def validate_token_date(self, username: types.UserID, issued_at: int, expires_at: int):
        versioned_key = await cache_helpers.get_version_key(self.cache_token, username)
        now = time_helpers.unixtime()

        if valid_after := await self.cache_token.get(versioned_key):
            return int(valid_after) <= issued_at and now < expires_at
        else:
            valid_after = await self.repo_meta.get_token_policy_unixtime(username)
            if valid_after <= issued_at and now < expires_at:
                ttl = expires_at - now
                if 2 < ttl:
                    await self.cache_token.set(versioned_key, value=str(valid_after).encode(), ttl=ttl - 2)
                return True
        return False

    async def revoke_tokens(self, username: types.UserID):
        await self.repo_meta.upsert_tokens_valid_after(username)
        await cache_helpers.incr_version(self.cache_token, username)
