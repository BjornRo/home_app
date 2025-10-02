import re

from core import constants, settings
from core.exceptions import ValidationError

# from core.types import Err, Ok, Result

# mail_validate = re.compile(r"(^[\w\.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]*[a-zA-Z0-9]$)")
mail_validate = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")
name_validate = re.compile(r"(^([\._]?[a-zA-Z]+[0-9]*)+[\._]?$)")


def validate_mail(mail: str) -> None:
    if (not (6 <= len(mail) <= 50)) or mail_validate.match(mail) is None:
        raise ValidationError("Valid mail is required")


def validate_name(name: str, min_len=1, max_len=34) -> None:
    if not (min_len <= len(name) <= max_len):
        raise ValidationError(f"Username must be between {min_len} and {max_len} characters long")

    name_low = name.lower().strip()
    if name_low in constants.INVALID_NAMES:
        raise ValidationError("Username is not allowed")

    if name_validate.match(name) is None or not any(c.isalpha for c in name):
        raise ValidationError("Here is the regex D: =>" + name_validate.pattern)


def validate_password(password: str) -> None:
    if not (settings.MIN_PASSWORD_LENGTH < len(password) <= 100):
        raise ValidationError(f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long")
    if not (
        any(c.isupper() for c in password) and any(c.islower() for c in password) and any(c.isdigit() for c in password)
    ):
        raise ValidationError("Password must contain at least one number, and capital and lowercase letter")
