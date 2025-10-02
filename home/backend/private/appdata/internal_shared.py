from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from msgspec import Struct

type DateTimeUTC = Annotated[datetime, ...]


class ErrorMessage(Struct):
    date: DateTimeUTC
    location: str
    device_name: str
    log_level: Literal["debug", "info", "warning", "error", "critical"]
    detail: str


class InternalRolesEnum(StrEnum):
    ROOT = "root"
    MQTT = "mqtt"
    LOCAL = "local"
    GLOBAL = "global"
    HOME = "home"
    REMOTE = "remote"
    CACHE = "cache"
    API = "api"  # allows to connect to this api

    @staticmethod
    def convert(roles: list[str] | list[InternalRolesEnum]) -> list[InternalRolesEnum]:
        return [InternalRolesEnum(r) for r in roles]
