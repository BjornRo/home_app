import os

DB_DATA = os.environ.get("DB_DATA", "data.db")
DB_APP = os.environ.get("DB_APP", "app.db")
DATA_PATH = os.environ.get("DATA_PATH", "./appdata/")

CA_FILEPATH = os.environ.get("CA_FILEPATH", "")

REFRESH_KEYDATA_PATH = "/certs/api/api_refresh.json"
ACCESS_KEYDATA_PATH = "/certs/api/api_access.json"
