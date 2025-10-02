import ssl
from datetime import timedelta
from typing import Any

from core import paths

from appdata.cfg_schema import FILENAME, load_file  # type: ignore

__CONFIG_FILE = load_file(paths.DATA_PATH + FILENAME)

HOSTNAME = __CONFIG_FILE["hostname"]
MAIL_SETTINGS = __CONFIG_FILE["mail"]

MQTT_SETTINGS: dict[str, Any] = dict(
    username="api",
    hostname=__CONFIG_FILE["mqtt"]["internal"]["hostname"],
    port=__CONFIG_FILE["mqtt"]["internal"]["port"],
    password=[x for x in __CONFIG_FILE["api"]["internal_users"] if x["name"] == "api"][0]["password"],
    tls_context=ssl.create_default_context(cafile=paths.CA_FILEPATH),
)

INTERNAL_MQTT_DEVICES_SETTINGS = __CONFIG_FILE["mqtt"]["publish"]


MIN_PASSWORD_LENGTH = 8

CACHE_DEFAULT_EXPIRY = 300  # seconds
# CACHE_TOKEN_EXPIRY = int(timedelta(days=7).total_seconds())

LOGGING_ONLINE_EXPIRY_SEC = 60  # How long time a user

MAX_LOGIN_TIMEOUT = 3600
MAX_LOGIN_ATTEMPS_PER_IP = 5
