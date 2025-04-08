from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Generic, TypedDict, TypeVar, override

from msgspec import Struct
from mytypes import DateTimeUTC, UserID


class TableAPI(StrEnum):
    USER = "user"
    USER_ROLE = "user_role"
    TOKEN_VALID_FROM = "token_valid_from"


class LoginTEnum(StrEnum):
    NAME = "name"
    MAIL = "mail"


class UserRolesEnum(StrEnum):
    ROOT = "root"
    MOD = "mod"  # Moderator
    USER = "user"

    @staticmethod
    def convert(roles: list[str] | list[UserRolesEnum]) -> list[UserRolesEnum]:
        return [UserRolesEnum(r) for r in roles]


"""
DB Tables
"""

HasRole = TypedDict(
    "HasRole",
    {
        "in": str,
        "out": str,
        "from": DateTimeUTC,
        "to": DateTimeUTC,
        "given_by": str,
        "created": DateTimeUTC,
    },
)


class User(Struct):
    modified_date: DateTimeUTC
    login: UserLogin
    registration: UserRegistration
    data: UserData


class UserLogin(Struct):
    name: str
    pwd: str
    mail: str | None


class UserRegistration(Struct):
    name: str
    mail: str | None
    number: int
    created_by: str
    created: DateTimeUTC


class UserData(Struct):
    name: str


"""
END DB TABLES
"""


T = TypeVar("T")  # New [T]-syntax does not work due to multiprocessing :(


class UserRolesBaseStruct(Struct, Generic[T]):
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


class UserRolesAPIStruct(UserRolesBaseStruct[UserRolesEnum]):
    @override
    def has_all_roles(self, roles: Iterable[UserRolesEnum]) -> bool:
        if self.is_root:
            return True
        return super().has_all_roles(roles)

    @override
    def has_any_roles(self, roles: Iterable[UserRolesEnum]) -> bool:
        if self.is_root:
            return True
        return super().has_any_roles(roles)

    @override
    def filter_roles(self, filter_roles: Iterable[UserRolesEnum], disjunctive_select: bool) -> bool:
        if self.is_root:
            return True
        return super().filter_roles(filter_roles, disjunctive_select)

    @property
    def is_root(self) -> bool:
        return UserRolesEnum.ROOT in self.roles

    @property
    def is_mod(self) -> bool:
        return UserRolesEnum.MOD in self.roles

    @property
    def is_user(self) -> bool:
        return UserRolesEnum.USER in self.roles


class AppUser(UserRolesAPIStruct, array_like=True):
    name: str

    def to_dict(self) -> ApiAppUser:
        return ApiAppUser(name=self.name, roles=self.roles)


class ApiAppUser(TypedDict):
    roles: list[UserRolesEnum]
    name: str


class UserACL(Struct):
    resource: str
    rwx: int
    start: str
    end: str
    given_by: str
    created: str


class AppUserACL(Struct):
    resource: str
    rwx: int


class AllUserView(User):
    user_id: UserID
    acl: list[UserACL]
    roles: list[UserRolesEnum]


class TokenValidFromDate(Struct):
    # To keep it as stateless as possible and still be able to "revoke" tokens.
    # If a user logs out or "revoke" is issued, set the date to that time of action.
    user_id: UserID
    unixtime: int
