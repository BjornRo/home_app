from collections.abc import Iterable
from typing import Any, Unpack

import aiosqlite
import internal.constants
import msgspec
from core import exceptions, paths
from internal import internal_models
from internal.storage import internal_tables
from internal.storage.sqlite_basic import INTERNALSQLite
from storage.db.sql.sqlite import SQLite
from utils import helpers, validation

from appdata import internal_shared, shared  # type:ignore


class InternalUserRepository(msgspec.Struct, gc=False):
    db: SQLite | INTERNALSQLite

    # region: Create
    async def create_user(self, username: str, pwd: str, enabled: bool):
        """
        Raises:
            IntegrityError
            ValidationError
        """
        validation.validate_name(username)
        validation.validate_password(pwd)
        pwd = await helpers.hash_password_b64_threaded(pwd)
        try:
            async with self.db.connect() as conn:
                await conn.execute(
                    f"INSERT INTO {internal_tables.User.__name__} (user_id, pwd, enabled) VALUES (?,?,?)",
                    (username, pwd, enabled),
                )
                await conn.execute(
                    f"INSERT INTO {internal_tables.User_Registration.__name__} (user_id, created_date) VALUES (?,?)",
                    (username, shared.datetime_now_isofmtZ()),
                )
                await conn.commit()
        except aiosqlite.IntegrityError as e:
            raise exceptions.IntegrityError(str(e)) from e

    async def insert_role(self, username: str, role: internal_shared.InternalRolesEnum):
        """
        Raises:
            IntegrityError
        """
        query = f"INSERT INTO {internal_tables.Has_Role.__name__} (user_id, role_name, created_date) VALUES (?,?,?)"
        try:
            await self.db.execute_void(query, (username, role, shared.datetime_now_isofmtZ()))
        except aiosqlite.IntegrityError as e:
            raise exceptions.IntegrityError(str(e)) from e

    async def insert_service_serving(self, username: str, service_name: str):
        query = f"INSERT INTO {internal_tables.Service_Ownership.__name__} (user_id, service_name) VALUES (?,?)"

        async with self.db.connect() as conn:
            try:
                await conn.execute("ATTACH DATABASE ? as app", (paths.DATA_PATH + paths.DB_APP))
                async with conn.execute("SELECT 1 FROM app.service WHERE name = ?", (service_name,)) as cur:
                    if await cur.fetchone() is None:
                        raise exceptions.NotFoundError(f"Service '{service_name}' does not exist in app DB")
                await conn.execute("PRAGMA app.foreign_keys = ON")
                await conn.execute("BEGIN")
                await conn.execute(query, (username, service_name))
                await conn.commit()
            except aiosqlite.IntegrityError as e:
                await conn.rollback()
                raise exceptions.IntegrityError(str(e)) from e
            except Exception as e:
                shared.print_err(e)
                await conn.rollback()
                raise
            finally:
                await conn.execute("DETACH DATABASE app")

    # endregion
    # region: Read

    async def get_user(self, username: str):
        query = f"SELECT * FROM {internal_tables.User.__name__} WHERE user_id = ?"
        if row := await self.db.fetch_one(query, (username,)):
            return msgspec.convert(row, type=internal_tables.User)

    async def get_users(self):
        rows = await self.db.fetch_all(f"SELECT * FROM {internal_tables.User.__name__}")
        return [msgspec.convert(row, type=internal_tables.User) for row in rows]

    async def get_user_has_roles(self, username: str):
        query = f"SELECT * FROM {internal_tables.Has_Role.__name__} WHERE user_id = ?"
        rows = await self.db.fetch_all(query, (username,))
        return [msgspec.convert(row, type=internal_tables.Has_Role) for row in rows]

    async def get_user_roles(self, username: str):
        """Only get if user is already authed!"""
        query = f"SELECT role_name FROM {internal_tables.Has_Role.__name__} WHERE user_id = ?"
        rows = await self.db.fetch_all(query, (username,))
        return [internal_shared.InternalRolesEnum(row["role_name"]) for row in rows]

    async def exists_user(self, username: str):
        query = f"SELECT 1 FROM {internal_tables.User.__name__} WHERE user_id = ?"
        return await self.db.fetch_one(query, (username,)) is not None

    async def get_all_users_view(self):
        rows = await self.db.fetch_all(_get_all_user_view_query("ORDER BY ur.created_date"))
        return [_alluserview_query_row_to_struct(row) for row in rows]

    async def get_all_user_view(self, username: str):
        if row := await self.db.fetch_one("WHERE user_id = ?", (username,)):
            return _alluserview_query_row_to_struct(row)

    async def search_user(self, search_term: str):
        rows = await self.db.fetch_all("WHERE u.user_id LIKE ? COLLATE NOCASE", (f"%{search_term}%",))
        return [_alluserview_query_row_to_struct(row) for row in rows]

    async def get_serving_service(self, username: str) -> list[str]:
        query = f"SELECT LOWER(service_name) FROM {internal_tables.Service_Ownership.__name__} WHERE user_id = ?"
        return [row["service_name"] for row in await self.db.fetch_all(query, (username,))]

    # endregion
    # region: Update

    async def update_user(self, username: str, **fields: Unpack[internal_models.InternalUserUpdate]):
        """
        Raises:
            UserInputError: if no fields are given
            IntegrityError: if value already exists
            ValidationError
        """
        if not fields:
            raise exceptions.UserInputError("No fields")

        if pwd := fields.get("pwd"):
            validation.validate_password(pwd)
            fields["pwd"] = await helpers.hash_password_b64_threaded(pwd)
        if uname := fields.get("user_id"):
            validation.validate_name(uname)

        _fields = ",".join(f"{col} = :{col}" for col in fields.keys())
        query = f"UPDATE user SET {_fields} WHERE user_id = :username"
        try:
            await self.db.execute_void(query, dict(**fields, username=username))
        except aiosqlite.IntegrityError as e:
            raise exceptions.IntegrityError(str(e)) from e

    async def update_service_ownership_owner(self, service_name: str, new_username: str):
        query = "UPDATE service_ownership SET user_id = ? WHERE service_name = ?"
        await self.db.execute_void(query, (new_username, service_name))

    # endregion
    # region: Delete

    async def delete_role(self, username: str, role: internal_shared.InternalRolesEnum):
        query = f"DELETE FROM {internal_tables.Has_Role.__name__} WHERE user_id = ? AND role_name = ?"
        await self.db.execute_void(query, (username, role))

    async def delete_user(self, username: str):
        await self.db.execute_void(f"DELETE FROM {internal_tables.User.__name__} WHERE user_id = ?", (username,))

    async def delete_service_serving(self, username: str, service_name: str):
        query = f"DELETE FROM {internal_tables.Service_Ownership.__name__} WHERE user_id = ? AND service_name = ?"
        await self.db.execute_void(query, (username, service_name))

    # endregion


# region: Helpers


def _get_all_user_view_query(query_filter: str = ""):
    """
    `Tables`:
        `ur`: User_Registration
        `u`: User
    """
    return (
        " WITH roles_agg AS ("
        "   SELECT user_id, json_group_array(role_name) AS roles"
        f"  FROM {internal_tables.Has_Role.__name__}"
        "   GROUP BY user_id"
        " ),"
        " WITH serving_agg AS ("
        "   SELECT user_id, json_group_array(LOWER(service_name)) AS services"
        f"  FROM {internal_tables.Service_Ownership.__name__}"
        "   GROUP BY user_id"
        " ),"
        " paged_users AS ("
        "   SELECT u.user_id, u.enabled, reg.created_date"
        f"  FROM {internal_tables.User.__name__} u"
        f"  JOIN {internal_tables.User_Registration.__name__} reg ON u.user_id = reg.user_id"
        f"  {query_filter}"
        " )"
        " SELECT "
        "   u.user_id,"
        "   u.enabled,"
        "   u.created_date,"
        "   COALESCE(r.roles, '[]') AS roles"
        "   COALESCE(s.services, '[]') AS services"
        " FROM paged_users u"
        " LEFT JOIN roles_agg r ON u.user_id = r.user_id"
        " LEFT JOIN serving_agg s ON u.user_id = s.user_id"
    )


def _alluserview_query_row_to_struct(row: dict[str, Any]):
    # for s in ("roles", "services"):
    #     concat_row: str = row[s]
    #     row[s] = concat_row.split("|") if concat_row else []
    return msgspec.convert(row, type=internal_models.AllUserView, strict=False)


# endregion
