from datetime import timedelta
from os import environ

from core import paths, settings
from utils import helpers

REFRESH_TIMEDELTA = int(timedelta(days=int(environ["REFRESH_JWT_DAYS"])).total_seconds())
ACCESS_TIMEDELTA = int(timedelta(minutes=int(environ["ACCESS_JWT_MINUTES"])).total_seconds())

ACCESS_KEYDATA = helpers.load_jwtkeys_json(paths.ACCESS_KEYDATA_PATH)
REFRESH_KEYDATA = helpers.load_jwtkeys_json(paths.REFRESH_KEYDATA_PATH)

"""
ed25519: "EdDSA"
ES###: "ES###"
"""
ALGORITHMS = ["EdDSA"]

ISS = f"https://api.{settings.HOSTNAME}/auth"
AUD = {"api": f"https://api.{settings.HOSTNAME}", "root": f"https://{settings.HOSTNAME}"}
