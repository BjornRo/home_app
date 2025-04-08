from __future__ import annotations

import msgspec

__import__("sys").path.append("/")  # To import from appdata. "/" for linting
import asyncio
import os
import shutil
from asyncio import Queue, Task, create_task
from datetime import UTC, datetime
from ftplib import FTP, FTP_TLS, error_perm
from os import environ
from pathlib import Path
from ssl import SSLContext, create_default_context
from typing import Any, Coroutine, Literal, TypedDict, cast

import aiomqtt as mqtt
import orjson as json

from appdata.distrilock_client import ClientUnix as DistlockClient
from appdata.surreal import Surreal

# Filepath, lock for db concurrency.
DB_FILE = environ["DB_FILE"]
DATA_PATH = environ["DATA_PATH"]

dl_sensor = DistlockClient(*next((int(sid), f"/mem/{path}") for path, sid in [environ["DL_SENSOR"].split("_")]))
dl_status = DistlockClient(*next((int(sid), f"/mem/{path}") for path, sid in [environ["DL_STATUS"].split("_")]))


def timenow_utc(ts: Literal["minutes", "seconds", "milliseconds", "auto"], dt: datetime | None = None) -> str:
    return (dt if dt else datetime.now(UTC)).isoformat(timespec=ts).rsplit("+", 1)[0] + "Z"


def fire_forget_coro(coro: Coroutine, _tasks: set[Task] = set()):
    task: Task = create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


# region: Types
class MQTTPacket(TypedDict):
    topic: str
    payload: bytes
    retain: bool


class ErrorMsg(TypedDict):
    date: str
    location: str
    device_name: str
    log_level: Literal["debug", "info", "warning", "error", "critical"]
    detail: str


class SensorData(msgspec.Struct):
    date: str  # isoformat
    location: str
    device_name: str
    data: dict[str, float]


class StatusData(msgspec.Struct):
    device_type: Literal["relay", "switch"] | str
    location: str
    device_name: str
    data: dict[str, bool]


# endregion


def load_setup_cfg():
    from tomllib import load as toml_load

    import appdata.cfg_schema as schema

    with open(DATA_PATH + "default.toml", "rb") as f:
        cfg = cast(schema.FileData, toml_load(f))

    class MQTTExternal(schema.FileKeyAPI_MQTT_External):
        password: str
        identifier: str
        hostname: str
        tls_context: SSLContext

    class MQTTInternal(schema.FileKeyAPI_MQTT_Internal):
        password: str
        identifier: str
        tls_context: SSLContext

    class Config(TypedDict):
        ftp: schema.FileKeyFTP
        external: MQTTExternal
        internal: MQTTInternal
        subs: list[str]
        sshuser: str
        sshport: int
        other_loc: list[str]
        current_loc: str

    external = internal = None
    for usr in cfg["api"]["internal_users"]:
        if (_ext := cfg["mqtt"]["external"])["username"] == usr["name"]:
            external = MQTTExternal(
                **_ext,
                password=usr["password"],
                identifier=_ext["username"] + "_unit",
                tls_context=create_default_context(),
                hostname=cfg["hostname"],
            )
        elif (_int := cfg["mqtt"]["internal"])["username"] == usr["name"]:
            internal = MQTTInternal(
                **_int,
                password=usr["password"],
                identifier=_int["username"] + "_unit",
                tls_context=create_default_context(cafile="/certs/ca/root.crt"),
            )
        if external and internal:
            break
    else:
        raise Exception("Password not found in config file")

    return Config(
        ftp=cfg["ftp"],
        external=external,
        internal=internal,
        subs=cfg["mqtt"]["internal_subs"],
        sshuser=cfg["ssh"]["user"],
        sshport=cfg["ssh"]["port"],
        other_loc=cfg["other_loc"],
        current_loc=cfg["current_loc"],
    )


CFG = load_setup_cfg()


class AsyncConnectionQueue:  # To prevent "memory leak" from adding too many items to queue.
    __slots__ = ("is_connected", "queue")

    def __init__(self, is_connected: bool):
        self.is_connected = is_connected
        self.queue: Queue[MQTTPacket] = Queue()

    async def put(self, data: MQTTPacket):
        if self.is_connected:
            await self.queue.put(data)

    async def get(self):
        return await self.queue.get()

    def toggle(self, value: bool):
        self.is_connected = value
        if not value:  # Clear queue if not connected
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except:
                    pass


class MQTTHandler:
    __slots__ = ("dl_sensor", "dl_status", "db", "push_external_msgs", "external_mqtt_task")
    encoder = msgspec.msgpack.Encoder().encode

    def __init__(self, dl_sensor: DistlockClient, dl_status: DistlockClient, db: SurrealDB):
        self.dl_sensor = dl_sensor
        self.dl_status = dl_status
        self.db = db
        self.push_external_msgs = AsyncConnectionQueue(is_connected=False)

    @staticmethod
    def _test_value(key: str | Literal["temperature", "humidity", "airpressure"], value: float | int) -> bool:
        match key.lower():
            case "temperature":
                _min, _max = -50, 60
            case "humidity":
                _min, _max = 0, 100
            case "airpressure":
                _min, _max = 800, 1300
            case _:
                raise ValueError(f"Unknown key: {key}")
        return _min <= value <= _max

    async def run(self):
        self.external_mqtt_task = asyncio.create_task(self._external_mqtt(), name="external_mqtt_task")
        await self.dl_sensor.init()
        await self.dl_status.init()
        await self._local_mqtt()

    async def _msg_handler(self, msg: mqtt.Message, location: str) -> None | MQTTPacket:
        try:
            location, topic = location.strip().lower(), msg.topic.value.strip().lower()
            payload = cast(bytes, msg.payload)
            match topic.split("/"):
                case "error", *_:
                    err_msg = ErrorMsg(**json.loads(payload), location=location, date=timenow_utc("seconds"))
                    await self.db.insert_error(err_msg)
                case device_name, device_type, device_payload_type:  # device_type: relay, sensor, switch
                    match device_payload_type:
                        case "status":
                            statusdata = StatusData(
                                device_type=device_type,
                                location=location,
                                device_name=device_name,
                                data=json.loads(payload),
                            )  # payload: json_ser(dict[str, bool])
                            await self.dl_status.set(device_name, None, self.encoder(statusdata))
                        case "data":
                            _data: dict[str, float] = json.loads(payload)
                            data = {k.lower(): v for k, v in _data.items() if self._test_value(k, v)}
                            if len(_data) == len(data):  # checks that all values are valid. Invalid values are filtered
                                sensordata = SensorData(
                                    date=timenow_utc("seconds"),
                                    location=location,
                                    device_name=device_name,
                                    data=data,
                                )
                                await self.dl_sensor.set(device_name, None, self.encoder(sensordata))
                                return MQTTPacket(topic=f"{location}/{topic}", payload=payload, retain=msg.retain)
        except:
            pass
        return None

    async def _external_mqtt(self):
        async def queue_handler(client: mqtt.Client):
            queued_msg = None
            while True:
                try:
                    if queued_msg is None:
                        queued_msg = await self.push_external_msgs.get()
                    await client.publish(**queued_msg, qos=1)
                    queued_msg = None
                except asyncio.CancelledError:
                    return
                except:
                    await asyncio.sleep(10)

        while True:
            queue_handler_task = None
            try:
                async with mqtt.Client(**CFG["external"], protocol=mqtt.ProtocolVersion.V31) as c:
                    queue_handler_task = asyncio.create_task(queue_handler(c))
                    await c.publish("void", c.identifier)
                    self.push_external_msgs.toggle(True)
                    for i in CFG["other_loc"]:
                        await c.subscribe(i + "/#", qos=1)
                    async for msg in c.messages:
                        try:
                            loc, rest = msg.topic.value.split("/", maxsplit=1)
                            msg.topic = mqtt.topic.Topic(rest)
                            fire_forget_coro(self._msg_handler(msg, location=loc))
                        except:
                            pass
            except:
                pass
            if queue_handler_task:
                queue_handler_task.cancel()
            self.push_external_msgs.toggle(False)
            await asyncio.sleep(30)

    async def _local_mqtt(self):
        async def handle_local_mqtt_msg(msg: mqtt.Message, current_loc: str = CFG["current_loc"]):
            if push_msg := await self._msg_handler(msg, location=current_loc):
                await self.push_external_msgs.put(push_msg)

        while True:
            try:
                async with mqtt.Client(**CFG["internal"], protocol=mqtt.ProtocolVersion.V31) as client:
                    for sub in CFG["subs"]:
                        await client.subscribe(sub, qos=1)
                    await client.publish("void", client.identifier)
                    async for _msg in client.messages:
                        fire_forget_coro(handle_local_mqtt_msg(_msg))
            except:
                raise
            await asyncio.sleep(30)


class SurrealDB:
    __slots__ = ("_db", "ns", "db", "uri")

    def __init__(self, uri: str, namespace="app", database="data", loop: asyncio.AbstractEventLoop | None = None):
        self._db = Surreal()
        self.uri = uri
        self.ns = namespace
        self.db = database
        if loop:
            loop.run_until_complete(self._check_insert_schema("schema.srql"))

    async def _check_insert_schema(self, schema: str):
        if (await self.query("SELECT VALUE 1 FROM ONLY sensor LIMIT 1")).data is None:
            with open(schema, "rt") as f:  # Definitions, schema, etc.
                await self.query(f.read())

    async def query(self, query: str, query_args: dict[str, Any] | None = None):
        while True:
            try:
                async with await self._db.connect(self.uri) as db:
                    await db.use(namespace=self.ns, database=self.db)
                    return await db.query(query, query_args)
            except:
                pass
            await asyncio.sleep(30)

    async def insert_data(self, data: list[SensorData]):
        for i in data:
            await self.query(
                "CREATE sensor:{device:$device,date:$date} CONTENT $data",
                {"device": i.device_name, "date": i.date, "data": msgspec.to_builtins(i)},
            )

    async def insert_error(self, data: ErrorMsg):
        await self.query("CREATE error CONTENT $data", {"data": data})


class SingleFileBackupFTP_TLS(FTP_TLS):
    __slots__ = ("user", "passwd", "workfolder", "target_file", "backup_size")

    def __init__(
        self, host: str, port: int, user: str, passwd: str, workdir: str, filepath: str, ftp_folder: str, size=10
    ):
        super().__init__()  # Has to be first, otherwise it connects due to self.host
        self.port, self.host, self.user, self.passwd = port, host, user, passwd
        self.workfolder = Path(workdir.strip("/").lower()) / Path(ftp_folder.strip("/").lower())
        self.target_file = Path(filepath.rstrip("/"))
        self.backup_size = size  # Generates new backups and deletes older that exceeds this number.

    def __enter__(self):
        self.connect()
        self.login(user=self.user, passwd=self.passwd, secure=True)
        self.prot_p()  # Get the "lowest" drive and create full path. Change to it
        self.cwd(sorted(self.nlst())[0])
        for path in ("backup" / self.workfolder).as_posix().split("/"):
            try:
                self.mkd(path)  # Throws error if path exists
            except error_perm:
                pass
            self.cwd(path)
        self.cwd("..")  # go back one step
        return self

    def upload_file(self) -> bool:
        backup_list = self.lsdir(self.workfolder.name, sorted_oldest_first=True)
        if len(backup_list) >= self.backup_size:
            self.delete(
                f"{self.workfolder.name}/{backup_list[-1]}"
            )  # NOTE: THis might be the bug, -1 sorted_oldest_first...?
        try:  # If file does not exist on FTP. Will exist after first run.
            new_name = f"{self.workfolder.name}/{timenow_utc('minutes')}_{self.target_file.name}"
            self.rename(fromname=self.target_file.name, toname=new_name)
        except error_perm:
            pass
        with open(self.target_file, "rb") as f:
            try:
                self.storbinary(f"STOR {self.target_file.name}", f)
                return True
            except error_perm:
                pass
        return False

    def get_file(self, overwite=True) -> bool:
        if self.target_file.name in self.lsdir():
            if overwite and os.path.exists(self.target_file):
                shutil.rmtree(self.target_file.parent, ignore_errors=True)
            os.makedirs(self.target_file.parent, exist_ok=True)
            with open(self.target_file, "wb") as f:
                try:
                    self.retrbinary(f"RETR {self.target_file.name}", f.write)
                    return True
                except:
                    pass
        return False

    def lsdir(self, dir: str = "", sorted_oldest_first=False) -> list[str]:
        xs = []
        self.dir("-t" * sorted_oldest_first, dir, lambda x: xs.append(x[x.rindex(" ") + 1 :]))
        return xs

    def ntransfercmd(self, cmd, rest=None):  # Transfers need the same session as the control connection.
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        return self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session), size  # type:ignore
