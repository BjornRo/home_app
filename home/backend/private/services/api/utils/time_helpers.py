import time
from datetime import UTC, datetime, timedelta
from typing import Any

from core import exceptions, types

from appdata import shared  # type: ignore


def unixtime() -> int:
    return int(time.time())


def parse_date(value: Any) -> shared.DateTimeUTC | None:
    if value is None:
        return None
    funcs = (
        lambda x: datetime.fromtimestamp(int(x)),
        lambda x: datetime.fromisoformat(x).replace(tzinfo=UTC),
    )
    for apply in funcs:
        try:
            return apply(value)
        except:
            pass
    raise ValueError("Date is not valid")


def get_uuid7_time(uuid: types.UserID) -> shared.DateTimeUTC:
    return datetime.fromtimestamp(int(uuid.replace("-", "")[:12], 16) / 1000, UTC)


def generate_end_date(time: shared.DateTimeUTC, date_primitive: types.DateT) -> str:
    match date_primitive:
        case None:
            return DATETIME_MAX_STR
        case timedelta() as t:
            if t.total_seconds() <= 0:
                raise exceptions.UserInputError(f"Invalid timedelta: {t.total_seconds()} <= 0")
            return shared.datetime_to_isofmtZ(time + t)
        case _:
            if date_primitive <= time:
                raise exceptions.UserInputError("Time is already expired")
            return shared.datetime_to_isofmtZ(date_primitive)


DATETIME_MIN_STR = "1970-01-01T00:00:00.000Z"
DATETIME_MAX_STR = "9999-12-31T23:59:59.000Z"
