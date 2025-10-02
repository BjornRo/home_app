from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Literal, cast

import aiomqtt as mqtt
import msgspec

from appdata import shared

encoder = msgspec.msgpack.Encoder().encode
decoder = msgspec.json.Decoder().decode


class AsyncConnectionQueue[T](asyncio.Queue[T]):  # To prevent "memory leak" from adding too many items to queue.
    __slots__ = ("is_connected",)

    def __init__(self, is_connected: bool):
        self.is_connected = is_connected
        super().__init__()

    async def put(self, data: T):
        if self.is_connected:
            await super().put(data)

    def set(self, value: bool):
        self.is_connected = value
        if not value:  # Clear queue if not connected
            with suppress(asyncio.QueueEmpty):
                while not self.get_nowait():
                    pass


async def msg_handler(msg: mqtt.Message, location: str, cache: shared.ValkeyBasic) -> None | shared.MQTTPacket:
    try:
        location = location.strip().lower()
        topic = msg.topic.value.strip().lower()
        payload = cast(bytes, msg.payload)
        paths = topic.split("/")
        if paths[0] == "error":
            # err_msg = ErrorMsg(**json.loads(payload), location=location, date=timenow_utc("seconds"))
            # await self.db.insert_error(err_msg)
            return None

        device_name, device_type, payload_tag = paths  # device_type: relay, sensor, switch
        match device_type:
            case "relay":
                statusdata = shared.StatusData(
                    device_type=device_type,
                    location=location,
                    device_name=device_name,
                    data=decoder(payload),  # payload: json_ser(dict[str, bool])
                )
                await cache.set(f"{device_type}:{device_name}", encoder(statusdata))
            case "sensor":
                __data: dict[str, float] = decoder(payload)
                data = {k.lower(): v for k, v in __data.items() if test_value(k, v)}
                if len(__data) == len(data):
                    sensordata = shared.SensorData(
                        date=shared.datetime_now_isofmtZ("seconds"),
                        location=location,
                        device_name=device_name,
                        sensor_id=int(payload_tag),  # 0..n sensor
                        data=data,
                    )
                    await cache.set(f"{device_type}:{device_name}:{payload_tag}", encoder(sensordata))
                    return shared.MQTTPacket(topic=f"{location}/{topic}", payload=payload, retain=msg.retain)
    except Exception as e:
        shared.print_err(e)


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


# class ErrorMsg(TypedDict):
#     date: str
#     location: str
#     device_name: str
#     log_level: Literal["debug", "info", "warning", "error", "critical"]
#     detail: str
