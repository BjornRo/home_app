from __future__ import annotations

import asyncio
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import timedelta
from typing import TypedDict
from uuid import uuid4

import db.distlock as dl
import db.queries as queries
import modules.myjwt as myjwt
import msgspec
import utils
from constants import DEFAULT_SECURITY_TAG as SECTAG
from constants import HOSTNAME
from db.models import UserLogin, UserRolesEnum
from jose import jwe, jws, jwt
from litestar import delete, get, post
from litestar.connection import Request
from litestar.controller import Controller
from litestar.exceptions import (
    ClientException,
    InternalServerException,
    NotFoundException,
    PermissionDeniedException,
)
from modules.guards import local_access_guard, mod_guard, root_guard

__secret0, __secret1 = utils.secrets[:2]
JWS_ALGO = "HS256"
EXPIRY_REGISTRATION_TOKEN = int(timedelta(minutes=10).total_seconds())
QUEUE_SIZE_OF_WAITING = 5


def gen_temp_token(unique_id: str, userdata: WaitingUserData) -> str:
    _time = int(time.time())
    payload = TempToken(
        sub=unique_id,
        exp=_time + EXPIRY_REGISTRATION_TOKEN + 5,
        iat=_time,
        data=userdata,
    )
    token_str = jwt.encode(msgspec.to_builtins(payload), key=__secret0, algorithm=JWS_ALGO).encode()
    token_str = jwe.encrypt(plaintext=token_str, key=__secret1, encryption="A256GCM")
    return urlsafe_b64encode(token_str).decode()


class UserRegistration(TypedDict):
    name: str
    pwd: str
    mail: str


class WaitingUserData(msgspec.Struct):
    mail: str
    name: str
    hash_b64_pwd: str


class TempToken(msgspec.Struct):
    sub: str
    exp: int
    iat: int
    data: WaitingUserData


async def _del_user(user_id: str):
    await asyncio.gather(queries.delete_user(user_id), myjwt.delete_all_cache(user_id))


class RegisterController(Controller):
    path = "/register"
    tags = ["register"]
    middleware = [myjwt.jwt_middleware]
    json_decode = msgspec.json.Decoder(TempToken).decode

    @post(
        "/",
        status_code=201,
        guards=[root_guard],
        raises=[ClientException, InternalServerException],
        security=SECTAG,
    )
    async def register_rootpath(self, data: UserLogin, request: Request) -> None:
        name = data.name
        pwd = data.pwd
        mail = data.mail
        utils.validate_name(name)
        utils.validate_password(pwd)
        # Critical section, race condition between name and mail, whatever
        if mail:
            utils.validate_mail(mail)
            ok, _ = await dl.mail_lock.set(mail, EXPIRY_REGISTRATION_TOKEN, None)
            if not ok:
                raise ClientException("Mail already exists")
            ok, _ = await dl.user_login_lock.set(name, EXPIRY_REGISTRATION_TOKEN, None)
            if not ok:
                await dl.mail_lock.delete(mail)
                raise ClientException("User already exists")
        else:
            ok, _ = await dl.user_login_lock.set(name, EXPIRY_REGISTRATION_TOKEN, None)
            if not ok:
                raise ClientException("User already exists")
        # End critical section
        try:
            if mail and await queries.exists_mail(mail):
                raise ClientException("Mail already exists")
            if await queries.exists_name(name):
                raise ClientException("User already exists")
            created_by = request.auth["sub"]
            await queries.insert_user(
                login=name,
                mail=mail,
                hash_b64_pwd=await utils.hash_password_b64(pwd),
                created_by_user_id=created_by,
            )
        finally:  # Unlock the names
            await dl.user_login_lock.delete(name)
            if mail:
                await dl.mail_lock.delete(mail)

    @post("/mail", exclude_from_auth=True, status_code=204, guards=[local_access_guard], raises=[ClientException])
    async def mail(self, data: UserRegistration) -> None:
        name = data["name"]
        mail = data["mail"]
        pwd = data["pwd"]
        utils.validate_mail(mail)
        utils.validate_name(name)
        utils.validate_password(pwd)

        try:
            if await dl.user_login_lock.size() >= QUEUE_SIZE_OF_WAITING:
                raise Exception
            ok, _ = await dl.mail_lock.set(mail, EXPIRY_REGISTRATION_TOKEN, None)
            if not ok:
                raise Exception
            ok, _ = await dl.user_login_lock.set(name, EXPIRY_REGISTRATION_TOKEN, None)
            if not ok:
                await dl.mail_lock.delete(mail)
                raise Exception
        except:
            raise ClientException("Please wait a few minutes before try to register again")

        credentials_exists = await asyncio.gather(
            queries.exists_name(name),
            queries.exists_mail(mail),
        )
        if any(credentials_exists):
            await asyncio.gather(dl.mail_lock.delete(mail), dl.user_login_lock.delete(name))
            raise ClientException("Username or mail already exists")

        """ Token.sub is UniqueID(No collisions for n minutes) | WaitingUserData -> [AnyCase(mail), Password b64] """
        userdata = WaitingUserData(mail=mail, name=name, hash_b64_pwd=await utils.hash_password_b64(pwd))
        unique_id = uuid4().hex
        send_mail = lambda: utils.Mail().send(
            mail,
            "Confirm your registration to " + HOSTNAME,
            f"https://{HOSTNAME}/register/confirm/" + gen_temp_token(unique_id, userdata),
        )
        await asyncio.to_thread(send_mail)

    @get(
        "/confirm/{tok64:str}",
        exclude_from_auth=True,
        status_code=201,
        guards=[local_access_guard],
        raises=[ClientException, InternalServerException],
    )
    async def confirm(self, tok64: str) -> None:
        try:
            raw_token = jwe.decrypt(urlsafe_b64decode(tok64), key=__secret1)
            if raw_token is None:
                raise BaseException

            userdata = self.json_decode(jws.verify(raw_token, __secret0, algorithms=JWS_ALGO)).data
        except:
            raise ClientException("Invalid token")

        try:
            await queries.insert_user(
                login=userdata.name,
                mail=userdata.mail,
                hash_b64_pwd=userdata.hash_b64_pwd,
                created_by_user_id="<self>",
            )
        finally:
            await dl.mail_lock.delete(userdata.mail)
            await dl.user_login_lock.delete(userdata.name)

    @delete(
        "/",
        status_code=204,
        security=SECTAG,
        raises=[InternalServerException, PermissionDeniedException],
    )
    async def unregister_self(self, request: myjwt.AuthRequest) -> None:
        user_id = request.auth["sub"]
        ok, _ = await dl.reg_delete.set(user_id, EXPIRY_REGISTRATION_TOKEN, None)
        if not ok:
            raise PermissionDeniedException

        try:
            if request.user.is_root or not request.user.is_user:  # Prevent root users from deleting
                raise PermissionDeniedException
            if not await queries.get_user_name(user_id):  # User does not exist??
                raise InternalServerException
            await _del_user(user_id)
        finally:
            await dl.reg_delete.delete(user_id)

    @delete(
        "/{user_id:str}",
        status_code=204,
        security=SECTAG,
        guards=[root_guard, mod_guard],
        raises=[PermissionDeniedException, NotFoundException],
    )
    async def unregister_other(self, request: myjwt.AuthRequest, user_id: str) -> None:
        if user_id == request.auth["sub"]:
            raise PermissionDeniedException  # Cannot delete self here

        usr = request.user
        appuser = await queries.get_app_user(user_id, () if usr.is_root else (UserRolesEnum.USER,), False)
        if not appuser:
            raise NotFoundException("User does not exist")

        if appuser.is_root:
            raise PermissionDeniedException

        if usr.is_mod and (appuser.is_mod or not appuser.is_user):
            raise PermissionDeniedException

        ok, _ = await dl.reg_delete.set(user_id, EXPIRY_REGISTRATION_TOKEN, None)
        if not ok:
            raise PermissionDeniedException("User is already being deleted")
        await _del_user(user_id)
        await dl.reg_delete.delete(user_id)
