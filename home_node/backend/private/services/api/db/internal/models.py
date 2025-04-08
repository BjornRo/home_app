from __future__ import annotations

from enum import StrEnum
from typing import Literal, TypedDict

from db.models import UserRolesBaseStruct
from msgspec import Struct
from mytypes import DateTimeUTC


class TableInternal(StrEnum):
    USER = "user"
    USER_ROLE = "user_role"
    TOKEN_VALID_FROM = "token_valid_from"


class ACL(StrEnum):
    STORE = "store"  # User is allowed to store

# Data is stores as a record, not as a relation other than id points to user_id.
# To be aple to give new services more roles/categories just by adding it here.
class InternalRolesEnum(StrEnum):  # user_role:{id:user_id, role: InternalRolesEnum}
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


class InternalUserRoles(UserRolesBaseStruct[InternalRolesEnum], array_like=True):  # For the array_like
    pass


class InternalUserAPIRegistration(TypedDict):
    name: str
    pwd: str
    enabled: bool


class InternalUserUpdate(TypedDict, total=False):
    enabled: bool
    name: str
    pwd: str


class InternalUserLogin(Struct):
    pwd: str
    name: str


class InternalUserRegistration(Struct):
    created_by: str
    created: DateTimeUTC


class InternalUser(Struct):
    enabled: bool
    login: InternalUserLogin
    registration: InternalUserRegistration


class InternalUserView(InternalUserRoles):
    name: str
    created: DateTimeUTC
    created_by: str
    enabled: bool


class SensorData(Struct):
    date: DateTimeUTC
    location: str
    device_name: str
    data: dict[str, float]


class ErrorMessage(Struct):
    date: DateTimeUTC
    location: str
    device_name: str
    log_level: Literal["debug", "info", "warning", "error", "critical"]
    detail: str


# PROTECTED_ROLES = {
#     RolesEnum.MQTT,
#     RolesEnum.LOCAL,
#     RolesEnum.GLOBAL,
#     RolesEnum.HOME,
#     RolesEnum.REMOTE,
# }
