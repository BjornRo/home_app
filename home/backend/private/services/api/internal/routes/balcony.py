from typing import Annotated

import msgspec
from core.constants import SECURITY_TAG
from guards import guards
from internal.internal_services import mqtt_service
from litestar import post
from litestar.controller import Controller
from litestar.params import Body, Parameter


class TimePayload(msgspec.Struct):
    time: Annotated[int, msgspec.Meta(ge=0, le=500)]


class BalconyController(Controller):
    path = "/balcony"
    tags = ["internal_balcony"]
    guards = [guards.root_or_local_jwt_guard]
    security = [SECURITY_TAG.access_token]

    @post(path="/all")
    async def control_relay_all(
        self,
        internal_mqtt_service: mqtt_service.MQTTService,
        data: Annotated[TimePayload, Body(description="Value(minutes) between 0-500, 0 means off.")],
    ) -> None:
        await internal_mqtt_service.control_relay("balcony", "all", data.time)

    @post(path="/{relay_id:int}")
    async def control_relay(
        self,
        internal_mqtt_service: mqtt_service.MQTTService,
        data: Annotated[TimePayload, Body(description="Value(minutes) between 0-500, 0 means off.")],
        relay_id: Annotated[int, Parameter(ge=0, le=3, description="Value between 0-3")],
    ) -> None:
        await internal_mqtt_service.control_relay("balcony", relay_id, data.time)
