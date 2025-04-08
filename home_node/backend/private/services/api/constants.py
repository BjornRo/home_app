from datetime import UTC, datetime
from os import environ

from mytypes import DateTimeUTC

MIN_PASSWORD_LENGTH = 8

DB_URI = environ.get("DB_URI", "app.db")
DB_FILE = environ.get("DB_FILE", "app.db")
DATA_PATH = environ.get("DATA_PATH", "/appdata/")


HEADER_SERVICE_KEY = "X-Service"
HEADER_IP_KEY = "X-Real-IP"

LOGGING_ONLINE_EXPIRY_SEC = 60


MAX_LOGIN_TIMEOUT = 3600
MAX_LOGIN_ATTEMPS_PER_IP = 5


def _load_config():
    from tomllib import load
    from typing import cast

    __import__("sys").path.append("/")  # To import schema. Can be "DATA_PATH", but "/" for linting
    from appdata.cfg_schema import FileData

    with open(DATA_PATH + "default.toml", "rb") as f:
        cfg = cast(FileData, load(f))
    return cfg["mail"], cfg["hostname"]


MAIL_SETTINGS, HOSTNAME = _load_config()

INVALID_NAMES = {"root", "admin", "user", "guest", "login", "mod", "moderator", "null", "none", "administrator"}

DEFAULT_SECURITY_TAG = [{"AccessToken": []}, {"BearerToken": []}]

DATETIME_MIN: DateTimeUTC = datetime.fromtimestamp(0, UTC)
DATETIME_MAX: DateTimeUTC = datetime.fromisoformat("9999-12-31T23:59:59Z")
