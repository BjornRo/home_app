import os
import secrets
from datetime import UTC, datetime, timedelta

import msgspec
from appdata import shared  # type: ignore

type TokenType = dict[str, list[str]]


class __SecurityTag(msgspec.Struct, gc=False):
    access_token: TokenType
    refresh_token: TokenType


HEADER_SERVICE_KEY = "X-Service"
HEADER_IP_KEY = "X-Real-IP"

REFRESH_TOKEN = "refresh_token"
ACCESS_TOKEN = "access_token"

SECURITY_TAG = __SecurityTag(access_token={"AccessToken": []}, refresh_token={"BearerToken": []})


def __get_secrets(secrets_file=".secrets", n_secrets=8) -> list[bytes]:
    if os.path.isfile(secrets_file):
        with open(secrets_file, "rt") as f:
            date = datetime.fromisoformat(f.readline().strip())
            if date + timedelta(days=90) > datetime.now(UTC):
                return [bytes(map(int, sec.split(","))) for sec in f if sec.strip]
        os.remove(secrets_file)

    _secrets = []
    with open(secrets_file, "wt") as f:
        f.write(shared.datetime_now_isofmtZ() + "\n")
        for _ in range(n_secrets):
            token = secrets.token_bytes(64)
            _secrets.append(token)
            f.write(str(list(token)).replace(" ", "")[1:-1] + "\n")
    return _secrets


SECRETS = __get_secrets()

INVALID_NAMES = {
    "root",
    "admin",
    "user",
    "guest",
    "login",
    "mod",
    "moderator",
    "null",
    "none",
    "administrator",
}
