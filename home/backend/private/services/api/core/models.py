from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict, override

import msgspec
from core import enums, types
from msgspec import Struct
from storage.db import tables

from appdata import shared  # type: ignore

type AppUserACL = dict[str, types.RWX]


class UserFullData(Struct):
    user_id: types.UserID
    account: tables.User
    registration: tables.Registration
    profile: tables.User_Profile
    roles: list[tables.Has_Role]
    acl: list[tables.Has_Service]


class UserDataDTO(Struct):
    user_id: types.UserID
    login_name: str
    login_mail: str | None
    display_name: str
    created_at: shared.DateTimeUTC


class UserRolesAPIStruct(shared.UserRolesBaseStruct[enums.UserRoles]):
    @override
    def has_all_roles(self, roles: Iterable[enums.UserRoles]) -> bool:  # type: ignore
        return self.is_root or super().has_all_roles(roles)

    @override
    def has_any_roles(self, roles: Iterable[enums.UserRoles]) -> bool:  # type: ignore
        return self.is_root or super().has_any_roles(roles)

    @override
    def filter_roles(self, filter_roles: Iterable[enums.UserRoles], disjunctive_select: bool) -> bool:  # type: ignore
        return self.is_root or super().filter_roles(filter_roles, disjunctive_select)

    @property
    def is_root(self) -> bool:
        return enums.UserRoles.ROOT in self.roles

    @property
    def is_mod(self) -> bool:
        return enums.UserRoles.MOD in self.roles

    @property
    def is_user(self) -> bool:
        return enums.UserRoles.USER in self.roles


class AppUser(UserRolesAPIStruct, array_like=True):  # type: ignore
    user_id: types.UserID
    display_name: str
    services: AppUserACL

    def to_dict(self):
        class ApiAppUser(TypedDict):
            user_id: types.UserID
            display_name: str
            roles: list[enums.UserRoles]
            services: AppUserACL

        return ApiAppUser(**msgspec.to_builtins(self))


class AllUserView(Struct):
    user_id: types.UserID
    enabled: bool
    registration_date: shared.DateTimeUTC
    display_name: str
    login_name: str
    login_mail: str | None
    created_by: types.UserID | None
    services: dict[str, int]  # service_name, rwx
    roles: list[enums.UserRoles]


# class UserBasic(Struct):
#     user_id: int
#     login_name: str
#     login_mail: str
#     login_mail: str
