from __future__ import annotations

__import__("sys").path.append("/")

import asyncio
import os
from contextlib import suppress

import aiomqtt
import load_config
import msgspec
import utils
import uvloop  # type:ignore

from appdata import shared

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

CFG = load_config.load(os.environ["DATA_PATH"])
THIS_LOCATION: str = CFG["current_loc"]

cache = shared.ValkeyBasic(unix_socket_path="/mem/cache_data", max_connections=5)


async def main():
    push_to_global = utils.AsyncConnectionQueue[shared.MQTTPacket](is_connected=False)
    try:
        await asyncio.gather(
            external_mqtt(push_to_global),
            local_mqtt(push_to_global),
        )
    finally:
        await cache.aclose()


async def external_mqtt(push_to_global: utils.AsyncConnectionQueue[shared.MQTTPacket]):
    async def queue_handler(client: aiomqtt.Client):
        while True:
            await client.publish(**msgspec.to_builtins(await push_to_global.get()), qos=1)

    async def message_handler(client: aiomqtt.Client):
        async for msg in client.messages:
            loc, rest = msg.topic.value.split("/", maxsplit=1)
            msg.topic = aiomqtt.topic.Topic(rest)
            shared.fire_forget_coro(utils.msg_handler(msg, location=loc, cache=cache))

    while True:
        with suppress(BaseException):
            async with aiomqtt.Client(**CFG["external"], protocol=aiomqtt.ProtocolVersion.V31) as client:
                push_to_global.set(True)
                await client.publish("void", client.identifier)
                for location in CFG["other_loc"]:
                    await client.subscribe(location + "/#", qos=1)
                await asyncio.gather(
                    queue_handler(client),
                    message_handler(client),
                )
        push_to_global.set(False)
        await asyncio.sleep(30)


async def local_mqtt(push_to_global: utils.AsyncConnectionQueue[shared.MQTTPacket]):
    async def handle_local_mqtt_msg(message: aiomqtt.Message):
        if push_msg := await utils.msg_handler(message, location=THIS_LOCATION, cache=cache):
            await push_to_global.put(push_msg)

    while True:
        with suppress(BaseException):
            async with aiomqtt.Client(**CFG["internal"], protocol=aiomqtt.ProtocolVersion.V31) as client:
                await client.publish("void", client.identifier)
                for sub in CFG["subs"]:
                    await client.subscribe(sub, qos=1)

                async for message in client.messages:
                    shared.fire_forget_coro(handle_local_mqtt_msg(message))
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
