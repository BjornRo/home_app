import asyncio

import msgspec
from services.user_service import UserService
from storage.db.repositories.user_account_repository import UserColumnFetch
from storage.db.repositories.user_ban_repository import UserBanRepository
from utils import helpers

from appdata import shared  # type: ignore


class AuthService(msgspec.Struct):
    user_service: UserService
    repo_ban: UserBanRepository

    async def verify_user(self, user_id: str, password: str):
        user, is_banned = await asyncio.gather(
            self.user_service.get_user("user_id", user_id),
            self.repo_ban.is_user_banned(user_id),
        )
        if user and not is_banned:
            hash_pwd = user.password if user.enabled else None
        else:
            hash_pwd = None
        return await helpers.check_password_b64_threaded(password, hash_pwd)

    async def login_user(self, name_or_mail: str, password: str):
        login_method: UserColumnFetch = "login_mail" if "@" in name_or_mail else "login_name"
        if user := await self.user_service.get_user(login_method, name_or_mail):
            result, is_banned = await asyncio.gather(
                helpers.check_password_b64_threaded(password, user.password),
                self.repo_ban.is_user_banned(user.user_id),
            )
            if result and user.enabled and not is_banned:
                shared.fire_forget_coro(self.user_service.update_user_login_date(user.user_id))
                return user.user_id
        else:
            await helpers.check_password_b64_threaded(password, None)
        return None
