import asyncio
import sys
from asyncio import Task
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import IntEnum
from typing import Annotated, Awaitable, Coroutine, Literal, override

import msgspec
import valkey.asyncio as valkey

"""
milliseconds: 3 digits
auto:         6 digits
"""
type __TimeSpec = Literal["minutes", "seconds", "milliseconds", "auto"]
type DateTimeUTC = Annotated[datetime, ...]


print_err = lambda *x: print(*x, file=sys.stderr)


class MeasurementTypes(IntEnum):
    TEMPERATURE = 0
    HUMIDITY = 1
    AIRPRESSURE = 2


class MQTTPacket(msgspec.Struct):
    topic: str
    payload: bytes
    retain: bool = False


class SensorData(msgspec.Struct):
    date: str  # isoformat
    location: str
    device_name: str
    sensor_id: int
    data: dict[str, float]

    def to_dict(self):
        return dict(date=self.date, data=self.data)


class StatusData(msgspec.Struct):
    device_type: Literal["relay", "switch"] | str
    location: str
    device_name: str
    data: dict[str, bool]


class UserRolesBaseStruct[T](msgspec.Struct):
    roles: list[T]

    def has_role(self, role: T) -> bool:
        return role in self.roles

    def has_all_roles(self, roles: Iterable[T]) -> bool:
        return all(role in self.roles for role in roles)

    def has_any_roles(self, roles: Iterable[T]) -> bool:
        return any(role in self.roles for role in roles)

    def filter_roles(self, filter_roles: Iterable[T], disjunctive_select: bool) -> bool:
        if not filter_roles:
            return True
        return (self.has_any_roles if disjunctive_select else self.has_all_roles)(filter_roles)


class ValkeyBasic(valkey.Valkey):
    @override
    async def get(self, key: str | bytes) -> bytes | None:
        return await super().get(key)

    async def get_many(self, *keys: str | bytes) -> tuple[bytes | None, ...]:
        return await super().mget(keys)

    @override
    async def set(self, key: str | bytes, value: bytes) -> bool:
        return await super().set(key, value)

    @override
    async def keys(self, pattern: str | bytes) -> list[bytes]:
        return await super().keys(pattern)

    @override
    async def close(self):
        await super().aclose()


def fire_forget_coro(coro: Coroutine | Awaitable, name: str | None = None, _tasks: set[Task] = set()):
    task = asyncio.create_task(coro, name=name)  # type: ignore
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def datetime_to_isofmtZ(dt: DateTimeUTC, timespec: __TimeSpec = "milliseconds") -> str:
    dt_str = dt.isoformat(timespec=timespec)
    return dt_str[: dt_str.rfind("+")] + "Z"


def datetime_now_isofmtZ(timespec: __TimeSpec = "milliseconds") -> str:
    return datetime_to_isofmtZ(datetime.now(UTC), timespec=timespec)
