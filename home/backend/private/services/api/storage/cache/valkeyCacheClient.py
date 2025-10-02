import msgspec
import valkey.asyncio as valkey


class ValkeyCacheClient(msgspec.Struct, gc=False):
    client: valkey.Valkey
    prefix: str
    default_ttl: int

    def __post_init__(self):
        if self.default_ttl < 0:
            raise ValueError("TTL has to be non-negative")

    def _key(self, key: str) -> bytes:
        return f"{self.prefix}:{key}".encode()

    async def get(self, key: str) -> bytes | None:
        return await self.client.get(self._key(key))

    async def get_many(self, *keys: str) -> tuple[bytes | None, ...]:
        return await self.client.mget(map(self._key, keys))

    async def get_many_dict(self, *keys: str) -> dict[str, bytes | None]:
        return dict(zip(keys, await self.get_many(*keys)))

    async def set(self, key: str, value: bytes, ttl: int | None = None) -> bool:
        return await self.client.set(self._key(key), value, ex=self.default_ttl if ttl is None else ttl)

    async def exists(self, key: str) -> bool:
        return (await self.client.exists(self._key(key))) == 1

    async def exists_many(self, key: str) -> int:
        return await self.client.exists(self._key(key))

    async def keys(self, pattern: str) -> list[bytes]:
        return await self.client.keys(self._key(pattern))

    async def incr(self, key: str) -> int:
        return await self.client.incrby(self._key(key))

    async def incr_ex(self, key: str, ttl: int | None = None) -> int:
        _key = self._key(key)
        value = await self.client.incrby(_key)
        await self.client.expire(_key, self.default_ttl if ttl is None else ttl)
        return value

    async def expire(self, key: str, ttl: int) -> bool:
        return await self.client.expire(self._key(key), ttl)

    async def delete(self, key: str) -> bool:
        return await self.client.delete(self._key(key))

    async def close(self):
        await self.client.aclose()
