from datetime import UTC, datetime

import msgspec
from core import types
from storage.db import tables
from storage.db.sql.sqlite import SQLite
from utils import time_helpers

from appdata import shared  # type: ignore


class UserBanRepository(msgspec.Struct, gc=False):
    db: SQLite
    _table = tables.User_Bans
    _table_name = _table.__name__

    # region: Create
    async def ban_user(
        self,
        user_id: types.UserID,
        banned_by: types.UserID | None,
        reason: str,
        end_time: types.DateT,
    ):
        """
        Returns:
            Optional[User_ban]: User ban is returned if ban exists, otherwise inserted.
        """
        now = datetime.now(UTC)
        _end_time = time_helpers.generate_end_date(now, end_time)
        _now = shared.datetime_to_isofmtZ(now)

        query_check = f"SELECT * FROM {self._table_name} WHERE user_id = ? AND is_active = 1 AND end_time > ? LIMIT 1"
        query_insert = (
            f"INSERT INTO {self._table_name} (user_id, is_active, banned_by, unbanned_by, reason, start_time, end_time) "
            "VALUES (?,?,?,?,?,?)"
        )
        async with self.db.connect() as conn:
            async with conn.execute(query_check, (user_id, _now)) as cur:
                if row := await cur.fetchone():
                    return msgspec.convert(row, type=self._table)

            await conn.execute(query_insert, (user_id, True, banned_by, None, reason, _now, _end_time))
            await conn.commit()

    # endregion
    # region: Read
    async def get_user_ban(self, user_id: types.UserID):
        query = f"SELECT * FROM {self._table_name} WHERE user_id = ? AND is_active = 1 AND end_time > ? LIMIT 1"
        if row := await self.db.fetch_one(query, (user_id, shared.datetime_now_isofmtZ())):
            return msgspec.convert(row, type=self._table, strict=False)

    async def is_user_banned(self, user_id: types.UserID):
        query = f"SELECT 1 FROM {self._table_name} WHERE user_id = ? AND is_active = 1 AND end_time > ? LIMIT 1"
        return await self.db.fetch_one(query, (user_id, shared.datetime_now_isofmtZ())) is not None

    async def user_number_of_bans(self, user_id: types.UserID) -> int:
        query = f"SELECT COUNT(*) FROM {self._table_name} WHERE user_id = ? LIMIT 1"
        return await self.db.fetch_one(query, (user_id,))  # type: ignore

    # endregion
    # region: Update
    async def unban_user(self, user_id: types.UserID, unbanned_by: types.UserID | None):
        query = (
            f"UPDATE {self._table_name}"
            " SET is_active = 0, unbanned_by = ? WHERE user_id = ? AND is_active = 1 AND end_time > ?"
        )

        return await self.db.execute_void(query, (unbanned_by, user_id, shared.datetime_now_isofmtZ()))

    async def update_user_ban_end_time(self, user_id: types.UserID, end_time: types.DateT):
        now = datetime.now(UTC)
        _end_time = time_helpers.generate_end_date(now, end_time)

        query = f"UPDATE {self._table_name} SET end_time = ? WHERE user_id = ? AND is_active = 1 AND end_time > ?"
        return await self.db.execute_void(query, (_end_time, user_id, shared.datetime_to_isofmtZ(now)))

    async def update_user_ban_reason(self, user_id: types.UserID, new_reason: str):
        query = f"UPDATE {self._table_name} SET reason = ? WHERE user_id = ? AND is_active = 1 AND end_time > ?"
        return await self.db.execute_void(query, (new_reason, user_id, shared.datetime_now_isofmtZ()))

    # endregion
    # region: Delete
    # endregion
