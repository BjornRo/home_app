from datetime import UTC, datetime
from typing import TypedDict, Unpack

import aiosqlite
import msgspec
from core import enums, exceptions, types
from storage.db import tables
from storage.db.sql.sqlite import SQLite
from utils import time_helpers

from appdata import shared  # type: ignore


class UpdateRoleField(TypedDict, total=False):
    valid_from: shared.DateTimeUTC
    valid_to: types.DateT


class UserRoleRepository(msgspec.Struct, gc=False):
    db: SQLite

    # region: Create
    async def insert_user_role(
        self,
        user_id: types.UserID,
        role: enums.UserRoles,
        valid_from: shared.DateTimeUTC | None,
        valid_to: types.DateT,
        given_by: types.UserID | None = None,
    ):
        """
        Raises:
            IntegrityError: if value already exists
        """
        now = datetime.now(UTC)
        start_time = shared.datetime_to_isofmtZ(valid_from) if valid_from else time_helpers.DATETIME_MIN_STR
        end_time = time_helpers.generate_end_date(now, valid_to)
        query = (
            f"INSERT INTO {tables.Has_Role.__name__}"
            " (valid_from, valid_to, created_date, user_id, role_name, given_by) "
            f"VALUES ('{start_time}', '{end_time}', '{shared.datetime_to_isofmtZ(now)}', ?, ?, ?)"
        )

        try:
            await self.db.execute_void(query, (user_id, role, given_by))
        except aiosqlite.IntegrityError as e:
            raise exceptions.IntegrityError(str(e)) from e

    # endregion
    # region: Read
    async def get_user_roles(self, user_id: types.UserID):
        query = f"SELECT * FROM {tables.Has_Role.__name__} WHERE user_id = ?"
        return [msgspec.convert(row, type=tables.Has_Role) for row in await self.db.fetch_all(query, (user_id,))]

    async def get_user_valid_roles(self, user_id: types.UserID):
        now = shared.datetime_now_isofmtZ()
        query = (
            f"SELECT role_name FROM {tables.Has_Role.__name__} "
            f"WHERE user_id = ? AND valid_from <= '{now}' AND valid_to >= '{now}'"
        )
        return [enums.UserRoles(row["role_name"]) for row in await self.db.fetch_all(query, (user_id,))]

    async def find_user_ids_by_role(self, role: enums.UserRoles) -> list[types.UserID]:
        query = f"SELECT user_id FROM {tables.Has_Role.__name__} WHERE role_name = ?"
        return await self.db.fetch_all(query, (role,))  # type: ignore

    # endregion
    # region: Update
    async def update_role(self, user_id: types.UserID, role: enums.UserRoles, **fields: Unpack[UpdateRoleField]):
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

        query = f"UPDATE {tables.Has_Role.__name__} SET {",".join(clauses)} WHERE user_id = ? AND role_name = ?"
        await self.db.execute_void(query, (user_id, role))

    async def replace_role(
        self,
        user_id: types.UserID,
        old_role: enums.UserRoles,
        new_role: enums.UserRoles,
        given_by: types.UserID | None = None,
    ):
        """
        Raises:
            IntegrityError: if value already exists
        """
        now = shared.datetime_now_isofmtZ()

        query = (
            f"UPDATE {tables.Has_Role.__name__}"
            " SET role_name = ?, given_by = ?, created_date = ?"
            " WHERE user_id = ? AND role_name = ?"
        )
        try:
            await self.db.execute_void(query, (new_role, given_by, now, user_id, old_role))
        except aiosqlite.IntegrityError as e:
            raise exceptions.IntegrityError(str(e)) from e

    # endregion
    # region: Delete
    async def delete_role(self, user_id: types.UserID, role: enums.UserRoles):
        query = f"DELETE FROM {tables.Has_Role.__name__} WHERE user_id = ? AND role_name = ?"
        await self.db.execute_void(query, (user_id, role))
