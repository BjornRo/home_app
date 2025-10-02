import asyncio
from typing import Literal

import aiomqtt
import msgspec

from appdata import cfg_schema, shared  # type: ignore


class MQTTService(msgspec.Struct):
    mqtt_queue: asyncio.Queue[shared.MQTTPacket]
    device_settings: cfg_schema.FileKeyMQTT_Publish

    async def control_relay(self, device: Literal["balcony"], relay_id: int | Literal["all"], time: int):
        """
        Raises:
            ValueError
        """
        if time < 0:
            return ValueError("time is less than 0")

        device_cfg = self.device_settings[device]
        if isinstance(relay_id, int):
            if not (0 <= relay_id < device_cfg["relays"]):
                raise ValueError(f"relays should be 0 to {device_cfg["relays"]-1}")
        elif relay_id != "all":
            raise ValueError("invalid string given to relay_id, only 'all' is allowed")

        await self.mqtt_queue.put(
            shared.MQTTPacket(
                topic=f"{device}/{device_cfg["path"]}/{relay_id}",
                payload=str(min(time, 500)).encode(),
            )
        )
