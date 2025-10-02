import asyncio

import msgspec
import valkey.asyncio as valkey
from core import constants, types
from litestar.connection import ASGIConnection
from services.user_service import UserService
from storage.cache.valkeyCacheClient import ValkeyCacheClient
from storage.db.repositories.user_meta_repository import UserMetaRepository
from utils import cache_helpers, helpers, http_helpers, jwt_helpers, time_helpers

from appdata import shared

token_encoder = msgspec.msgpack.Encoder().encode
token_decoder = msgspec.msgpack.Decoder(types.JWTToken).decode


class TokenService(msgspec.Struct):
    user_service: UserService
    repo_meta: UserMetaRepository
    cache_token: ValkeyCacheClient
    cache_online_users: valkey.Valkey

    async def authenticate_access_token_connection(self, connection: ASGIConnection):
        if token := connection.cookies.get(
            constants.ACCESS_TOKEN,
            http_helpers.get_token_str(connection.headers),
        ):
            if result := await self.authenticate_access_token(token):
                shared.fire_forget_coro(self.cache_online_users.set(result[0].user_id, value=b"1", ex=90))
                return result
        return None

    async def authenticate_access_token(self, token: str):
        """
        Raises:
            NotFoundError
        """
        if res := await self.cache_token.get(token):
            claims = token_decoder(res)
            valid_token, appuser = await asyncio.gather(
                self.validate_token_date(claims.sub, claims.iat, claims.exp),
                self.user_service.get_appuser(claims.sub),
            )
            if valid_token:
                return appuser, claims

        elif claims := await self.validate_token(token, access_token=True):
            ttl = claims.exp - time_helpers.unixtime()
            if 2 < ttl:
                await self.cache_token.set(token, token_encoder(claims), ttl - 2)
            if appuser := await self.user_service.get_appuser(claims.sub):
                return appuser, claims
        return None

    async def validate_token(self, token_str: str, access_token=True) -> types.JWTToken | None:
        try:
            func = jwt_helpers.jwt_access.decode if access_token else jwt_helpers.jwt_refresh.decode
            claims = await helpers.pool_runner(func, token_str)
            if await self.validate_token_date(claims.sub, claims.iat, claims.exp):
                return claims
        except:
            pass
        return None

    async def validate_token_date(self, user_id: types.UserID, issued_at: int, expires_at: int):
        versioned_key = await cache_helpers.get_version_key(self.cache_token, user_id)
        now = time_helpers.unixtime()

        if valid_after := await self.cache_token.get(versioned_key):
            return int(valid_after) <= issued_at and now < expires_at
        else:
            valid_after = await self.repo_meta.get_token_policy_unixtime(user_id)
            if valid_after <= issued_at and now < expires_at:
                ttl = expires_at - now
                if 2 < ttl:
                    await self.cache_token.set(versioned_key, value=str(valid_after).encode(), ttl=ttl - 2)
                return True
        return False

    async def revoke_tokens(self, user_id: types.UserID):
        await self.repo_meta.upsert_tokens_valid_after(user_id)
        await cache_helpers.incr_version(self.cache_token, user_id=user_id)
