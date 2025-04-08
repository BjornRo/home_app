import asyncio
import os
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime, timedelta
from zipfile import ZIP_LZMA, ZipFile

import asyncssh
import msgspec
import utils as ut
import uvloop  # type: ignore
from aiocron import crontab
from utils import dl_sensor, dl_status

loop: asyncio.AbstractEventLoop = uvloop.new_event_loop()
asyncio.set_event_loop(loop)

# Cron job for inserting data to db
CRON_AT_MINUTE = 30

DB = ut.SurrealDB(os.environ["DB_URI"], database="data", loop=loop)

""" FTP + SSH """
tmp_path = ut.DATA_PATH + "tmp/dbbks"
target_zip_file = f"{tmp_path}/{ut.DB_FILE}.zip"
db_names = ("api", "data", "internal")
ssh_cfg = {
    "host": "host.docker.internal",
    "port": ut.CFG["sshport"],
    "username": ut.CFG["sshuser"],
    "known_hosts": None,
    "client_keys": ["/certs/sensor_listener/sshkey"],
}
ftp = ut.SingleFileBackupFTP_TLS(**ut.CFG["ftp"], filepath=target_zip_file)


decode_sensor = msgspec.msgpack.Decoder(ut.SensorData).decode


def main():
    loop.run_until_complete(ut.MQTTHandler(dl_sensor=dl_sensor, dl_status=dl_status, db=DB).run())


def zip_file():
    with ZipFile(target_zip_file, "w", compression=ZIP_LZMA) as zip:
        for db_name in db_names:
            file_path = tmp_path + db_name
            zip.write(file_path, arcname=db_name)
            os.remove(file_path)


def upload_file_ftp():
    with ftp:
        return ftp.upload_file()


async def ssh_comm(commands: list[str]):
    async with asyncssh.connect(**ssh_cfg) as ssh:
        for c in commands:
            if (res := await ssh.run(c)).exit_status:
                raise RuntimeError(f"SSH exited with status: {res.stderr}")


commands = [
    f"mkdir -p ~/docker{tmp_path}",
    f"chmod 777 ~/docker{tmp_path}",
    *[
        f"docker exec graph /surreal export --conn http://127.0.0.1:5432 --ns app --db {db} {tmp_path}/{db}"
        for db in db_names
    ],
]


@crontab("15 14 * * *", tz=UTC, loop=loop)
async def backup_to_ftp(pool=ProcessPoolExecutor(max_workers=1)):  # Contact database to export databases.
    try:
        await ssh_comm(commands)
        try:
            await loop.run_in_executor(pool, zip_file)
            await crontab("15 * * * *").next()  # Wait till next 15min = ~1h wait.
            await loop.run_in_executor(pool, upload_file_ftp)
        except:
            pass
    except:
        raise
    finally:
        await ssh_comm([f"rm -rf ~/docker{tmp_path}"])


@crontab("*/{} * * * *".format(CRON_AT_MINUTE), tz=UTC, loop=loop)
async def dump_data_backup():
    keys = await ut.dl_sensor.keys("..20")

    dt_now = datetime.now(UTC)
    temp_new_data: list[ut.SensorData] = []

    for data in (decode_sensor(x) for _, x in await asyncio.gather(*(ut.dl_sensor.get(k) for k in keys))):
        if (datetime.fromisoformat(data.date) + timedelta(minutes=CRON_AT_MINUTE)) >= dt_now:
            data.date = ut.timenow_utc("seconds", dt_now)
            temp_new_data.append(data)
    if temp_new_data:
        ut.fire_forget_coro(DB.insert_data(temp_new_data))


if __name__ == "__main__":
    main()
