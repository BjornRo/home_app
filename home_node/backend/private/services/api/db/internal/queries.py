from asyncio import gather
from datetime import timedelta
from typing import Any

import db.distlock as dl
from constants import DB_URI
from db.internal.models import InternalUserRoles
from db.strategy.surreal import SurrealInternalDB
from msgspec import msgpack
from mytypes import DateTimeUTC, UserID, UserID_Result
from utils import fire_forget_coro, msgpack_encoder

from .models import (
    InternalRolesEnum,
    InternalUserAPIRegistration,
    InternalUserUpdate,
    InternalUserView,
)

INTERNAL_DB = SurrealInternalDB(DB_URI, database="internal")

_default_expire = int(timedelta(hours=48).total_seconds())

internal_user_decode = msgpack.Decoder(InternalUserRoles).decode


async def query(query: str, query_args: dict[str, Any] | None = None):
    return await INTERNAL_DB.query(query=query, query_args=query_args)


async def insert_internal_user(name: str, hash_b64_pwd: str, created_by_user_id: str, enabled=True) -> None | UserID:
    return await INTERNAL_DB.insert_internal_user(name, hash_b64_pwd, created_by_user_id, enabled=enabled)


async def insert_internal_userrole(name_or_user_id: str, role: InternalRolesEnum, given_by_user_id: str) -> bool:
    return await INTERNAL_DB.insert_internal_userrole(name_or_user_id, role, given_by_user_id)


async def get_all_internal_user_view(limit=10, offset=0, asc=True) -> list[UserID_Result[InternalUserView]]:
    return await INTERNAL_DB.get_all_internal_user_view(limit, offset, asc)


async def get_internal_token_valid_from_date(user_id: str) -> DateTimeUTC:  # 0 means no time set
    return await INTERNAL_DB.get_internal_token_valid_from_date(user_id)


async def get_internal_userlogin(name: str) -> UserID_Result[InternalUserAPIRegistration] | None:
    return await INTERNAL_DB.get_internal_userlogin(name)


async def get_internal_userroles(user_id: str):
    return await INTERNAL_DB.get_internal_userroles(user_id)


async def upsert_internal_token_valid_from_date(user_id: str) -> None:
    return await INTERNAL_DB.upsert_internal_token_valid_from_date(user_id)


async def update_internal_user(name_or_user_id: str, data: InternalUserUpdate) -> None:
    return await INTERNAL_DB.update_internal_user(name_or_user_id, data)


async def delete_internal_user(name_or_user_id: str) -> bool:
    return await INTERNAL_DB.delete_internal_user(name_or_user_id)


async def delete_internal_userrole(name_or_user_id: str, role: InternalRolesEnum) -> bool:
    return await INTERNAL_DB.delete_internal_userrole(name_or_user_id, role)


async def get_internal_user_roles_cache(user_id: str) -> InternalUserRoles | None:
    try:
        if result := await _cache_internal_user_get(user_id):
            return result
        if result := await get_internal_userroles(user_id):
            await _cache_internal_user_set(user_id, result)
            return result
        return None
    except:
        print(__import__("traceback").print_exc(), file=__import__("sys").stderr)
        raise
    return None


async def delete_internal_all_cache(user_id: str) -> None:
    await gather(
        dl.internal_user.delete(user_id),
        dl.internal_user_exists.delete(user_id),
    )


async def cache_user_exists(user_id: str) -> bool:
    ok, _ = await dl.internal_user_exists.get(user_id)
    if not ok:
        if not await INTERNAL_DB.exists_internal_user(user_id):
            return False
        fire_forget_coro(dl.internal_user_exists.set(user_id, _default_expire, None))
    return True


async def _cache_internal_user_get(user_id: str) -> InternalUserRoles | None:
    ok, data = await dl.internal_user.get(user_id)
    if ok:
        return internal_user_decode(data)
    return None


async def _cache_internal_user_set(user_id: str, value: InternalUserRoles) -> None:
    await dl.internal_user.set(user_id, _default_expire, msgpack_encoder(value))
