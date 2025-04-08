from typing import TypedDict


class FileKeyMQTT_JWT(TypedDict):
    user: str
    pwd: str


class FileKeyAPI_MQTT_External(TypedDict):
    hostname: str
    port: int
    username: str
    password: str


class FileKeyAPI_MQTT_Internal(TypedDict):
    hostname: str
    port: int
    username: str
    password: str


class FileKeyMQTT(TypedDict):
    internal_subs: list[str]
    jwt: FileKeyMQTT_JWT
    external: FileKeyAPI_MQTT_External
    internal: FileKeyAPI_MQTT_Internal


class FileData(TypedDict):
    current_loc: str
    api_addr: str
    mqtt: FileKeyMQTT
