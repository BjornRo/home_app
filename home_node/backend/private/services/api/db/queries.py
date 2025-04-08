from asyncio import gather
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable

import db.distlock as dl
from constants import DB_URI
from db.models import (
    AllUserView,
    AppUser,
    LoginTEnum,
    User,
    UserData,
    UserLogin,
    UserRegistration,
    UserRolesAPIStruct,
    UserRolesEnum,
)
from db.strategy.surreal import SurrealDB
from msgspec import msgpack
from mytypes import DateT, DateTimeUTC, Password, UserID, UserID_Result
from utils import fire_forget_coro, msgpack_encoder

""" Database strategy """
DB = SurrealDB(DB_URI, database="api")


""" Cache store related """
_default_expire = int(timedelta(hours=48).total_seconds())
appuser_decode = msgpack.Decoder(AppUser).decode


async def _cache_user_set(user_id: str, value: AppUser) -> None:
    await dl.auth_appuser.set(user_id, _default_expire, msgpack_encoder(value))


async def _cache_user_get(user_id: str) -> AppUser | None:
    ok, data = await dl.auth_appuser.get(user_id)
    if ok:
        return appuser_decode(data)
    return None


async def delete_all_db_cache(user_id: str) -> None:
    await gather(
        dl.auth_appuser.delete(user_id),
        dl.auth_exists.delete(user_id),
    )


async def jwt_exists_user_cache(user_id: str) -> bool:  # Bare minimum
    ok, _ = await dl.auth_exists.get(user_id)
    if ok:
        return True
    if await exists_user_id(user_id):
        fire_forget_coro(dl.auth_exists.set(user_id, _default_expire, None))
        return True
    return False


async def upsert_token_valid_from_date(user_id: str) -> None:
    """
    Upsert the token valid from date.

    Use username from db to keep consistent state.

    Call this function to set the date which tokens are valid from.
    Check using iat-claim in the token.
    """
    await DB.upsert_token_valid_from_date(user_id)


async def get_token_valid_from_date(user_id: str) -> DateTimeUTC:
    return await DB.get_token_valid_from_date(user_id)


async def get_user_name(user_id: str) -> str | None:
    return await DB.get_user_name(user_id)


async def get_user_modified(user_id: str) -> DateTimeUTC | None:
    return await DB.get_user_modified(user_id)


async def exists_mail(mail: str) -> bool:
    return await DB.exists_mail(mail)


async def exists_name(name: str) -> bool:
    return await DB.exists_name(name)


async def exists_user_id(user_id: str) -> bool:
    return await DB.exists_user_id(user_id)


async def insert_user(login: str, mail: str | None, hash_b64_pwd: str, created_by_user_id: str) -> UserID | None:
    """Returns generated user id"""
    return await DB.insert_user(login, mail, hash_b64_pwd, created_by_user_id, UserRolesEnum.USER)


async def delete_user(user_id: str) -> None:
    await gather(
        DB.delete_user(user_id),
        delete_all_db_cache(user_id),
    )


async def replace_userrole(
    user_id: str,
    role: UserRolesEnum,
    to_replace: UserRolesEnum,
    end_date: DateT,
    given_by_user_id: str,
):
    await DB.replace_userrole(user_id, role, to_replace, end_date, given_by_user_id)
    if userobj := await _cache_user_get(user_id):
        userobj.roles.remove(to_replace)
        userobj.roles.append(role)
        await _cache_user_set(user_id, userobj)


async def insert_userrole(user_id: str, role: UserRolesEnum, end_date: DateT, given_by_user_id: str) -> None:
    await DB.insert_userrole(user_id, role, end_date, given_by_user_id)
    if userobj := await _cache_user_get(user_id):
        userobj.roles.append(role)
        await _cache_user_set(user_id, userobj)


async def delete_userrole(user_id: str, role: UserRolesEnum) -> None:
    await DB.delete_userrole(user_id, role)
    if userobj := await _cache_user_get(user_id):
        userobj.roles.remove(role)
        await _cache_user_set(user_id, userobj)


async def get_user(user_id: str) -> User | None:
    return await DB.get_user(user_id)


async def get_user_id(name: str) -> str | None:
    return await DB.get_user_id(name)


async def get_userid_roles_pwd(
    login: str,
    login_type: LoginTEnum,
    filter_roles: Iterable[UserRolesEnum],
    disjunctive_select: bool = False,
) -> UserID_Result[tuple[Password, UserRolesAPIStruct]] | None:
    """True, can be seen as "ANY ROLE MATCH USERS" | Otherwise, "ALL ROLES HAS TO MATCH"""
    return await DB.get_userid_roles_pwd(login, login_type, filter_roles, disjunctive_select)


async def get_user_login(user_id: str) -> UserLogin | None:
    return await DB.get_user_login(user_id)


async def get_app_user(
    user_id: str, filter_roles: Iterable[UserRolesEnum] = (), disjunctive_select: bool = False
) -> AppUser | None:
    return await DB.get_app_user(user_id, filter_roles, disjunctive_select)


async def get_app_user_cache(
    user_id: str, filter_roles: Iterable[UserRolesEnum] = (), disjunctive_select: bool = False
) -> AppUser | None:
    """This caches the user in cache db for a limited period.
    It also uses the stored db.name to store and refetch. i.e case sensitive
    """
    try:
        if result := await _cache_user_get(user_id):
            if result.filter_roles(filter_roles, disjunctive_select):
                return result
        elif result := await get_app_user(user_id, filter_roles, disjunctive_select):
            await _cache_user_set(user_id, result)
            return result
        return None
    except:
        print(__import__("traceback").print_exc(), file=__import__("sys").stderr)
        raise
    return None


async def get_user_data(user_id: str) -> UserData | None:
    return await DB.get_user_data(user_id)


async def get_user_registration(user_id: str) -> UserRegistration | None:
    return await DB.get_user_registration(user_id)


async def get_all_users(limit=10, offset=0, asc=True) -> list[AllUserView]:
    return await DB.get_all_user_view(limit, offset, asc)


async def search_user(name_or_email: str, limit=10, exact_match: bool = False) -> list[AllUserView]:
    return await DB.search_user(name_or_email, limit, exact_match)


async def update_user_modified(user_id: str) -> None:
    return await DB.update_user_modified(user_id, datetime.now(UTC))


async def delete_mail(user_id: str) -> None:
    return await DB.delete_mail(user_id)


async def update_mail(user_id: str, mail: str) -> None:
    return await DB.update_mail(user_id, mail)


async def update_name(user_id: str, name: str) -> None:
    return await DB.update_name(user_id, name)


async def update_data_name(user_id: str, name: str) -> None:
    return await DB.update_data_name(user_id, name)


async def update_pwd(user_id: str, password: str) -> None:
    return await DB.update_pwd(user_id, password)


async def number_of_users() -> int:
    return await DB.number_of_users()


async def query(query: str, query_args: dict | None = None):
    return await DB.query(query=query, query_args=query_args)
