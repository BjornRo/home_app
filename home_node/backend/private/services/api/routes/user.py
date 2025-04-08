import asyncio
from asyncio import TaskGroup
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Coroutine, NotRequired, TypedDict

import db.distlock as dl
import db.queries as queries
import msgspec
from constants import DEFAULT_SECURITY_TAG as SECTAG
from db.models import (
    AllUserView,
    ApiAppUser,
    AppUserACL,
    TableAPI,
    User,
    UserData,
    UserRolesEnum,
)
from litestar import delete, get, patch, post
from litestar.controller import Controller
from litestar.dto import DTOConfig, MsgspecDTO
from litestar.exceptions import (
    ClientException,
    InternalServerException,
    NotFoundException,
    PermissionDeniedException,
    TooManyRequestsException,
)
from litestar.params import Body, Parameter
from modules.guards import root_guard, root_or_local_guard
from modules.myjwt import AuthRequest, jwt_middleware
from mytypes import DateTimeUTC, ItemAlreadyExistException
from typing_extensions import Annotated
from utils import (
    datetime_to_isoformat,
    generate_created_end_date,
    validate_mail,
    validate_name,
    validate_password,
)


def json_encode(x: dict, _enc=msgspec.json.Encoder().encode):
    return _enc(x).decode()


class ReturnUserDTO(MsgspecDTO[User]):
    config = DTOConfig(
        exclude={
            "login.pwd",
            "acl",
        }
    )


class ReturnAllUserViewDTO(MsgspecDTO[AllUserView]):
    config = DTOConfig(
        exclude={
            "login.pwd",
        }
    )


class UserSettingsUpdate(TypedDict, total=False):
    mail: str
    name: str
    data_name: str
    password: str


class ACLPayload(TypedDict):
    start_date: NotRequired[str]
    end_date: NotRequired[str]
    rwx: Annotated[int, Parameter(ge=0, le=7, description="Value as Linux RWX value 0-7")]


class UserController(Controller):
    path = "/user"
    tags = ["user"]
    security = SECTAG
    guards = [root_or_local_guard]
    middleware = [jwt_middleware]
    # exclude_from_auth=True

    @get(path="/", guards=[root_guard], return_dto=ReturnAllUserViewDTO)
    async def all_users(self, limit: int = 10, offset: int = 0, asc: bool = True) -> list[AllUserView]:
        return await queries.get_all_users(limit=limit, offset=offset, asc=asc)

    @get(path="/count", guards=[root_guard])
    async def user_count(self) -> int:
        return await queries.number_of_users()

    @get(
        path="/search/{name_or_email:str}",
        guards=[root_guard],
        return_dto=ReturnAllUserViewDTO,
        raises=[ClientException],
    )
    async def search(
        self,
        name_or_email: str,
        limit: Annotated[int, Parameter(ge=0, description="0 means no limit")] = 10,
        exact_match: Annotated[bool, Parameter(description="If false, then it checks a subset")] = False,
    ) -> list[AllUserView]:
        return await queries.search_user(name_or_email, limit, exact_match)

    @get(path="/{user_id:str}", return_dto=ReturnUserDTO, raises=[NotFoundException])
    async def data(self, user_id: str, request: AuthRequest) -> User:
        if user_id.lower() == "self" or (not (user_id == request.auth["sub"] or request.user.is_root)):
            user_id = request.auth["sub"]

        if result := await queries.get_user(user_id):
            return result
        raise NotFoundException

    @get(path="/{user_id:str}/data", raises=[NotFoundException])
    async def user_data(self, user_id: str, request: AuthRequest) -> UserData:
        if user_id.lower() == "self" or (not (user_id == request.auth["sub"] or request.user.is_root)):
            user_id = request.auth["sub"]

        if result := await queries.get_user_data(user_id):
            return result
        raise NotFoundException

    @patch(
        path="/{user_id:str}",
        status_code=204,
        guards=[root_or_local_guard],
        raises=[
            ClientException,
            PermissionDeniedException,
            InternalServerException,
            NotFoundException,
            TooManyRequestsException,
        ],
    )
    async def update_user(
        self,
        request: AuthRequest,
        user_id: str,
        settings: Annotated[
            UserSettingsUpdate,
            Body(title="Update user settings", description="Supply at least one or more settings to update"),
        ],
    ) -> None:
        if not settings:
            raise ClientException
        USER_IS_ROOT = request.user.is_root
        target_user = request.user
        if user_id.lower() == "self":
            user_id = request.auth["sub"]
        elif user_id != request.auth["sub"]:
            if not USER_IS_ROOT:
                raise PermissionDeniedException
            if appuser := await queries.get_app_user(user_id):
                target_user = appuser
            else:
                raise NotFoundException

        if not USER_IS_ROOT:  # If the requester is not root, then cooldown for modifying
            last_update = await queries.get_user_modified(user_id)
            if not last_update:
                raise InternalServerException  # Should not happen

            if datetime.now(UTC) - last_update <= timedelta(seconds=60):
                raise TooManyRequestsException

        # Update only after payload is validated -> Not well-formed -> no update
        tasks_holder: list[tuple[str, Coroutine]] = []  # Add validated tasks, then execute them.
        success = []
        fail = []

        if mail := settings.get("mail"):

            async def can_update_mail(mail: str) -> bool:
                if validate_mail(mail):
                    acquired_lock, _ = await dl.mail_lock.set(mail, 60, None)
                    if acquired_lock:
                        if not await queries.exists_mail(mail):
                            return True  # We have the lock, no one else can change to this mail
                        await dl.mail_lock.delete(mail)  # unlock, mail already exists
                return False

            if mail == "null":
                if request.user.is_root:
                    tasks_holder.append(("mail", queries.delete_mail(user_id)))
                else:
                    fail.append("mail")
            elif await can_update_mail(mail):
                # TODO add that user needs to verify their new mail
                tasks_holder.append(("mail", queries.update_mail(user_id, mail)))
            else:
                fail.append("mail")

        if password := settings.get("password"):
            if validate_password(password):
                tasks_holder.append(("password", queries.update_pwd(user_id, password)))
            else:
                fail.append("password")

        if data_name := settings.get("data_name"):
            if validate_name(data_name):
                tasks_holder.append(("data_name", queries.update_data_name(user_id, data_name)))
            else:
                fail.append("data_name")

        if name := settings.get("name"):  # Only root

            async def can_update_login(name: str):
                if validate_name(name):
                    acquired_lock, _ = await dl.user_login_lock.set(name, 60, None)
                    if acquired_lock:
                        if not await queries.exists_name(name):
                            return True
                        await dl.user_login_lock.delete(name)
                return False

            if not target_user.is_root:
                fail.append("name")
            elif await can_update_login(name):
                tasks_holder.append(("name", queries.update_name(user_id, name)))
            else:
                fail.append("name")

        if tasks_holder:
            keys: list[str]
            tasks: list[Coroutine]
            keys, tasks = zip(*tasks_holder)
            for key, task in zip(keys, await asyncio.gather(*tasks, return_exceptions=True)):
                if isinstance(task, BaseException):
                    fail.append(key)
                else:
                    success.append(key)
                match key:
                    case "name":
                        await dl.user_login_lock.delete(settings[key])  # type: ignore
                    case "mail":
                        await dl.mail_lock.delete(settings[key])  # type: ignore

        # Update
        if fail or not success or not tasks_holder:
            raise InternalServerException(json_encode({"fail": fail, "success": success}))
        await queries.update_user_modified(user_id)

    @get(path="/{user_id:str}/app", guards=[root_or_local_guard], raises=[NotFoundException])
    async def app_user(self, user_id: str, request: AuthRequest) -> ApiAppUser:
        if not (user_id.lower() == "self" or user_id == request.auth["sub"]) and request.user.is_root:
            if _appuser := await queries.get_app_user(user_id):
                return _appuser.to_dict()
            raise NotFoundException
        return request.user.to_dict()

    @get(
        path="/{user_id:str}/modified",
        raises=[NotFoundException, InternalServerException],
    )
    async def user_modified(self, user_id: str, request: AuthRequest) -> DateTimeUTC:
        if user_id.lower() != "self" and user_id != request.auth["sub"] and request.user.is_root:
            if (res := await queries.get_user_modified(user_id)) is not None:
                return res
            raise NotFoundException

        if (res := await queries.get_user_modified(request.auth["sub"])) is not None:
            return res
        raise InternalServerException

    @get(path="/{user_id:str}/all_data", guards=[root_or_local_guard], raises=[NotFoundException])
    async def all_data(self, user_id: str, request: AuthRequest) -> dict:
        if user_id.lower() == "self":
            user_id = request.auth["sub"]
        elif user_id != request.auth["sub"]:
            if request.user.is_root:
                if not await queries.exists_user_id(user_id):
                    raise NotFoundException
            else:
                user_id = request.auth["sub"]

        tasks: dict[str, Coroutine[Any, Any, Any | None]] = {"user": queries.get_user(user_id)}
        # Gather/TG to speed up the process. Then unpack if result is not None.
        async with TaskGroup() as tg:
            tg_tasks = [tg.create_task(x) for x in tasks.values()]

        tasks_result = zip(tasks.keys(), map(lambda x: x.result(), tg_tasks))
        data = {k: msgspec.to_builtins(v) for k, v in tasks_result}
        for d, k in (data["user"], "acl"), (data["user"]["login"], "pwd"):
            try:
                del d[k]
            except:
                pass
        return data

    @patch(
        path="/{user_id:str}/role/{role:str}",
        status_code=204,
        guards=[root_guard],
        raises=[PermissionDeniedException, ClientException, ItemAlreadyExistException],
    )
    async def add_replace_role(self, user_id: str, role: str, request: AuthRequest, replace_role: str = "") -> None:
        if not replace_role:
            raise ClientException("Disabled for time being.")
        try:
            role_to_add = UserRolesEnum(role.lower())
        except:
            raise ClientException(f"Role ({role}) does not exist")
        if UserRolesEnum.ROOT == role_to_add:
            raise PermissionDeniedException

        appuser = await queries.get_app_user(user_id)
        if not appuser:
            raise NotFoundException

        if appuser.has_role(role_to_add):
            login_name = await queries.get_user_name(user_id)
            raise ItemAlreadyExistException(f"User ({login_name}) already has role ({role_to_add})")
        given_by = request.auth["sub"]
        if not replace_role:
            await queries.insert_userrole(user_id, role_to_add, None, given_by)
            return
        try:
            role_to_remove = UserRolesEnum(replace_role.lower())
        except:
            raise ClientException("Role to be removed is invalid")
        if not appuser.has_role(role_to_remove):
            login_name = await queries.get_user_name(user_id)
            raise ClientException(f"User ({login_name}) does not have role to be removed ({role_to_remove})")
        await queries.replace_userrole(user_id, role_to_add, role_to_remove, None, given_by)

    @delete(
        path="/{user_id:str}/role/{role:str}",
        status_code=204,
        guards=[root_guard],
        raises=[PermissionDeniedException, ClientException, NotFoundException],
    )
    async def del_role(self, user_id: str, role: str) -> None:
        try:
            role_to_delete = UserRolesEnum(role.lower())
        except:
            raise ClientException(f"Role ({role}) does not exist")
        if UserRolesEnum.ROOT == role_to_delete:
            raise PermissionDeniedException

        appuser = await queries.get_app_user(user_id)
        if not appuser:
            raise NotFoundException

        if len(appuser.roles) == 1:
            raise ClientException(f"A user has to have at least one role, add one and then delete old.")

        if role_to_delete not in appuser.roles:
            login_name = await queries.get_user_name(user_id)
            raise ClientException(f"User ({login_name}) does not have ({role_to_delete.value})")
        await queries.delete_userrole(user_id, role_to_delete)

    @get(
        path="/{user_id:str}/acl",
        status_code=200,
        guards=[root_guard],
        raises=[NotFoundException],
    )
    async def get_acl(self, user_id: str, request: AuthRequest) -> list[AppUserACL]:
        resp = await queries.query(f"SELECT meta::id(out) AS resource, rwx FROM {TableAPI.USER}:{user_id}->has_service")
        return resp.data

    @staticmethod
    def pre_validate_acl(data: ACLPayload):
        rwx = data["rwx"]
        if not (0 <= rwx <= 7):
            raise ClientException("Invalid rwx value")

        def validate_datestr(date_str: str):
            if date_str[-1] == "Z":
                try:
                    return datetime.fromisoformat(date_str)
                except:
                    pass
            return None

        curr_time = datetime.now(UTC)
        start_date = None
        if date_str := data.get("start_date"):
            start_date = validate_datestr(date_str)
            if not start_date:
                raise ClientException("Invalid start date")

        end_date = None
        if date_str := data.get("end_date"):
            end_date = validate_datestr(date_str)
            if not end_date:
                raise ClientException("Invalid end date")
            if end_date <= curr_time:
                raise ClientException("End date is already expired")
        if start_date and end_date and start_date >= end_date:
            raise ClientException("Start date is larger or equal to end date")

        return curr_time, start_date, end_date, rwx

    @post(
        path="/{user_id:str}/acl/{service_name:str}",
        status_code=201,
        guards=[root_guard],
        raises=[NotFoundException, ClientException],
    )
    async def insert_acl(
        self,
        user_id: str,
        service_name: str,
        data: ACLPayload,
        request: AuthRequest,
    ) -> None:
        curr_time, start_date, end_date, rwx = self.pre_validate_acl(data)

        created_str, end_str = generate_created_end_date(end_date, curr_time)
        if not start_date or start_date <= curr_time:
            start_str = created_str
        else:
            start_str = datetime_to_isoformat(start_date)

        q = (
            "BEGIN TRANSACTION;"
            "IF (SELECT VALUE TRUE FROM ONLY $uid)!=TRUE {RETURN 1}"
            " ELSE IF (SELECT VALUE TRUE FROM ONLY $sid)!=TRUE {RETURN 2}"
            " ELSE IF (SELECT VALUE TRUE FROM ONLY has_service WHERE in=$uid AND out=$sid LIMIT 1)=TRUE {RETURN 3}"
            " ELSE {RELATE $uid->has_service->$sid CONTENT $content; RETURN 0};"
            "COMMIT TRANSACTION;"
        )
        qry = {
            "uid": f"{TableAPI.USER}:{user_id}",
            "sid": f"service:{service_name.lower()}",
            "content": {
                "rwx": rwx,
                "given_by": f"{TableAPI.USER}:{request.auth['sub']}",
                "start": start_str,
                "end": end_str,
                "created": created_str,
            },
        }
        resp = await queries.query(q, qry)
        if not resp.ok:
            raise ClientException
        match resp.data:
            case 0:
                return None
            case 1:
                raise NotFoundException
            case 2:
                raise ClientException("Service name does not exist")
            case 3:
                raise ClientException("User does already have service")
            case _:
                raise ClientException("Unknown error")

    @patch(
        path="/{user_id:str}/acl/{service_name:str}",
        status_code=201,
        guards=[root_guard],
        raises=[NotFoundException, ClientException],
    )
    async def update_acl(
        self,
        user_id: str,
        service_name: str,
        data: ACLPayload,
        request: AuthRequest,
    ) -> None:
        curr_time, start_date, end_date, rwx = self.pre_validate_acl(data)
        curr_time_str, end_str = generate_created_end_date(end_date, curr_time)

        content: dict = {"rwx": rwx}

        if start_date:
            content["start"] = curr_time_str if start_date <= curr_time else datetime_to_isoformat(start_date)
        if end_date:
            content["end"] = end_str
        q = (
            "BEGIN TRANSACTION;"
            "IF (SELECT VALUE TRUE FROM ONLY $uid)!=TRUE {RETURN 1}"
            " ELSE IF (SELECT VALUE TRUE FROM ONLY $sid)!=TRUE {RETURN 2}"
            " ELSE {"
            "  LET $has_service=SELECT start,id,rwx FROM ONLY has_service WHERE in=$uid AND out=$sid LIMIT 1;"
            "  RETURN IF $has_service=NONE {RETURN 3}"
            "   ELSE IF $content.rwx=$has_service.rwx {RETURN 4}"
            "   ELSE {UPDATE ONLY $has_service.id CONTENT $content; RETURN 0}"
            " };"
            "COMMIT TRANSACTION;"
        )

        qry = {
            "uid": f"{TableAPI.USER}:{user_id}",
            "sid": f"service:{service_name.lower()}",
            "content": content,
        }

        resp = await queries.query(q, qry)
        if not resp.ok:
            raise ClientException
        match resp.data:
            case 0:
                return None
            case 1:
                raise NotFoundException
            case 2:
                raise ClientException("Service name does not exist")
            case 3:
                raise ClientException("User does not have service")
            case 4:
                raise ClientException("RWX number is the same")
            case _:
                raise ClientException("Unknown error")

    @delete(
        path="/{user_id:str}/acl/{service_name:str}",
        status_code=201,
        guards=[root_guard],
        raises=[NotFoundException, ClientException],
    )
    async def delete_acl(
        self,
        user_id: str,
        service_name: str,
    ) -> None:
        q = (
            "BEGIN TRANSACTION;"
            "IF (SELECT VALUE TRUE FROM ONLY $uid)!=TRUE {RETURN 1}"
            " ELSE IF (SELECT VALUE TRUE FROM ONLY $sid)!=TRUE {RETURN 2}"
            " ELSE {"
            "  LET $has_service=SELECT VALUE id FROM ONLY has_service WHERE in=$uid AND out=$sid LIMIT 1;"
            "  RETURN IF $has_service=NONE {RETURN 3}"
            "   ELSE {DELETE ONLY $has_service; RETURN 0}"
            " };"
            "COMMIT TRANSACTION;"
        )
        qry = {
            "uid": f"{TableAPI.USER}:{user_id}",
            "sid": f"service:{service_name.lower()}",
        }

        resp = await queries.query(q, qry)
        if not resp.ok:
            raise ClientException
        match resp.data:
            case 0:
                return None
            case 1:
                raise NotFoundException
            case 2:
                raise ClientException("Service name does not exist")
            case 3:
                raise ClientException("User does not have service")
            case _:
                raise ClientException("Unknown error")
