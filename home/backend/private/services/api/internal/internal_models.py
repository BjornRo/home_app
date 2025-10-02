from __future__ import annotations

from typing import TypedDict

from appdata import internal_shared, shared  # type: ignore


class InternalUserUpdate(TypedDict, total=False):
    user_id: str
    pwd: str
    enabled: bool


class InternalAppUser(shared.UserRolesBaseStruct[internal_shared.InternalRolesEnum], array_like=True):  # type: ignore
    user_id: str
    services: list[str]


class AllUserView(InternalAppUser):
    enabled: bool
    created_date: shared.DateTimeUTC
