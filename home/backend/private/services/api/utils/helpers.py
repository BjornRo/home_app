import asyncio
import base64
import secrets
import time
from concurrent.futures.process import ProcessPoolExecutor
from typing import Any, Callable, cast

import msgspec
from bcrypt import checkpw, gensalt, hashpw
from core import types
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

process_pool = ProcessPoolExecutor(2)


async def pool_runner[T](func: Callable[..., T], *args):
    return await asyncio.get_event_loop().run_in_executor(process_pool, func, *args)


async def check_password_b64_threaded(pwd: types.Password, hash_pwd: str | None) -> bool:
    return await pool_runner(check_password_b64, pwd, hash_pwd)


def check_password_b64(pwd: types.Password, hash_pwd: str | None) -> bool:
    # Base64(bcrypt.hashpw(b"", bcrypt.gensalt()))
    h64 = hash_pwd or "JDJiJDEyJEU5Q0U3azFlcHdZTjkuQkwuSWZMemVucWYuTWF1dzRGS0c3aVExUjZnRmFtd3dnSHJycXNp"
    _pwd = pwd.encode()
    _hash_pwd = base64.b64decode(h64)
    return checkpw(_pwd, _hash_pwd) and bool(hash_pwd)


async def hash_password_b64_threaded(password: str) -> str:
    return await pool_runner(hash_password_b64, password)


def hash_password_b64(password: str) -> str:
    return base64.b64encode(hashpw(password.encode(), gensalt())).decode()


def load_jwtkeys_json(key_file: str) -> types.KeyData:
    with open(key_file, "rb") as f:
        data = msgspec.json.decode(f.read(), type=types.KeyData)
    try:
        validate_keydata(data)
        return data
    except InvalidSignature:
        raise


def validate_keydata(data: types.KeyData, signer="root"):
    """Validate the signed public key"""
    with open(f"/certs/ca/{signer}.crt", "rb") as f:
        root_cert = cast(RSAPublicKey, x509.load_pem_x509_certificate(f.read(), backend=default_backend()).public_key())
    root_cert.verify(
        base64.b64decode(data.public_key_sign),
        (data.created.isoformat().replace("+00:00", "") + "Z" + data.keys.public).encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )


def parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except:
        return None


def uuid7() -> str:
    ts = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    ts_high = ts >> 16
    ts_low = ts & 0xFFFF
    version = 0x7000 | (secrets.randbits(12) & 0x0FFF)
    variant = 0x8000 | (secrets.randbits(14) & 0x3FFF)
    rand_low = secrets.randbits(48)
    return f"{ts_high:08x}-{ts_low:04x}-{version:04x}-{variant:04x}-{rand_low:012x}"
