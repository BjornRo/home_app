from collections import defaultdict
from typing import Mapping

import msgspec
from guards.guards import root_or_local_jwt_guard
from litestar import get
from litestar.controller import Controller

from appdata import shared  # type: ignore
from appdata.shared import SensorData, StatusData  # type: ignore

type Location = str
type DeviceName = str
type SensorID = str


class DataController(Controller):
    path = "/data"
    tags = ["data"]
    sensor_decoder = msgspec.msgpack.Decoder(SensorData).decode
    status_decoder = msgspec.msgpack.Decoder(StatusData).decode

    @get(path="/sensors", description="Root-prop: Location\n\nChild-prop: Device")
    async def get_sensors_data(
        self, data_cache: shared.ValkeyBasic
    ) -> Mapping[Location, dict[DeviceName, dict[SensorID, float]]]:
        all_data = defaultdict(lambda: defaultdict(dict))
        data = await data_cache.keys("sensor:*")
        result = await data_cache.get_many(*(x.decode() for x in await data_cache.keys("sensor:*")))
        for data in (self.sensor_decoder(data) for data in result if data):
            all_data[data.location][data.device_name][data.sensor_id] = data.to_dict()
        return all_data

    @get(
        path="/relays",
        # middleware=[JWTAuthenticationMiddleware],
        guards=[root_or_local_jwt_guard],
        description="Root-prop: Location\n\nChild-prop: Device",
    )
    async def get_status(self, data_cache: shared.ValkeyBasic) -> dict[str, dict[str, StatusData]]:
        all_data = defaultdict(dict)
        result = await data_cache.get_many(*(x.decode() for x in await data_cache.keys("relay:*")))
        for data in (self.status_decoder(data) for data in result if data):
            all_data[data.location][data.device_name] = data.data
        return all_data

    # @get(path="/sensors/logs", return_dto=MsgspecDTO[SensorData], raises=[ClientException])
    # async def get_sensors_logs(
    #     self,
    #     start: str = "",
    #     end: str = "",
    #     limit: int = 10,
    #     offset: int = 0,
    #     device: str = "",
    #     location: str = "",
    # ) -> list[SensorData]:
    #     if not (0 < limit <= 1_000_000_000_000 and 0 <= offset <= 1_000_000_000_000):
    #         raise ClientException("Limit or offset contain invalid values")
    #     for i in start, end, device, location:
    #         if len(i) >= 50:
    #             raise ClientException

    #     qry_args = None
    #     where = ""
    #     if device or location:
    #         if device and location:
    #             raise ClientException("Either device or location")
    #         if ":" in device or ":" in location:
    #             raise ClientException("Invalid device")
    #         qry_args = {}
    #         if device:
    #             qry_args["setting"] = device
    #             where = "WHERE device_name=$setting"
    #         elif location:
    #             qry_args["setting"] = location
    #             where = "WHERE location=$setting"

    #     try:
    #         if start:
    #             start = '{date:"%s"}' % datetime_to_isoformat(datetime.fromisoformat(start), "minutes")
    #         if end:
    #             end = '{date:"%s"}' % datetime_to_isoformat(datetime.fromisoformat(end), "minutes")
    #     except:
    #         raise ClientException("Invalid start and end date format")
    #     if start and end and (start >= end):
    #         raise ClientException("Start date is equal or larger to end date")

    #     ranges = ":" + start + ".." + end if (start or end) else ""
    #     qry = f"SELECT * FROM sensor{ranges} {where} LIMIT {limit} {f'START {offset}' if offset else ''}"
    #     return (await self.db.query(qry, qry_args)).data
