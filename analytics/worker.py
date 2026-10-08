"""Conservative stored-reading analytics; pure computation, no storage or job writes.

Extends the existing electrical/top-oil implementation without invoking its optional
heuristic health, confidence, alert or forecast features.
"""
from copy import deepcopy
import hashlib
import json
import math
from uuid import UUID

from .adapter import CHANNELS, THERMAL_KEYS, _normalize
from .transformer_twin import AssetConfig, ThermalState
from .transformer_twin.engine import _timestamp
from .transformer_twin.model import _advance, finite

MODEL_VERSION = "stored-reading-top-oil-1.0.0"
STATE_VERSION = "stored-reading-state-1.0.0"
RESULT_VERSION = "stored-reading-result-1.0.0"
MAX_GAP_S = 300.0


def _positive_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _utc(value):
    return _timestamp(value).isoformat().replace("+00:00", "Z")


def _parameter_version(config):
    content = {key: value for key, value in config.items() if key != "created_at"}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return f"asset-config-{config['version']}:{digest}"


def _validate_config(reading, config):
    if config.get("asset_id") != reading["asset_id"] or config.get("version") != reading["configuration_version"]:
        raise ValueError("Use the reading-bound immutable ConfigurationResponse")
    if not _positive_integer(config.get("version")):
        raise ValueError("Configuration version must be a positive integer")
    for key in ("rated_current_a", "rated_voltage_v", "rated_kva"):
        if not finite(config.get(key)) or config[key] <= 0:
            raise ValueError(f"Invalid rating: {key}")
    if config.get("voltage_convention") not in ("line_to_line", "phase_to_neutral") or config.get("measurement_side") not in ("primary", "secondary"):
        raise ValueError("Explicit voltage convention and measurement side required")
    thermal = config.get("thermal_parameters", {})
    limits = config.get("operational_limits", {})
    provenance = config.get("parameter_provenance", {})
    if not all(isinstance(v, dict) for v in (thermal, limits, provenance)):
        raise ValueError("Configuration parameter groups must be maps")
    required = {"rated_kva", "rated_voltage_v", "rated_current_a", "voltage_convention", "measurement_side", "cooling_type"}
    for group, values in (("thermal_parameters", thermal), ("operational_limits", limits)):
        for key, value in values.items():
            if value is not None:
                if not finite(value) or (key != "max_top_oil_temp_c" and key != "max_hot_spot_temp_c" and value <= 0):
                    raise ValueError(f"Invalid configuration parameter: {group}.{key}")
                required.add(f"{group}.{key}")
    if set(provenance) != required or any(v not in ("assumed", "simulated", "nameplate", "measured") for v in provenance.values()):
        raise ValueError("Configuration must retain exact parameter provenance from registry")
    if not config.get("cooling_type"):
        raise ValueError("Cooling type required")
    _utc(config["created_at"])
    return [f"thermal_parameters.{key}" for key in THERMAL_KEYS if thermal.get(key) is None]


def _reading(record):
    if not _positive_integer(record.get("id")):
        raise ValueError("Stored reading requires a positive database id")
    normalized = record["normalized_telemetry"]
    # Allow a complete A response, but copy only known normalized fields into calculations.
    known = ("schema_version", "message_id", "asset_id", "source", "run_id", "configuration_version", "timestamp", "measurements", "measurement_quality")
    reading = {key: deepcopy(normalized[key]) for key in known if key in normalized}
    if not _positive_integer(reading.get("configuration_version")):
        raise ValueError("Positive configuration_version required")
    try:
        identifier = UUID(reading["message_id"])
    except (ValueError, AttributeError, TypeError):
        raise ValueError("message_id must be a UUID4 string") from None
    if identifier.version != 4:
        raise ValueError("message_id must be UUID4")
    for key in ("asset_id", "source", "configuration_version", "message_id"):
        if record[key] != reading[key]:
            raise ValueError(f"Stored envelope and normalized telemetry differ: {key}")
    if record.get("run_id") != reading.get("run_id") or _utc(record["measurement_time"]) != _utc(reading["timestamp"]):
        raise ValueError("Stored stream/time differs from normalized telemetry")
    return reading


def _imbalance(values):
    if any(v is None for v in values):
        return None
    mean = sum(values) / 3
    return 100 * max(abs(v - mean) for v in values) / mean if mean else None


def _rule(quantity, value, threshold, unit, relation):
    available = value is not None and threshold is not None
    return {"kind": "configured_limit_check", "quantity": quantity, "value": value,
            "threshold": threshold, "unit": unit, "relation": relation,
            "breached": (value > threshold if relation == "gt" else value < threshold) if available else None,
            "status": "available" if available else "unavailable",
            "reasons": [] if available else ["configured_limit_missing" if threshold is None else "usable_measurement_missing"],
            "interpretation": "Instant comparison only; not an alert, probability or maintenance recommendation."}


def process_stored_reading(stored_reading: dict, asset_config: dict, previous_state: dict | None = None) -> dict:
    """Return eight proposed contract categories for A's stored normalized reading.

    A supplies an immutable config, serializes access, and atomically persists result,
    returned state and job completion. This function does not provide exactly-once I/O.
    """
    reading = _reading(stored_reading)
    missing_parameters = _validate_config(reading, asset_config)
    if set(stored_reading["quality_flags"]) - set(CHANNELS) - {"stale", "clamped"}:
        raise ValueError("Only channel quality reasons and explicit stale/clamped controls are supported")
    _row, clean, channel_reasons = _normalize(reading, stored_reading["quality_flags"], asset_config)
    stamp = _utc(reading["timestamp"])
    identity = {"reading_id": stored_reading["id"], "message_id": reading["message_id"]}
    stream = {"asset_id": reading["asset_id"], "source": reading["source"], "run_id": reading.get("run_id")}
    parameter_version = _parameter_version(asset_config)
    binding = {"stream": stream, "configuration_version": reading["configuration_version"],
               "model_version": MODEL_VERSION, "parameter_version": parameter_version}
    policy = stored_reading["processing_job"]["state_policy"]
    if policy not in ("forward_only", "historical_only"):
        raise ValueError("Unknown processing job state policy")
    advance, ordering_reasons = policy == "forward_only", []
    elapsed = None
    if previous_state is not None:
        if previous_state.get("schema_version") != STATE_VERSION:
            raise ValueError("State schema changed; explicit replay/cold start required")
        if previous_state.get("binding") != binding:
            raise ValueError("State stream/configuration/model/parameter binding changed; explicit replay/cold start required")
        elapsed = (_timestamp(stamp) - _timestamp(previous_state["last_measurement_time"])).total_seconds()
        prior_identity = previous_state["last_reading_identity"]
        same_identity = identity["reading_id"] == prior_identity["reading_id"] or identity["message_id"] == prior_identity["message_id"]
        if same_identity and elapsed != 0:
            raise ValueError("Stored reading identity reused with a different measurement time")
        if elapsed <= 0:
            advance = False
            ordering_reasons.append("duplicate_or_equal_time" if elapsed == 0 else "out_of_order")
    if policy == "historical_only":
        ordering_reasons.append("historical_only")
    if stored_reading["quality_flags"].get("stale") is True:
        advance = False
        ordering_reasons.append("upstream_stale")

    currents = [clean[f"current_{p}_a"] for p in "ryb"]
    volts = [clean[f"voltage_{p}_v"] for p in "ryb"]
    rated_current = asset_config["rated_current_a"]
    loading = [100 * value / rated_current if value is not None else None for value in currents]
    complete_current = all(v is not None for v in currents)
    k = math.sqrt(sum((v / rated_current)**2 for v in currents) / 3) if complete_current else None
    complete_electrical = all(v is not None for v in currents + volts)
    line_line = asset_config["voltage_convention"] == "line_to_line"
    apparent = None
    if complete_electrical:
        apparent = math.sqrt(3) * (sum(volts) / 3) * (sum(currents) / 3) / 1000 if line_line else sum(v * i for v, i in zip(volts, currents)) / 1000
    if apparent is not None and not finite(apparent):
        apparent = None
    capacity_loading = apparent / asset_config["rated_kva"] * 100 if apparent is not None else None
    electrical = {"phase_loading_pct": loading, "max_phase_loading_pct": max(loading) if complete_current else None,
                  "thermal_load_pu": k, "current_magnitude_imbalance_pct": _imbalance(currents),
                  "voltage_magnitude_imbalance_pct": _imbalance(volts), "apparent_power_kva": apparent,
                  "capacity_loading_pct": capacity_loading,
                  "apparent_power_method": "balanced_approximation_sqrt3_mean_line_voltage_mean_line_current" if line_line else "sum_phase_neutral_voltage_times_line_current_magnitudes",
                  "voltage_convention": asset_config["voltage_convention"], "measurement_side": asset_config["measurement_side"],
                  "active_power_kw": None, "reactive_power_kvar": None, "power_factor": None, "symmetrical_components": None}

    predicted, residual, initialization = None, None, None
    thermal_reasons = list(missing_parameters)
    thermal = deepcopy(previous_state["thermal"]) if previous_state else {"initialized": False, "valid": False, "oil_temp_c": None, "reason": "awaiting_initial_condition"}
    if not advance:
        thermal_reasons.append("forward_state_not_advanced")
    elif missing_parameters:
        thermal.update(valid=False, reason="required_thermal_parameters_missing")
    elif not thermal["initialized"]:
        if k is not None and clean["ambient_temperature_c"] is not None and clean["oil_temperature_c"] is not None:
            thermal.update(initialized=True, valid=True, oil_temp_c=clean["oil_temperature_c"], reason=None)
            initialization = {"value": clean["oil_temperature_c"], "unit": "C", "source": reading["source"], "measurement_time": stamp}
            thermal_reasons.append("initialized_from_measurement_prediction_not_independent")
        else:
            thermal_reasons.append("usable_current_ambient_and_oil_required_for_initialization")
    elif not thermal["valid"]:
        thermal_reasons.append(thermal["reason"])
    elif elapsed > MAX_GAP_S:
        thermal.update(valid=False, reason="measurement_gap_exceeds_300_s")
        thermal_reasons.append(thermal["reason"])
    elif previous_state["held_inputs"]["thermal_load_pu"] is None or previous_state["held_inputs"]["ambient_temp_c"] is None:
        thermal.update(valid=False, reason="preceding_interval_inputs_unavailable")
        thermal_reasons.append(thermal["reason"])
    else:
        # Reuse the tested existing physical core, with all thermal coefficients explicit.
        params = asset_config["thermal_parameters"]
        held = previous_state["held_inputs"]
        try:
            core = AssetConfig(asset_id=reading["asset_id"], rated_current_a=rated_current,
                               rated_phase_voltage_v=asset_config["rated_voltage_v"] / (math.sqrt(3) if line_line else 1),
                               rated_oil_rise_c=params["rated_top_oil_rise_c"], time_constant_s=params["oil_time_constant_min"] * 60,
                               loss_ratio=params["loss_ratio"], oil_exponent=params["oil_exponent"])
            next_state = _advance(ThermalState(thermal["oil_temp_c"], held["ambient_temp_c"], core), held["thermal_load_pu"], held["ambient_temp_c"], elapsed)
            predicted = next_state.predicted_oil_temp_c
            thermal["oil_temp_c"] = predicted
        except (OverflowError, ValueError):
            thermal.update(valid=False, reason="thermal_arithmetic_unavailable")
            thermal_reasons.append(thermal["reason"])
        if predicted is not None and clean["oil_temperature_c"] is not None:
            residual = clean["oil_temperature_c"] - predicted
        elif predicted is not None:
            thermal_reasons.append("usable_oil_measurement_missing_for_residual")

    updated = deepcopy(previous_state)
    if advance:
        updated = {"schema_version": STATE_VERSION, "binding": binding, "last_measurement_time": stamp,
                   "last_reading_identity": identity, "thermal": thermal,
                   "held_inputs": {"thermal_load_pu": k, "ambient_temp_c": clean["ambient_temperature_c"]}}
    limits = asset_config.get("operational_limits", {})
    rules = [_rule("capacity_loading_pct", capacity_loading, limits.get("max_load_pct"), "%", "gt"),
             _rule("measured_top_oil_temperature_c", clean["oil_temperature_c"], limits.get("max_top_oil_temp_c"), "C", "gt")]
    for p, voltage in zip("ryb", volts):
        pu = voltage / asset_config["rated_voltage_v"] if voltage is not None else None
        rules.extend([_rule(f"voltage_{p}_pu", pu, limits.get("min_voltage_pu"), "pu", "lt"),
                      _rule(f"voltage_{p}_pu", pu, limits.get("max_voltage_pu"), "pu", "gt")])
    availability = {}
    for key, value in electrical.items():
        if key in ("apparent_power_method", "voltage_convention", "measurement_side"):
            continue
        available = all(v is not None for v in value) if isinstance(value, list) else value is not None
        reason = "phase_angles_or_power_channels_not_supplied" if key in ("active_power_kw", "reactive_power_kvar", "power_factor", "symmetrical_components") else "usable_required_channels_missing_or_zero_reference"
        availability[f"electrical_metrics.{key}"] = {"status": "available" if available else "unavailable", "reasons": [] if available else [reason]}
    availability["thermal_assessment.predicted_top_oil_temperature_c"] = {"status": "available" if predicted is not None else "unavailable", "reasons": [] if predicted is not None else thermal_reasons}
    availability["thermal_assessment.thermal_residual_c"] = {"status": "available" if residual is not None else "unavailable", "reasons": [] if residual is not None else thermal_reasons}
    unavailable_channels = [c for c in CHANNELS[:8] if clean[c] is None]
    status = "insufficient_data" if not advance or not complete_current else "computed" if predicted is not None and residual is not None and complete_electrical else "degraded"
    output = {
        "electrical_metrics": electrical,
        "thermal_assessment": {"predicted_top_oil_temperature_c": predicted, "measured_top_oil_temperature_c": clean["oil_temperature_c"],
                               "thermal_residual_c": residual, "initial_condition": initialization, "elapsed_s": elapsed,
                               "prediction_source": "estimated", "interval_convention": "previous_sample_zero_order_hold",
                               "winding_hot_spot_temperature_c": None, "reasons": thermal_reasons},
        "condition_contributors": {"health_index": None, "status": "not_assessed", "reason": "no_agreed_validated_health_model",
                                   "thermal_aging_acceleration_factor": None, "loss_of_life_rate": None},
        "data_confidence": {"score": None, "status": "not_estimated", "reason": "no_calibrated_confidence_model",
                            "usable_required_channel_count": 8 - len(unavailable_channels), "required_channel_count": 8,
                            "channels": {c: {"usable": clean[c] is not None, "reasons": channel_reasons.get(c, [])} for c in CHANNELS}},
        "anomaly_observations": rules,
        "updated_state": updated,
        "metadata": {"result_schema_version": RESULT_VERSION, "model_version": MODEL_VERSION, "parameter_version": parameter_version,
                     "reading_identity": identity, "stream": stream, "measurement_time": stamp, "configuration_version": reading["configuration_version"],
                     "measurement_source": reading["source"], "parameter_provenance": deepcopy(asset_config["parameter_provenance"]),
                     "units": {"phase_loading_pct": "%", "capacity_loading_pct": "%", "apparent_power_kva": "kVA", "thermal_load_pu": "pu",
                               "magnitude_imbalance": "%", "oil_temperature": "C", "thermal_residual": "C", "elapsed_s": "s"}},
        "execution_status": {"status": status, "state_advanced": advance, "state_policy": policy,
                             "ordering_reasons": ordering_reasons, "availability": availability,
                             "unavailable_measurements": unavailable_channels,
                             "unsupported_outputs": ["health_index", "confidence_score", "fault_probability", "forecasts", "maintenance_recommendations",
                                                     "winding_hot_spot_temperature_c", "thermal_aging_acceleration_factor", "loss_of_life_rate", "remaining_useful_life"]},
    }
    json.dumps(output, allow_nan=False)  # Wire output must remain strict finite JSON.
    return output
