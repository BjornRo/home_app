from datetime import UTC, datetime

import msgspec
import valkey.asyncio as valkey
from core import types
from storage.db import tables
from storage.db.sql.sqlite import SQLite
from utils import time_helpers

from appdata import shared  # type: ignore


class UserMetaRepository(msgspec.Struct, gc=False):
    db: SQLite
    cache_online_users_counter: valkey.Valkey

    # region: Tokens
    async def get_token_policy(self, user_id: types.UserID):
        query = f"SELECT * FROM {tables.User_Token_Policy.__name__} WHERE user_id = ?"
        if row := await self.db.fetch_one(query, (user_id,)):
            return msgspec.convert(row, type=tables.User_Token_Policy)

    async def get_token_policy_unixtime(self, user_id: types.UserID) -> int:
        query = f"SELECT tokens_valid_after AS date FROM {tables.User_Token_Policy.__name__} WHERE user_id = ?"
        return row["date"] if (row := await self.db.fetch_one(query, (user_id,))) else 0

    async def upsert_tokens_valid_after(self, user_id: types.UserID):
        query = (
            f"INSERT INTO {tables.User_Token_Policy.__name__}"
            " (user_id, tokens_valid_after)"
            " VALUES (?, ?)"
            " ON CONFLICT(user_id) DO UPDATE SET tokens_valid_after = EXCLUDED.tokens_valid_after"
        )

        try:
            await self.db.execute_void(query, (user_id, time_helpers.unixtime()))
        except Exception as e:
            shared.print_err(e)
            raise

    # endregion
    # region: Mail confirmation
    async def mail_store_confirmation(self, user_id: types.UserID, token: str, expiry_date: types.DateT) -> None:
        query = "INSERT INTO mail_confirmation (user_id, token, created_date, expiry_date) VALUES (?,?,?,?)"
        now = datetime.now(UTC)
        end_time = time_helpers.generate_end_date(now, expiry_date)
        async with self.db.connect() as conn:
            try:
                await conn.execute(query, (user_id, token, shared.datetime_to_isofmtZ(now), end_time))
                await conn.commit()
            except Exception as e:
                shared.print_err(e)
                raise

    async def mail_confirm_user(self, token: str):
        query = "DELETE FROM mail_confirmation WHERE token = ? RETURNING user_id, expiry_date"
        ok = False
        try:
            async with self.db.connect() as conn:
                async with conn.execute(query, (token,)) as cur:
                    if row := await cur.fetchone():
                        if datetime.now(UTC) <= datetime.fromisoformat(row["expiry_date"]):
                            query2 = f"UPDATE {tables.User.__name__} SET enabled = 1 WHERE user_id = ?"
                            ok = True
                        else:
                            query2 = f"DELETE FROM {tables.User.__name__} WHERE user_id = ?"
                        await cur.execute(query2, (row["user_id"],))
            return ok
        except Exception as e:
            shared.print_err(e)
            raise
        finally:
            await conn.commit()

    # endregion
    # region: Misc
    async def number_of_users(self) -> int:
        async with self.db.connect() as conn:
            async with conn.execute("SELECT COUNT(*) FROM user") as cur:
                return (await cur.fetchone())[0]  # type: ignore

    async def online_users(self) -> int:
        return await self.cache_online_users_counter.dbsize()

    # endregion

    # --- Future misc metadata ---
    # async def get_last_login(self, user_id: types.UserID) -> types.DateTimeUTC | None: ...
    # async def set_last_login(self, user_id: types.UserID) -> None: ...
