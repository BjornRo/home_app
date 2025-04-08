import asyncio
from asyncio import Queue, Task, create_task
from datetime import UTC, datetime
from glob import glob
from ssl import SSLContext, create_default_context
from typing import Coroutine, Literal, NoReturn, TypedDict, cast

import aiomqtt as mqtt
import ujson as json
import utils
from aiofiles import open as async_open

TEMPERATURE_FILE = glob("/sys/bus/w1/devices/28*")[0] + "/w1_slave"


# Temp data and corresponding time when data was received.
class TmpData(TypedDict):
    date: datetime
    data: dict[str, float]


class MQTTPacket(TypedDict):
    topic: str
    payload: bytes
    retain: bool


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
    __slots__ = ("push_external_msgs", "external_mqtt_task", "tmp_data")

    def __init__(self, tmp_data: dict[str, TmpData]):
        self.tmp_data = tmp_data
        self.external_mqtt_task = None
        self.push_external_msgs = AsyncConnectionQueue(is_connected=False)

    async def run(self) -> NoReturn:
        self.external_mqtt_task = asyncio.create_task(self._external_mqtt(), name="external_mqtt_task")
        await self._local_mqtt()

    async def _external_mqtt(self):
        while True:
            try:
                async with mqtt.Client(**CFG["external"], protocol=mqtt.ProtocolVersion.V31) as c:
                    await c.publish("void", c.identifier)
                    self.push_external_msgs.toggle(True)
                    while True:
                        await c.publish(**await self.push_external_msgs.get(), qos=1)
            except:
                self.push_external_msgs.toggle(False)
                await asyncio.sleep(30)

    async def _local_mqtt(self):
        async def msg_handler(msg: mqtt.Message) -> None | MQTTPacket:
            try:
                full_topic = msg.topic.value.lower()
                device_name = full_topic.split("/", 1)[0]
                payload = cast(bytes, msg.payload)
                _data: dict[str, float] = json.loads(payload)
                data = {k.lower(): v for k, v in _data.items() if test_value(k, v)}
                if len(_data) == len(data):
                    self.tmp_data[device_name] = TmpData(date=datetime.now(UTC), data=data)
                    await self.push_external_msgs.put(
                        MQTTPacket(topic=f'{CFG["current_loc"]}/{full_topic}', payload=payload, retain=msg.retain)
                    )
            except:
                pass
            return None

        async def publish_temp_to_mqtt_task(client: mqtt.Client, publish_topic: str) -> None:
            while True:
                try:
                    await asyncio.sleep(5)
                    temperature = await read_temp()
                    if temperature is None:
                        continue
                    await client.publish(
                        qos=1, topic=publish_topic, payload='{"temperature":%.2f}' % temperature, retain=False
                    )
                except asyncio.CancelledError:
                    return
                except:
                    await asyncio.sleep(30)

        publish_topic: str = next(sub for sub in CFG["subs"] if CFG["internal"]["username"] in sub)
        while True:
            task = None
            try:
                async with mqtt.Client(**CFG["internal"], protocol=mqtt.ProtocolVersion.V31) as c:
                    for sub in CFG["subs"]:
                        await c.subscribe(sub, qos=1)
                    await c.publish("void", c.identifier)
                    task = asyncio.create_task(publish_temp_to_mqtt_task(c, publish_topic))
                    async for msg in c.messages:
                        utils.fire_forget_coro(msg_handler(msg))
            except:
                if task is not None:
                    task.cancel()
                await asyncio.sleep(30)


def test_value(key: str | Literal["temperature", "humidity", "airpressure"], value: float | int) -> bool:
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


def fire_forget_coro(coro: Coroutine, tasks: set[Task] = set()):
    task = create_task(coro)
    tasks.add(task)
    task.add_done_callback(tasks.discard)


def load_setup_cfg():
    __import__("sys").path.append("/")  # To import from appdata. "/" for linting
    from os import environ
    from tomllib import load

    import appdata.cfg_schema as schema

    with open(environ["DATA_PATH"] + "default.toml", "rb") as f:
        cfg = cast(schema.FileData, load(f))

    class MQTTExternal(schema.FileKeyAPI_MQTT_External):
        identifier: str
        tls_context: SSLContext

    class MQTTInternal(schema.FileKeyAPI_MQTT_Internal):
        identifier: str
        tls_context: SSLContext

    class Config(TypedDict):
        external: MQTTExternal
        internal: MQTTInternal
        subs: list[str]
        current_loc: str
        api_addr: str

    return Config(
        external=MQTTExternal(
            **cfg["mqtt"]["external"],
            identifier=cfg["mqtt"]["external"]["username"] + "_unit",
            tls_context=create_default_context(),
        ),
        internal=MQTTInternal(
            **cfg["mqtt"]["internal"],
            identifier=cfg["mqtt"]["internal"]["username"] + "_unit",
            tls_context=create_default_context(cafile="/certs/ca/root.crt"),
        ),
        subs=cfg["mqtt"]["internal_subs"],
        current_loc=cfg["current_loc"],
        api_addr=cfg["api_addr"],
    )


async def read_temp() -> float | None:
    try:
        async with async_open(TEMPERATURE_FILE, "r") as f:
            if "YES" in (await f.readline()):
                temp = float((await f.readline()).split("t=")[1].strip()) / 1000
                if utils.test_value("temperature", temp):
                    return temp
    except:
        pass
    return None


CFG = utils.load_setup_cfg()
