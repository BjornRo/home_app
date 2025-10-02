from datetime import UTC, datetime
from typing import TypedDict, Unpack

import aiosqlite
import msgspec
from core import exceptions, paths, types
from core.models import AppUserACL
from internal.constants import DB_INTERNAL
from storage.db import tables
from storage.db.sql.sqlite import SQLite
from utils import time_helpers

from appdata import shared  # type: ignore


class UpdateUserServiceField(TypedDict, total=False):
    rwx: types.RWX
    valid_from: shared.DateTimeUTC
    valid_to: types.DateT


class UpdateServiceFields(TypedDict, total=False):
    name: str
    url: str | None
    description: str


class UserACLRepository(msgspec.Struct, gc=False):
    db: SQLite

    # region: Create
    async def register_service(self, service_name: str, url: str | None, description: str):
        query = "INSERT OR IGNORE INTO service (name, url, description, created_date) VALUES (?,?,?,?)"
        # query = (
        #     "INSERT INTO service (name, url, description, created_date) VALUES (?,?,?,?)"
        #     " ON CONFLICT(name) DO UPDATE SET url = EXCLUDED.url, description = EXCLUDED.description"
        # )
        await self.db.execute_void(query, (service_name, url, description, shared.datetime_now_isofmtZ()))

    async def insert_service(
        self,
        user_id: types.UserID,
        service_name: str,
        rwx: types.RWX,
        valid_from: shared.DateTimeUTC | None,
        valid_to: types.DateT,
        given_by: types.UserID | None = None,
    ):
        now = datetime.now(UTC)
        start_time = shared.datetime_to_isofmtZ(valid_from) if valid_from else time_helpers.DATETIME_MIN_STR
        end_time = time_helpers.generate_end_date(now, valid_to)
        _now = shared.datetime_to_isofmtZ(now)
        query = (
            f"INSERT INTO {tables.Has_Service.__name__}"
            " (user_id, service_name, rwx, valid_from, valid_to, given_by, created_date) "
            f"VALUES (?,?,?,?,?,?,?)"
        )

        try:
            await self.db.execute_void(
                query, (user_id, service_name, rwx.to_int(), start_time, end_time, given_by, _now)
            )
        except aiosqlite.IntegrityError as e:
            raise exceptions.IntegrityError(str(e)) from e

    # endregion
    # region: Read
    async def get_service(self, service_name: str):
        query = f"SELECT * FROM {tables.Service.__name__} WHERE name = ?"
        if row := await self.db.fetch_one(query, (service_name,)):
            return msgspec.convert(row, type=tables.Service)

    async def get_all_services(self):
        query = f"SELECT * FROM {tables.Service.__name__}"
        return [msgspec.convert(row, type=tables.Service) for row in await self.db.fetch_all(query)]

    async def get_all_service_names(self) -> list[str]:
        query = f"SELECT name FROM {tables.Service.__name__}"
        return [row["name"] for row in await self.db.fetch_all(query)]

    async def get_user_services(self, user_id: types.UserID):
        query = f"SELECT * FROM {tables.Has_Service.__name__} WHERE user_id = ?"
        return [msgspec.convert(row, type=tables.Has_Service) for row in await self.db.fetch_all(query, (user_id,))]

    async def get_user_valid_services(self, user_id: types.UserID):
        """RWX 0 should mean no access but granted service, like a soft ban"""
        now = shared.datetime_now_isofmtZ()
        query = (
            f"SELECT LOWER(service_name) AS name, rwx FROM {tables.Has_Service.__name__} "
            f"WHERE user_id = ? AND valid_from <= '{now}' AND valid_to >= '{now}' AND rwx != 0"
        )
        rows = await self.db.fetch_all(query, (user_id,))
        trans: AppUserACL = {row["name"]: types.RWX.from_int(row["rwx"]) for row in rows}
        return trans

    async def find_user_ids_by_service(self, service_name: str) -> list[types.UserID]:
        query = f"SELECT user_id FROM {tables.Has_Service.__name__} WHERE service_name = ?"
        return await self.db.fetch_all(query, (service_name,))  # type: ignore

    # endregion
    # region: Update
    async def update_user_service(
        self, user_id: types.UserID, service_name: str, **fields: Unpack[UpdateUserServiceField]
    ):
        if not fields:
            raise exceptions.UserInputError("No fields given")

        now = datetime.now(UTC)
        clauses = []
        if field := fields.get("valid_from"):
            if field <= now:
                raise exceptions.UserInputError("Not allowed to move valid date in the past")
            clauses.append(f"valid_from = '{shared.datetime_to_isofmtZ(field)}'")
        if "valid_to" in fields:
            clauses.append(f"valid_to = '{time_helpers.generate_end_date(now, fields['valid_to'])}'")
        if field := fields.get("rwx"):
            value = field.to_int()
            if not (0 <= value <= 7):
                raise exceptions.UserInputError("Invalid RWX value")
            clauses.append(f"rwx = {value}")

        query = f"UPDATE {tables.Has_Service.__name__} SET {",".join(clauses)} WHERE user_id = ? AND service_name = ?"
        await self.db.execute_void(query, (user_id, service_name))

    async def update_service(self, service_name: str, **fields: Unpack[UpdateServiceFields]):
        if not fields:
            raise exceptions.UserInputError("No fields given")

        clauses = [f"{field} = :{field}" for field in fields.keys()]
        query = f"UPDATE {tables.Service.__name__} SET {",".join(clauses)} WHERE name = :sn"
        if (new_service_name := fields.get("name")) is not None:
            internal_query = "UPDATE internal.service_ownership SET service_name = ? WHERE service_name = ?"
            async with self.db.connect() as conn:
                try:
                    await conn.execute("ATTACH DATABASE ? AS internal", (paths.DATA_PATH + DB_INTERNAL,))
                    await conn.execute("PRAGMA internal.foreign_keys = ON")
                    await conn.execute("BEGIN")
                    await conn.execute(query, dict(**fields, sn=service_name))
                    await conn.execute(internal_query, (new_service_name, service_name))
                    await conn.commit()
                except aiosqlite.IntegrityError as e:
                    await conn.rollback()
                    raise exceptions.IntegrityError(str(e)) from e
                except Exception as e:
                    shared.print_err(e)
                    await conn.rollback()
                    raise
                finally:
                    await conn.execute("DETACH DATABASE internal")
            return None

        await self.db.execute_void(query, dict(**fields, sn=service_name))

    # endregion
    # region: Delete
    async def delete_service_from_user(self, user_id: types.UserID, service_name: str):
        query = f"DELETE FROM {tables.Has_Service.__name__} WHERE user_id = ? AND service_name = ?"
        await self.db.execute_void(query, (user_id, service_name))

    async def unregister_service(self, service_name: str):
        async with self.db.connect() as conn:
            try:
                await conn.execute("ATTACH DATABASE ? AS internal", (paths.DATA_PATH + DB_INTERNAL,))
                await conn.execute("PRAGMA internal.foreign_keys = ON")
                await conn.execute("BEGIN")
                await conn.execute(f"DELETE FROM {tables.Service.__name__} WHERE name = ?", (service_name,))
                await conn.execute("DELETE FROM internal.service_ownership WHERE service_name = ?", (service_name,))
                await conn.commit()
            finally:
                await conn.execute("DETACH DATABASE internal")
