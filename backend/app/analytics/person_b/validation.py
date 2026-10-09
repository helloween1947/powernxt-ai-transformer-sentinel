"""Small standard-library validators for restored opaque model state."""
import json
from uuid import UUID

from .core import _timestamp, finite


def mapping(value, label, required=()):
    if not isinstance(value, dict) or not set(required).issubset(value):
        raise ValueError(f"{label} must be a map with its required fields")
    return value


def strict_json(value):
    try:
        json.dumps(value, allow_nan=False)
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Input/state must be finite JSON") from None


def identity(value):
    mapping(value, "Reading identity", ("reading_id", "message_id"))
    if type(value["reading_id"]) is not int or value["reading_id"] <= 0:
        raise ValueError("Reading identity requires a positive integer")
    try:
        if not isinstance(value["message_id"], str) or UUID(value["message_id"]).version != 4:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Reading identity requires a UUID4 string") from None
