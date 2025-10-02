from appdata import internal_shared, shared  # type: ignore
from msgspec import Struct

from core import types


class User(Struct):
    user_id: str
    pwd: str
    enabled: bool


class User_Registration(Struct):
    user_id: str
    created_date: shared.DateTimeUTC


class Has_Role(Struct):
    user_id: str
    role_name: internal_shared.InternalRolesEnum
    created_date: shared.DateTimeUTC


class User_Token_Policy(Struct):
    user_id: types.UserID
    tokens_valid_after: types.Unixtime


class Service_Ownership(Struct):
    service_name: str  # Same as app-database service(name)
    user_id: str
