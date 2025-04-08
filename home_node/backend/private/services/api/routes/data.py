import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal

import db.distlock as dl
import msgspec
from constants import DB_URI
from db.strategy.surreal import SurrealSimple
from litestar import get
from litestar.controller import Controller
from litestar.dto import MsgspecDTO
from litestar.exceptions import ClientException
from modules.guards import root_or_local_jwt_guard
from utils import datetime_to_isoformat


class SensorData(msgspec.Struct):
    date: str  # isoformat
    location: str
    device_name: str
    data: dict[str, float]

    def to_dict(self):
        return dict(date=self.date, data=self.data)


class StatusData(msgspec.Struct):
    device_type: Literal["relay", "switch"] | str
    location: str
    device_name: str
    data: dict[str, bool]


class DataController(Controller):
    path = "/data"
    tags = ["data"]
    sensor_decoder = msgspec.msgpack.Decoder(SensorData).decode
    status_decoder = msgspec.msgpack.Decoder(StatusData).decode
    db = SurrealSimple(DB_URI, database="data")

    @get(path="/")
    async def index(self) -> dict:
        return dict(valid_paths=["status", "sensors", "/sensors/logs"])

    @get(path="/sensors/logs", return_dto=MsgspecDTO[SensorData], raises=[ClientException])
    async def get_sensors_logs(
        self,
        start: str = "",
        end: str = "",
        limit: int = 10,
        offset: int = 0,
        device: str = "",
        location: str = "",
    ) -> list[SensorData]:
        if not (0 < limit <= 1_000_000_000_000 and 0 <= offset <= 1_000_000_000_000):
            raise ClientException("Limit or offset contain invalid values")
        for i in start, end, device, location:
            if len(i) >= 50:
                raise ClientException

        qry_args = None
        where = ""
        if device or location:
            if device and location:
                raise ClientException("Either device or location")
            if ":" in device or ":" in location:
                raise ClientException("Invalid device")
            qry_args = {}
            if device:
                qry_args["setting"] = device
                where = "WHERE device_name=$setting"
            elif location:
                qry_args["setting"] = location
                where = "WHERE location=$setting"

        try:
            if start:
                start = '{date:"%s"}' % datetime_to_isoformat(datetime.fromisoformat(start), "minutes")
            if end:
                end = '{date:"%s"}' % datetime_to_isoformat(datetime.fromisoformat(end), "minutes")
        except:
            raise ClientException("Invalid start and end date format")
        if start and end and (start >= end):
            raise ClientException("Start date is equal or larger to end date")

        ranges = ":" + start + ".." + end if (start or end) else ""
        qry = f"SELECT * FROM sensor{ranges} {where} LIMIT {limit} {f'START {offset}' if offset else ''}"
        return (await self.db.query(qry, qry_args)).data

    @get(path="/sensors", description="Root-prop: Location\n\nChild-prop: Device")
    async def get_sensors_data(self) -> dict[str, dict[str, dict[str, Any]]]:
        all_data = defaultdict(dict)
        keys = await dl.misc_sensordata.keys(key="0..10")
        result = await asyncio.gather(*(dl.misc_sensordata.get(k) for k in keys))
        for data in (self.sensor_decoder(data) for _, data in result):
            all_data[data.location][data.device_name] = data.to_dict()
        return all_data

    @get(path="/status", guards=[root_or_local_jwt_guard], description="Root-prop: Location\n\nChild-prop: Device")
    async def get_status(self) -> dict[str, dict[str, StatusData]]:
        all_data = defaultdict(dict)
        keys = await dl.misc_statusdata.keys(key="0..10")
        for d in (self.status_decoder(x) for _, x in await asyncio.gather(*(dl.misc_statusdata.get(k) for k in keys))):
            all_data[d.location][d.device_name] = d
        return all_data
