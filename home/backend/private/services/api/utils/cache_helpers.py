from core import types
from storage.cache.valkeyCacheClient import ValkeyCacheClient


def version_key(key: str) -> str:
    return f"{key}:v"


async def get_version_key(cache: ValkeyCacheClient, user_id: types.UserID) -> str:
    return f"{user_id}:{int(await cache.get(version_key(user_id)) or 1)}"


async def incr_version(cache: ValkeyCacheClient, user_id: types.UserID | str):
    await cache.incr_ex(version_key(user_id))
