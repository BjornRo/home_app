__import__("sys").path.append("/")
from os import environ

from appdata.distrilock_client import ClientUnix

"""LockStrat"""
__REGISTER = "/mem/register"
mail_lock = ClientUnix(0, __REGISTER)
user_login_lock = ClientUnix(1, __REGISTER)
reg_delete = ClientUnix(2, __REGISTER)


"""CacheStrat"""
_AUTH = "/mem/auth"
auth_jwt = ClientUnix(0, _AUTH)
auth_appuser = ClientUnix(1, _AUTH)
auth_exists = ClientUnix(2, _AUTH)  # user exists


_MISC = "/mem/misc"
misc_sensordata = ClientUnix(*next((int(sid), f"/mem/{path}") for path, sid in [environ["DL_SENSOR"].split("_")]))
misc_statusdata = ClientUnix(*next((int(sid), f"/mem/{path}") for path, sid in [environ["DL_STATUS"].split("_")]))

internal_user = ClientUnix(2, _MISC)
internal_user_exists = ClientUnix(3, _MISC)

_APP = "/mem/app" # 1 stores unused
api_request_cache = ClientUnix(0, _APP) # For example, fetching almost "static" resources (resources that barely change)


_ONLINE = "/mem/online"
online_users = ClientUnix(0, _ONLINE)  # Value could be what users browses, thinks or whatever.


"""CounterStrat"""
_COUNT = "/mem/count"  # misc locks
count_login_attempts = ClientUnix(0, _COUNT)


async def init_all():
    for i in (x for x in globals().values()):
        if isinstance(i, ClientUnix):
            await i.init()
