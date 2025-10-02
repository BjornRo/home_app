from core import types


class DatabaseError(Exception):
    """Base class for all database-related errors in the API."""

    pass


class UserInputError(Exception):
    """Raised when the caller provides invalid input, e.g., empty list for inserting new values."""

    pass


class NotFoundError(Exception):
    """Raised when a required object is not found, e.g user does not exist."""

    pass


class IntegrityError(Exception):
    """Raised when an integrity constraint is violated (e.g., FK, unique)."""

    pass


class ValidationError(Exception):
    """Raised when input data is invalid."""

    pass


class PermissionError(Exception):
    """Raised when the caller is not authorized to perform an operation."""

    pass


class NoChangeError(Exception):
    """Raised when an update request results in no changes (values are identical)."""

    pass


class AlreadyExistsError(Exception):
    """Raised when attempting to create a resource that already exists."""

    pass


class InvalidUserIDError(Exception):
    """Raised when a user ID is invalid or does not exist."""

    pass


# class UserDisabledError(Exception):
#     """Raised when a disabled user attempts to authenticate or perform restricted actions."""

#     pass
