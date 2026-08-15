"""
Utility functions for payment gateways.
"""
import base64
import logging
import time
from typing import Union

from .exceptions import InternalServiceError, exception_whitelist


logger = logging.getLogger(__name__)


def generate_timestamp() -> int:
    """
    Generate a Unix timestamp.

    Returns:
        Current Unix timestamp in seconds
    """
    return int(time.time())


def format_amount(amount: Union[int, float, str]) -> int:
    """
    Format amount to integer (in tiyin).

    Args:
        amount: Amount in som

    Returns:
        Amount in tiyin (integer)
    """
    try:
        return int(float(amount) * 100)
    except (ValueError, TypeError) as e:
        logger.error("Failed to format amount: %s, Error: %s", amount, e)
        raise ValueError(f"Invalid amount format: {amount}") from e


def generate_basic_auth(username: str, password: str) -> str:
    """
    Generate a Basic Authentication header value.

    Args:
        username: Username
        password: Password

    Returns:
        Basic Authentication header value
    """
    auth_bytes = f"{username}:{password}".encode('utf-8')
    encoded = base64.b64encode(auth_bytes).decode('utf-8')
    return f"Basic {encoded}"


def handle_exceptions(func):
    """
    Decorator that converts unexpected exceptions into payment exceptions.

    Exceptions listed in ``exception_whitelist`` are re-raised untouched;
    anything else is wrapped in ``InternalServiceError``.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exception_whitelist:
            raise
        except Exception as exc:
            logger.exception("Unexpected error in %s: %s", func.__name__, exc)
            raise InternalServiceError(str(exc)) from exc

    return wrapper
