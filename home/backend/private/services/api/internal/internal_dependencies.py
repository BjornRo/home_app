import asyncio

import aiomqtt
import internal.constants
import msgspec
from core import paths, settings
from dependencies import _cache_app, _cache_token
from internal.internal_services.mqtt_service import MQTTService
from internal.internal_services.token_service import InternalTokenService
from internal.internal_services.user_service import InternalUserService
from internal.storage.repositories.internal_meta_repository import (
    InternalMetaRepository,
)
from internal.storage.repositories.internal_user_repository import (
    InternalUserRepository,
)
from litestar import Litestar
from storage.db.sql.sqlite import SQLite

from appdata import shared

__db_internal_client = SQLite(dbfile=paths.DATA_PATH + internal.constants.DB_INTERNAL, pool_size=5)
__mqtt_client = aiomqtt.Client(**settings.MQTT_SETTINGS, protocol=aiomqtt.ProtocolVersion.V31)

# Repositories
__repo_user = InternalUserRepository(db=__db_internal_client)
__repo_meta = InternalMetaRepository(db=__db_internal_client)

__queue_push_to_local_mqtt = asyncio.Queue[shared.MQTTPacket]()


async def push_to_local_mqtt_task():
    while True:
        msg = await __queue_push_to_local_mqtt.get()
        await __mqtt_client.publish(**msgspec.to_builtins(msg), qos=1)


async def start(app: Litestar):
    await __mqtt_client.__aenter__()
    await __mqtt_client.publish("void", f"api({__mqtt_client.identifier})")
    shared.fire_forget_coro(push_to_local_mqtt_task())


async def close():
    await asyncio.gather(
        __mqtt_client.__aexit__(None, None, None),
        __db_internal_client.close(),
    )


async def provide_internal_token_service() -> InternalTokenService:
    return InternalTokenService(
        user_service=await provide_internal_user_service(),
        repo_meta=__repo_meta,
        cache_token=_cache_token,
    )


async def provide_internal_user_service() -> InternalUserService:
    return InternalUserService(
        repo_user=__repo_user,
        cache_app=_cache_app,
    )


async def provide_internal_mqtt_service() -> MQTTService:
    return MQTTService(__queue_push_to_local_mqtt, settings.INTERNAL_MQTT_DEVICES_SETTINGS)
