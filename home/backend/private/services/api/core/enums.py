from __future__ import annotations

from enum import StrEnum


class UserRoles(StrEnum):
    ROOT = "root"
    MOD = "mod"  # Moderator
    USER = "user"

    @staticmethod
    def convert(roles: list[str] | list[UserRoles]) -> list[UserRoles]:
        return [UserRoles(r) for r in roles]
