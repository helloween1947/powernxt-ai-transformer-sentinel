"""Shared normalized-channel quality policy; no legacy score/detector dependency."""
import math
from .core import _timestamp
from .core import finite

CHANNELS = (
    "voltage_r_v", "voltage_y_v", "voltage_b_v",
    "current_r_a", "current_y_a", "current_b_a",
    "oil_temperature_c", "ambient_temperature_c", "oil_level_pct",
)
THERMAL_KEYS = ("rated_top_oil_rise_c", "oil_time_constant_min", "loss_ratio", "oil_exponent")

def _normalize(reading, quality_flags, config):
    if not isinstance(reading, dict) or not isinstance(quality_flags, dict):
        raise ValueError("Reading and quality flags must be maps")
    if set(quality_flags) - set(CHANNELS) - {"stale", "clamped"}:
        raise ValueError("Unknown quality flag channel")
    for key in ("stale", "clamped"):
        if key in quality_flags and type(quality_flags[key]) is not bool:
            raise ValueError(f"{key} must be boolean")
    if reading.get("schema_version") != "1.0.0":
        raise ValueError("Unsupported telemetry schema")
    source, run = reading.get("source"), reading.get("run_id")
    if source not in ("device", "simulator", "file_replay"):
        raise ValueError("Unsupported telemetry source")
    if not isinstance(reading.get("asset_id"), str) or not reading["asset_id"]:
        raise ValueError("Asset identity must be a nonempty string")
    if (source == "device" and run is not None) or (source != "device" and (not isinstance(run, str) or not run)):
        raise ValueError("Invalid source/run_id pairing")
    stamp = _timestamp(reading["timestamp"])
    quality = reading.get("measurement_quality", {})
    values = reading["measurements"]
    if not isinstance(values, dict) or not isinstance(quality, dict) or not isinstance(quality_flags, dict):
        raise ValueError("Measurements and quality must be maps")
    if set(values) - set(CHANNELS) or set(quality) - set(CHANNELS):
        raise ValueError("Unknown telemetry measurement channel")
    reasons, clean = {}, {}
    for channel in CHANNELS:
        value = values.get(channel)
        producer = quality.get(channel, "missing" if value is None else "good")
        if producer not in ("good", "suspect", "bad", "missing"):
            raise ValueError(f"Unsupported quality for {channel}")
        flags = quality_flags.get(channel, [])
        if not isinstance(flags, list) or not all(isinstance(flag, str) for flag in flags):
            raise ValueError("Ingestion quality flags must be lists of reasons per channel")
        problems = list(flags)
        if producer != "good":
            problems.append(producer)
        if not finite(value):
            problems.append("missing" if value is None else "invalid_number")
        elif channel.startswith(("current_", "voltage_")):
            rating = config["rated_current_a"] if channel.startswith("current_") else config["rated_voltage_v"]
            multiplier = 10 if channel.startswith("current_") else 2
            if not 0 <= value <= multiplier * rating:
                problems.append("outside_electrical_sanity_range")
        elif channel.endswith("temperature_c"):
            lower, upper = (-50, 80) if channel.startswith("ambient_") else (-50, 200)
            if not lower <= value <= upper:
                problems.append("outside_analytics_temperature_range")
        elif not 0 <= value <= 100:
            problems.append("outside_oil_level_range")
        if quality_flags.get("clamped") is True:
            problems.append("clamped_input")
        clean[channel] = None if problems else value
        if problems:
            reasons[channel] = sorted(set(problems))
    ll = config["voltage_convention"] == "line_to_line"
    volts = [clean[f"voltage_{p}_v"] for p in ("r", "y", "b")]
    if ll:
        volts = [v / math.sqrt(3) if v is not None else None for v in volts]
    core_reading = {
        "asset_id": reading["asset_id"], "timestamp": stamp.isoformat(),
        "source": "measured" if source == "device" else "simulated",
        "currents_a": [clean[f"current_{p}_a"] for p in ("r", "y", "b")],
        "voltages_v": volts, "oil_temp_c": clean["oil_temperature_c"],
        "ambient_temp_c": clean["ambient_temperature_c"],
    }
    return core_reading, clean, reasons
