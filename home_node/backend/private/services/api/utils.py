import asyncio
import base64
from collections.abc import Awaitable, Callable, Coroutine
from concurrent.futures.process import ProcessPoolExecutor
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from re import compile as re_compile
from smtplib import SMTP_SSL
from ssl import create_default_context
from typing import Literal, cast

import msgspec
from bcrypt import checkpw, gensalt, hashpw
from constants import (
    DATETIME_MAX,
    HEADER_SERVICE_KEY,
    INVALID_NAMES,
    MIN_PASSWORD_LENGTH,
)
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from litestar import Request, Response
from litestar.connection import ASGIConnection, Request
from litestar.datastructures.headers import Headers
from litestar.enums import MediaType
from litestar.exceptions import ClientException
from mytypes import DateT, DateTimeUTC, KeyData, Password, Singleton

# mail_validate = re.compile(r"(^[\w\.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]*[a-zA-Z0-9]$)")
mail_validate = re_compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")
name_validate = re_compile(r"(^([\._]?[a-zA-Z]+[0-9]*)+[\._]?$)")
guid_validate = re_compile(r"^[a-z0-9]+$")

msgpack_encoder = msgspec.msgpack.Encoder().encode

resp401 = Response({"status_code": 401, "detail": "Unauthorized"}, media_type=MediaType.JSON, status_code=401)

# A route can add their schema to this,
# then it gets executed on_start.
db_schema_init_internal: list[str] = []
db_schema_init_api: list[str] = []


def _get_secrets():
    with open("secrets", "rt") as f:
        f.readline()  # Date
        secrets: list[bytes] = []
        while sec := f.readline():
            secrets.append(bytes(map(int, sec.split(","))))
        return secrets


secrets = _get_secrets()


async def pool_runner(func: Callable, *args, _pool=ProcessPoolExecutor(2)):
    return await asyncio.get_event_loop().run_in_executor(_pool, func, *args)


def get_token_str(headers: Headers) -> str | None:
    try:
        prefix, token_str = headers["Authorization"].split(" ")
        if prefix.lower() == "bearer":
            return token_str
    except:
        pass
    return None


async def check_password_b64(pwd: Password, hash_pwd: str | None) -> bool:
    return await pool_runner(_check_password_b64, pwd, hash_pwd)


def _check_password_b64(pwd: Password, hash_pwd: str | None) -> bool:
    # Base64(bcrypt.hashpw(b"", bcrypt.gensalt()))
    h64 = hash_pwd or "JDJiJDEyJEU5Q0U3azFlcHdZTjkuQkwuSWZMemVucWYuTWF1dzRGS0c3aVExUjZnRmFtd3dnSHJycXNp"
    _pwd = pwd.encode()
    _hash_pwd = base64.b64decode(h64)
    return checkpw(_pwd, _hash_pwd) and bool(hash_pwd)


def fire_forget_coro(coro: Coroutine | Awaitable, name: str | None = None, _tasks: set[asyncio.Task] = set()):
    task = asyncio.create_task(coro, name=name)  # type:ignore
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def hash_password_b64(password: str) -> str:
    return await pool_runner(_hash_password_b64, password)


def _hash_password_b64(password: str) -> str:
    return base64.b64encode(hashpw(password.encode(), gensalt())).decode()


def validate_mail(mail: str) -> None:
    if (not (6 <= len(mail) <= 50)) or mail_validate.match(mail) is None:
        raise ClientException("Valid mail is required")


def validate_name(name: str, min_len=1, max_len=34) -> None:
    if not (min_len <= len(name) <= max_len):
        raise ClientException(f"Username must be between {min_len} and {max_len} characters long")

    name_low = name.lower().strip()
    if name_low in INVALID_NAMES:
        raise ClientException("Username is not allowed")

    if name_validate.match(name) is None or not any(c.isalpha for c in name):
        raise ClientException("Here is the regex D: =>" + name_validate.pattern)


def validate_password(password: str) -> None:
    if not (MIN_PASSWORD_LENGTH < len(password) <= 100):
        raise ClientException(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    if not (
        any(c.isupper() for c in password) and any(c.islower() for c in password) and any(c.isdigit() for c in password)
    ):
        raise ClientException("Password must contain at least one number, and capital and lowercase letter")


def validate_guid(guid: str, exact_len: bool = False) -> None:
    if guid_validate.match(guid) is None or (exact_len and len(guid) != 20):
        raise ClientException("Is not UID")


def load_jwtkeys_json(key_file: str) -> KeyData:
    with open(key_file, "rb") as f:
        data = msgspec.json.decode(f.read(), type=KeyData)
    try:
        _validate_keydata(data)
        return data
    except InvalidSignature:
        raise


def _validate_keydata(data: KeyData, signer="root"):
    """Validate the signed public key"""
    with open(f"/certs/ca/{signer}.crt", "rb") as f:
        root_cert = cast(RSAPublicKey, x509.load_pem_x509_certificate(f.read(), backend=default_backend()).public_key())
    root_cert.verify(
        base64.b64decode(data.public_key_sign),
        (data.created.isoformat().replace("Z", "+00:00") + data.keys.public).encode(),
        padding.PKCS1v15(),
        hashes.SHA384(),
    )


class Mail(metaclass=Singleton):
    __slots__ = ("context", "user", "port", "password", "relay", "noreply", "host")

    def config(self, user: str, password: str, host: str, hostname: str, relay: str, port: int):
        self.context = create_default_context()
        self.user = user
        self.password = password
        self.host = host
        self.noreply = "noreply@" + hostname
        self.relay = user + "@" + relay
        self.port = port

    def send(self, to: str, subject: str, message: str) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.noreply
            msg["To"] = to
            msg.attach(MIMEText(message, "plain"))
            with SMTP_SSL(self.host, self.port, context=self.context) as server:
                server.login(user=self.user, password=self.password)
                server.sendmail(self.relay, to, msg.as_string())
            return True
        except:
            pass
        return False


"""
milliseconds: 3 digits
auto:         6 digits
"""
type _TimeSpec = Literal["minutes", "seconds", "milliseconds", "auto"]


def datetime_to_isoformat(dt: DateTimeUTC, timespec: _TimeSpec = "milliseconds") -> str:
    dt_str = dt.isoformat(timespec=timespec)
    return dt_str[: dt_str.rfind("+")] + "Z"


def datetime_now_utc_isoformat(timespec: _TimeSpec = "milliseconds") -> str:
    return datetime_to_isoformat(datetime.now(UTC), timespec=timespec)


def http_401_resp(request: Request, exc: Exception) -> Response:
    return resp401


def is_local_request(conn: ASGIConnection) -> bool:
    return HEADER_SERVICE_KEY not in conn.headers


def generate_created_end_date(end_date: DateT, created: DateTimeUTC):
    match end_date:  # Generate when a role should end, i.e limited role access.
        case None:
            end_date = DATETIME_MAX
        case timedelta():
            end_date = created + end_date

    if not (created < end_date <= DATETIME_MAX):
        raise ClientException(f"Invalid date given: {created} < {end_date} <= {DATETIME_MAX}")

    return datetime_to_isoformat(created), datetime_to_isoformat(end_date)
