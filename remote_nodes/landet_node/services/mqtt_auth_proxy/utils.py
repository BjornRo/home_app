__import__("sys").path.append("/")  # To import from appdata. "/" for linting
import asyncio
import time
from datetime import timedelta
from enum import StrEnum
from hashlib import sha384 as sha
from http.cookiejar import DefaultCookiePolicy
from os import environ, path, urandom
from typing import Coroutine, Literal, TypedDict, cast

import ujson as json
from aiosqlite import connect
from httpx import AsyncClient, Response

from appdata.cfg_schema import FileKeyMQTT_JWT

SALT_LEN = 16
DB_FILE = environ["DATA_PATH"] + "tmp_auth.sqlite"

db_connect = lambda: connect(DB_FILE)


class TokenName(StrEnum):
    REFRESH = "refresh"
    ACCESS = "access"


class JWT(TypedDict):
    name: TokenName
    token: str
    expiry: int


class LoginTokens(TypedDict):
    access_token: str
    expires_in: int
    token_type: str
    refresh_token: str
    refresh_token_expires_in: int


class NewToken(TypedDict):
    token_type: Literal["Bearer"]
    access_token: str
    expires_in: int


class TokenPair(TypedDict):
    refresh_token: JWT
    access_token: JWT


class UserAuth(TypedDict):
    username: str
    password: str
    clientid: str


class UserAcl(TypedDict):
    clientid: str
    acc: int
    topic: str
    username: str


def load_config():
    from tomllib import load

    from appdata.cfg_schema import FileData

    class Config(TypedDict):
        base_url: str
        credentials: FileKeyMQTT_JWT

    with open(environ["DATA_PATH"] + "default.toml", "rb") as f:
        cfg = cast(FileData, load(f))
        base_url = f'https://{cfg["api_addr"]}/'
        return Config(base_url=base_url, credentials=cfg["mqtt"]["jwt"])


def fire_forget_coro(coro: Coroutine, tasks: set[asyncio.Task] = set()):
    task = asyncio.create_task(coro)
    tasks.add(task)
    task.add_done_callback(tasks.discard)


def _hash_func(s: str, salt: bytes) -> bytes:
    return salt + sha(salt + s.encode()).digest()


def check_pwd(s: str, hash: bytes) -> bool:
    return _hash_func(s, hash[:SALT_LEN]) == hash


async def insert_user(user: UserAuth, _cache: set = set()):
    name = user["username"].lower()
    if name in _cache:
        return
    _cache.add(name)
    async with db_connect() as db:
        async with db.execute("SELECT 1 FROM User WHERE LOWER(username) = ?", (name,)) as cursor:
            if await cursor.fetchone() is None:
                await db.execute(
                    "INSERT INTO User (username, password) VALUES (?, ?)",
                    (name, _hash_func(user["password"], salt=urandom(SALT_LEN))),
                )
        await db.commit()


async def insert_acl(acl: UserAcl, _cache: set = set()):
    name = acl["username"].lower()
    topic = acl["topic"].lower()
    if (name, topic) in _cache:
        return
    _cache.add((name, topic))
    async with db_connect() as db:
        async with db.execute(
            "SELECT 1 FROM Acl WHERE LOWER(username) = ? AND LOWER(topic) = ?", (name, topic)
        ) as cursor:
            if await cursor.fetchone():
                return

        await db.execute("INSERT INTO Acl (username, topic, acc) VALUES (?, ?, ?)", (name, topic, acl["acc"]))
        await db.commit()


async def get_user_password(username: str) -> bytes | None:
    async with db_connect() as db:
        async with db.execute("SELECT password FROM User WHERE LOWER(username) = ?", (username.lower(),)) as cursor:
            if user := await cursor.fetchone():
                return user[0]
    return None


async def get_acl(acl: UserAcl) -> UserAcl | None:
    async with db_connect() as db:
        async with db.execute(
            "SELECT username, topic, acc FROM Acl WHERE LOWER(username) = ? AND LOWER(topic) = ?",
            (acl["username"].lower(), acl["topic"].lower()),
        ) as cursor:
            if dbacl := await cursor.fetchone():
                return UserAcl(username=dbacl[0], topic=dbacl[1], acc=dbacl[2], clientid="")
    return None


async def _db_upsert_refresh_jwt(token: JWT) -> None:
    async with db_connect() as db:
        await db.execute(
            """
            INSERT INTO JWT (name, token, expiry)
                VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                token = excluded.token,
                expiry = excluded.expiry
            """,
            ("refresh", token["token"], token["expiry"]),
        )
        await db.commit()


async def if_not_exist_create_db() -> None:
    if not path.exists(DB_FILE):
        async with db_connect() as db:
            await db.executescript(
                """
            CREATE TABLE User (
                username TEXT PRIMARY KEY,
                password BLOB NOT NULL
            );
            CREATE TABLE Acl (
                username TEXT,
                topic TEXT,
                acc INT NOT NULL,
                PRIMARY KEY (username, topic),
                FOREIGN KEY (username) REFERENCES User (username) ON DELETE CASCADE
            );
            CREATE TABLE JWT (
                name TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                expiry INT NOT NULL
            );"""
            )
            await db.commit()


class APIClient:
    __slots__ = ("http", "access_token", "refresh_token", "credentials")
    refresh_time_margin = int(timedelta(days=7).total_seconds())
    access_time_margin = int(timedelta(minutes=1).total_seconds())
    time_int = lambda: int(time.time())

    def __init__(self, base_url: str, credentials: FileKeyMQTT_JWT):
        self.http = AsyncClient(timeout=4, http2=True, base_url=base_url)
        self.http._cookies.jar.set_policy(DefaultCookiePolicy(allowed_domains=[]))
        self.access_token = JWT(name=TokenName.ACCESS, token="", expiry=-1)
        self.refresh_token = JWT(name=TokenName.REFRESH, token="", expiry=-1)
        self.credentials = credentials

    async def init(self) -> bool:
        async with db_connect() as db:
            async with db.execute("SELECT token, expiry FROM JWT WHERE name = 'refresh'") as cursor:
                if row := await cursor.fetchone():
                    self.refresh_token["token"] = row[0]
                    self.refresh_token["expiry"] = row[1]
                    if self.refresh_token["expiry"] > self.time_int():
                        return True
        return await self._login_and_set()

    async def post(self, path: str, jsobj: UserAuth | UserAcl, timeout=8) -> None | Response:
        async def _post():
            if not await self._check_tokens_or_fetch():
                return None
            result = await self.http.post(url=path, json=jsobj)
            if result.status_code < 300:
                return result
            raise RuntimeError("Invalid credentials to api")

        return await asyncio.wait_for(_post(), timeout=timeout)

    def _set_auth_header(self):
        self.http.headers = {b"Authorization": f"Bearer {self.access_token['token']}".encode()}

    async def _login_and_set(self) -> bool:
        try:
            resp = await self.http.post("auth/login", json=self.credentials)
            if resp.status_code < 300:
                time_now = self.time_int()
                tokens = LoginTokens(**json.loads(resp.content))
                self.refresh_token["token"] = tokens["refresh_token"]
                self.refresh_token["expiry"] = time_now + tokens["refresh_token_expires_in"] - self.refresh_time_margin
                self.access_token["token"] = tokens["access_token"]
                self.access_token["expiry"] = time_now + tokens["expires_in"] - self.access_time_margin
                fire_forget_coro(_db_upsert_refresh_jwt(self.refresh_token))
                self._set_auth_header()
                return True
        except:
            pass
        return False

    async def _check_tokens_or_fetch(self) -> bool:
        time_now = self.time_int()
        if self.access_token["expiry"] > time_now:
            return True

        if self.refresh_token["expiry"] <= time_now:
            return await self._login_and_set()

        resp = await self.http.get("auth/token", cookies={"refresh_token": self.refresh_token["token"]})
        if resp.status_code >= 300:  # Token might have been revoked.
            return await self._login_and_set()

        data = NewToken(**json.loads(resp.content))
        self.access_token["token"] = data["access_token"]
        self.access_token["expiry"] = time_now + data["expires_in"] - self.access_time_margin
        self._set_auth_header()
        return True
