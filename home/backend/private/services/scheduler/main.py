__import__("sys").path.append("/")
import asyncio
import os
from concurrent.futures.process import ProcessPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import msgspec
import netifaces
import utils
import uvloop  # type: ignore
from aiocron import crontab

from appdata import cfg_schema, shared

loop: asyncio.AbstractEventLoop = uvloop.new_event_loop()
asyncio.set_event_loop(loop)

DATA_PATH = Path(os.environ["DATA_PATH"])
CONFIG = cfg_schema.load_file(str(DATA_PATH / Path(cfg_schema.FILENAME)))

decode_sensor = msgspec.msgpack.Decoder(shared.SensorData).decode
cache = shared.ValkeyBasic(unix_socket_path="/mem/cache_data", max_connections=2)
process_pool = ProcessPoolExecutor(1)


CRON_DB_DUMP_MINUTE = 30


async def main():
    try:
        await asyncio.gather(
            ddns(CONFIG["ddns"]),
            scan_app_db_expired_registrations(),
        )
    finally:
        await cache.close()
        process_pool.shutdown(cancel_futures=True)


async def scan_app_db_expired_registrations():
    query = "DELETE FROM user WHERE user_id IN (SELECT user_id FROM mail_confirmation WHERE expiry_date < ?)"
    while True:
        try:
            async with utils.connect_db(DATA_PATH / Path(os.environ["DB_APP"])) as conn:
                await conn.execute(query, (shared.datetime_now_isofmtZ(),))
                await conn.commit()
        except Exception as e:
            shared.print_err(e)
        await asyncio.sleep(3600)


async def ddns(cfg: cfg_schema.FileKeyDDNS, update_interval: int = 600):
    # Add ip between part_get and part_http
    part_get = f"GET {cfg["path"].format(DOM=cfg["domain"], TOK=cfg["token"])}".encode()
    part_http = f" HTTP/1.1\r\nHost: {cfg["address"]}\r\nConnection: close\r\n\r\n".encode()
    last_ip = ""
    while True:
        try:
            for iface in netifaces.ifaddresses("eth0").values():
                ip = iface[0]["addr"]
                if ip.startswith("192"):
                    if ip != last_ip:
                        _, writer = await asyncio.open_connection(host=cfg["address"], port=443, ssl=True)
                        writer.write(part_get)
                        writer.write(ip.encode())
                        writer.write(part_http)
                        await writer.drain()
                        writer.close()
                        await writer.wait_closed()
                        last_ip = ip
                    break
            await asyncio.sleep(update_interval)
        except:
            await asyncio.sleep(180)


@crontab("40 3 * * *", tz=UTC, loop=loop)
async def backup_databases():
    TMP_FOLDER = "tmp"
    ZIP_FILE = "dbs.zip"

    await loop.run_in_executor(
        process_pool,
        utils.backup_db_routine,
        str(DATA_PATH),
        TMP_FOLDER,
        ZIP_FILE,
        [os.environ[key] for key in ("DB_INTERNAL", "DB_DATA", "DB_APP")],
        CONFIG["ftp"],
    )


@crontab("*/30 * * * *".format(CRON_DB_DUMP_MINUTE), tz=UTC, loop=loop)
async def dump_data_to_db():
    now = datetime.now(UTC)
    unixtime = int(now.timestamp())
    new_rows = []

    for device_data in (decode_sensor(x) for x in await cache.get_many(*await cache.keys("sensor:*")) if x):
        if (datetime.fromisoformat(device_data.date) + timedelta(minutes=CRON_DB_DUMP_MINUTE)) >= now:
            for key, value in device_data.data.items():
                type_id = shared.MeasurementTypes[key.upper()].value
                new_rows.append((unixtime, device_data.device_name, device_data.sensor_id, type_id, value))

    query = "INSERT INTO measurements (timestamp, device_name, sensor_id, type_id, value) VALUES (?,?,?,?,?)"
    async with utils.connect_db(DATA_PATH / Path(os.environ["DB_DATA"])) as conn:
        await conn.executemany(query, new_rows)
        await conn.commit()


if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
