"""Small standard-library validators for restored opaque model state."""
import json
from uuid import UUID

from .transformer_twin.engine import _timestamp
from .transformer_twin.model import finite


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


def worker_state(value, schema_version):
    mapping(value, "Worker state", ("schema_version", "binding", "last_measurement_time", "last_reading_identity", "thermal", "held_inputs"))
    strict_json(value)
    if value["schema_version"] != schema_version:
        raise ValueError("State schema changed; explicit replay/cold start required")
    binding = mapping(value["binding"], "State binding", ("stream", "configuration_version", "model_version", "parameter_version"))
    stream = mapping(binding["stream"], "State stream", ("asset_id", "source", "run_id"))
    if not isinstance(stream["asset_id"], str) or not stream["asset_id"] or stream["source"] not in ("device", "simulator", "file_replay"):
        raise ValueError("Invalid state stream")
    if (stream["source"] == "device" and stream["run_id"] is not None) or (stream["source"] != "device" and (not isinstance(stream["run_id"], str) or not stream["run_id"])):
        raise ValueError("Invalid state source/run pairing")
    if type(binding["configuration_version"]) is not int or binding["configuration_version"] <= 0:
        raise ValueError("Invalid state configuration version")
    if not all(isinstance(binding[k], str) and binding[k] for k in ("model_version", "parameter_version")):
        raise ValueError("Invalid state version identifiers")
    _timestamp(value["last_measurement_time"])
    identity(value["last_reading_identity"])
    thermal = mapping(value["thermal"], "Thermal state", ("initialized", "valid", "oil_temp_c", "reason"))
    if any(type(thermal[k]) is not bool for k in ("initialized", "valid")):
        raise ValueError("Thermal validity/initialization must be booleans")
    if thermal["valid"] and not thermal["initialized"]:
        raise ValueError("Valid thermal state must be initialized")
    if thermal["initialized"] and not finite(thermal["oil_temp_c"]):
        raise ValueError("Initialized thermal state needs finite oil temperature")
    if not thermal["initialized"] and thermal["oil_temp_c"] is not None:
        raise ValueError("Uninitialized thermal state cannot have a temperature")
    if thermal["reason"] is not None and not isinstance(thermal["reason"], str):
        raise ValueError("Thermal reason must be null or a string")
    if not thermal["valid"] and not thermal["reason"]:
        raise ValueError("Invalid thermal state needs a reason")
    held = mapping(value["held_inputs"], "Held inputs", ("thermal_load_pu", "ambient_temp_c"))
    for key, low, high in (("thermal_load_pu", 0, 10), ("ambient_temp_c", -50, 80)):
        if held[key] is not None and (not finite(held[key]) or not low <= held[key] <= high):
            raise ValueError(f"Invalid held input: {key}")
