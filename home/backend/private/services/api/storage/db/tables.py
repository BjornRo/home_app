from __future__ import annotations

from appdata import shared  # type: ignore
from msgspec import Struct

from core import enums, types


class User(Struct):  # "Credentials" essentially
    user_id: types.UserID  # UUIDv7
    login_name: str
    login_mail: str | None
    password: str  # b64(bcrypt)
    enabled: bool
    last_login_date: shared.DateTimeUTC
    last_updated_date: shared.DateTimeUTC


class Registration(Struct):  # Read only
    user_id: types.UserID
    name: str
    mail: str | None
    created_by: types.UserID | None
    created_date: shared.DateTimeUTC


class User_Token_Policy(Struct):
    user_id: types.UserID
    tokens_valid_after: types.Unixtime


class User_Profile(Struct):
    user_id: types.UserID
    display_name: str
    last_updated_date: shared.DateTimeUTC


# class Role(Struct):
#     name: enums.UserRoles


class Has_Role(Struct):
    user_id: types.UserID
    role_name: enums.UserRoles
    valid_from: shared.DateTimeUTC
    valid_to: shared.DateTimeUTC
    given_by: types.UserID | None
    created_date: shared.DateTimeUTC


class Service(Struct):
    name: str
    url: str
    description: str
    created_date: shared.DateTimeUTC


class Has_Service(Struct):
    user_id: types.UserID
    service_name: str
    rwx: int
    valid_from: shared.DateTimeUTC
    valid_to: shared.DateTimeUTC
    given_by: types.UserID | None
    created_date: shared.DateTimeUTC


class User_Bans(Struct):
    _id: int  # Auto-incremented(table wide). Users can have multiple bans.
    user_id: types.UserID
    is_active: bool
    banned_by: types.UserID
    unbanned_by: types.UserID
    reason: str
    start_time: shared.DateTimeUTC
    end_time: shared.DateTimeUTC
