import msgspec
from core import types
from services.token_service import TokenService
from storage.db.repositories.user_ban_repository import UserBanRepository


class BanService(msgspec.Struct):
    token_service: TokenService
    repo_ban: UserBanRepository

    async def ban_user(
        self,
        user_id: types.UserID,
        banned_by: types.UserID | None,
        reason: str,
        end_time: types.DateT,
    ):
        await self.token_service.revoke_tokens(user_id)
        await self.repo_ban.ban_user(user_id, banned_by, reason, end_time)

    async def is_user_banned(self, user_id: types.UserID):
        return await self.repo_ban.is_user_banned(user_id)

    async def unban_user(self, user_id: types.UserID, unbanned_by: types.UserID | None):
        return await self.repo_ban.unban_user(user_id, unbanned_by)
