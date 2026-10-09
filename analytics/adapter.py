"""Adapter for Person A's implemented telemetry/registry contracts.

No raw payload, labels, latest-config lookup, I/O, or worker/job mutations.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math

from .transformer_twin import (
    AssetConfig, ThermalState, TwinEngine, detect_anomalies, compare_scenarios,
)
from .transformer_twin.engine import _timestamp
from .transformer_twin.model import finite

STATE_VERSION = "sentinel-analytics-state-1.0"
MODEL_VERSION = "sentinel-twin-0.2.0"
DETECTOR_POLICY_VERSION = "threshold-persistence-1.0"
CHANNELS = (
    "voltage_r_v", "voltage_y_v", "voltage_b_v",
    "current_r_a", "current_y_a", "current_b_a",
    "oil_temperature_c", "ambient_temperature_c", "oil_level_pct",
)
THERMAL_KEYS = ("rated_top_oil_rise_c", "oil_time_constant_min", "loss_ratio", "oil_exponent")


def _fingerprint(config):
    # A's configuration is immutable; include provenance and all fields, except publication time.
    bound = {k: v for k, v in config.items() if k != "created_at"}
    return hashlib.sha256(json.dumps(bound, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _configuration(reading, config):
    if config.get("asset_id") != reading["asset_id"] or config.get("version") != reading["configuration_version"]:
        raise ValueError("Pass the exact bound ConfigurationResponse (asset_id and version must match)")
    for key in ("rated_kva", "rated_current_a", "rated_voltage_v"):
        if not finite(config.get(key)) or config[key] <= 0:
            raise ValueError(f"Missing or invalid configuration: {key}")
    convention = config.get("voltage_convention")
    if convention not in ("phase_to_neutral", "line_to_line"):
        raise ValueError("Unsupported voltage convention")
    thermal = config.get("thermal_parameters") or {}
    unavailable = [f"thermal_parameters.{k}" for k in THERMAL_KEYS if thermal.get(k) is None]
    mapping = {
        "rated_top_oil_rise_c": "rated_oil_rise_c", "oil_time_constant_min": "time_constant_s",
        "loss_ratio": "loss_ratio", "oil_exponent": "oil_exponent",
    }
    parameters = {}
    for key, target in mapping.items():
        if thermal.get(key) is not None:
            if not finite(thermal[key]) or thermal[key] <= 0:
                raise ValueError(f"Invalid thermal parameter: {key}")
            parameters[target] = thermal[key] * 60 if key == "oil_time_constant_min" else thermal[key]
    limits = config.get("operational_limits") or {}
    oil_limit = limits.get("max_top_oil_temp_c")
    load_limit = limits.get("max_load_pct")
    for key, value in (("max_top_oil_temp_c", oil_limit), ("max_load_pct", load_limit)):
        if value is not None and (not finite(value) or (key == "max_load_pct" and value <= 0)):
            raise ValueError(f"Invalid operational limit: {key}")
    if oil_limit is not None:
        parameters.update(oil_warning_c=oil_limit, oil_critical_c=oil_limit + 15)
    if load_limit is not None:
        parameters["overload_warning_pct"] = load_limit
    core = AssetConfig(asset_id=reading["asset_id"], rated_current_a=config["rated_current_a"],
                       rated_phase_voltage_v=config["rated_voltage_v"] / (math.sqrt(3) if convention == "line_to_line" else 1),
                       **parameters)
    return core, unavailable, limits


def _normalize(reading, quality_flags, config):
    if reading.get("schema_version") != "1.0.0":
        raise ValueError("Unsupported telemetry schema")
    source, run = reading.get("source"), reading.get("run_id")
    if source not in ("device", "simulator", "file_replay"):
        raise ValueError("Unsupported telemetry source")
    if (source == "device" and run is not None) or (source != "device" and not run):
        raise ValueError("Invalid source/run_id pairing")
    stamp = _timestamp(reading["timestamp"])
    quality = reading.get("measurement_quality") or {}
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


def _observation(kind, item, stream, version, lifecycle, limits, epoch):
    evidence = deepcopy(item.get("evidence", {}))
    severity = item.get("severity", "warning")
    if kind == "high_oil_temperature" and limits.get("max_top_oil_temp_c") is not None:
        severity = "critical"  # Persistent breach of the explicitly configured maximum.
    sequence = item.get("sequence", 1)
    namespace = f"{stream['asset_id']}:{stream['source']}:{stream['run_id'] or 'live'}:cfg{version}:epoch{epoch}"
    return {
        "incident_id": f"{namespace}:{kind}:{sequence}", "category": kind, "severity": severity,
        "lifecycle": lifecycle, "evidence": evidence, "threshold": evidence.get("trigger"),
        "anomaly_score": None, "evidence_available": item.get("evidence_available", True),
        "rationale": "Continuous threshold evidence opened this incident; missing evidence does not resolve it."
                     if lifecycle != "resolved" else "Continuous evidence below the recovery threshold resolved this incident.",
    }


def _process(reading, quality_flags, asset_config, previous_state, *, policy="forward_only", arrival_time=None):
    core, missing_parameters, limits = _configuration(reading, asset_config)
    row, clean, quality_reasons = _normalize(reading, quality_flags, asset_config)
    stream = {"asset_id": reading["asset_id"], "source": reading["source"], "run_id": reading.get("run_id")}
    version, fingerprint = reading["configuration_version"], _fingerprint(asset_config)
    epoch = previous_state.get("state_epoch", previous_state["last_measurement_time"]) if previous_state else row["timestamp"]
    reasons = []
    if policy not in ("forward_only", "historical_only"):
        raise ValueError("Unknown job state policy")
    advance = policy == "forward_only"
    engine = None
    if previous_state is not None:
        if previous_state.get("schema_version") != STATE_VERSION or previous_state.get("stream") != stream:
            raise ValueError("Previous state must match this asset/source/run_id and state schema")
        watermark = previous_state["last_measurement_time"]
        if _timestamp(row["timestamp"]) <= _timestamp(watermark):
            advance = False
            reasons.append("not_newer_than_processed_watermark")
        if advance:
            if previous_state["configuration_version"] != version or previous_state["configuration_fingerprint"] != fingerprint:
                raise ValueError("Configuration changed: explicitly replay or cold-start a new bound state")
            engine = TwinEngine.restore(previous_state["engine"])
    if quality_flags.get("stale") is True:
        advance = False
        reasons.append("upstream_stale")
    if reading["source"] == "device" and arrival_time is not None:
        age = (_timestamp(arrival_time) - _timestamp(row["timestamp"])).total_seconds()
        if age < 0 or age > core.max_gap_s:
            advance = False
            reasons.append("future_measurement" if age < 0 else "stale_at_arrival")
    if policy == "historical_only":
        reasons.append("historical_only")
    thermal_initialized = bool(previous_state and previous_state.get("thermal_initialized")) if engine else False
    if engine is None:
        engine = TwinEngine(core)
        engine.state = ThermalState(core.initial_oil_temp_c, core.initial_ambient_temp_c, core, False,
                                    "thermal_parameters_unavailable" if missing_parameters else "initial_temperature_unavailable")
    if advance and not missing_parameters and not thermal_initialized and clean["oil_temperature_c"] is not None and clean["ambient_temperature_c"] is not None:
        engine.initialize_temperature(clean["oil_temperature_c"], clean["ambient_temperature_c"])
        thermal_initialized = True
        reasons.append("initialized_from_first_usable_oil_measurement")
    if not advance:
        # Compute electrical diagnostics without using or modifying forward thermal history.
        engine = TwinEngine(core)
        engine.state = ThermalState(core.initial_oil_temp_c, core.initial_ambient_temp_c, core, False, "forward_state_not_advanced")
    prior_history = deepcopy(engine.alert_history)
    previous_time = engine.last_timestamp
    result = engine.process(row)
    elapsed = (_timestamp(row["timestamp"]) - _timestamp(previous_time)).total_seconds() if previous_time else 0.0
    metric = result["electrical"]
    detector_metrics = deepcopy(metric)
    if limits.get("max_load_pct") is None:
        detector_metrics["max_loading_pct"] = None
    if advance:
        detected = detect_anomalies(detector_metrics, {
            "elapsed_s": elapsed, "timestamp": row["timestamp"],
            "residual_c": result["thermal"]["residual_c"],
            "oil_temp_c": clean["oil_temperature_c"] if limits.get("max_top_oil_temp_c") is not None else None,
            "data_unavailable": 1 - result["data_quality"]["coverage"],
        }, prior_history)
        engine.alert_history = detected["history"]
    else:
        history = deepcopy(previous_state["engine"]["alert_history"]) if previous_state else {}
        for item in history.values():
            item["evidence_available"] = False
        detected = {"history": history, "events": []}
    observations = []
    observation_version = previous_state["configuration_version"] if not advance and previous_state else version
    observation_limits = {"max_top_oil_temp_c": previous_state["engine"]["config"]["oil_warning_c"]} if not advance and previous_state else limits
    transitions = {e["type"]: e["lifecycle"] for e in detected["events"]}
    for kind, item in detected["history"].items():
        if item["active"] or transitions.get(kind) == "resolved":
            observations.append(_observation(kind, item, stream, observation_version, transitions.get(kind, "active"), observation_limits, epoch))
    voltages = [clean[f"voltage_{p}_v"] for p in ("r", "y", "b")]
    currents = [clean[f"current_{p}_a"] for p in ("r", "y", "b")]
    if asset_config["voltage_convention"] == "line_to_line":
        power = math.sqrt(3) * (sum(voltages) / 3) * (sum(currents) / 3) / 1000 if all(v is not None for v in voltages + currents) else None
        power_method = "balanced_system_approximation_from_mean_line_line_voltage_and_mean_line_current"
    else:
        power, power_method = metric["apparent_power_kva"], "sum_phase_voltage_times_phase_current"
    unavailable_measurements = [channel for channel in CHANNELS[:8] if clean[channel] is None]
    confidence = (8 - len(unavailable_measurements)) / 8 if advance else 0.0
    predicted = result["thermal"]["predicted_oil_temp_c"] if advance and not missing_parameters else None
    residual = result["thermal"]["residual_c"] if predicted is not None else None
    condition = deepcopy(result["condition"])
    condition["data_confidence"] = confidence
    if limits.get("max_top_oil_temp_c") is None:
        for contributor in condition["contributors"]:
            if contributor["name"] == "oil_temperature":
                contributor.update(penalty=None, healthy_limit=None, full_penalty_at=None)
        condition.update(health_index=None, status="unknown")
    unavailable_estimates = ["symmetrical_components", "active_power_kw", "reactive_power_kvar", "power_factor",
                             "winding_hot_spot_temperature_c", "thermal_aging_acceleration_factor", "loss_of_life_rate", "remaining_useful_life"]
    if predicted is None:
        unavailable_estimates.extend(["predicted_top_oil_temperature_c", "thermal_residual_c", "temperature_forecast"])
    if clean["oil_temperature_c"] is None:
        unavailable_estimates.append("action_forecast_initial_temperature")
    if not missing_parameters and not engine.state.valid:
        reasons.append(engine.state.reason)
    if missing_parameters:
        reasons.append("missing_thermal_parameters")
    if limits.get("max_load_pct") is None:
        reasons.append("overload_alert_unavailable_without_configured_limit")
    if limits.get("max_top_oil_temp_c") is None:
        reasons.append("oil_temperature_alert_unavailable_without_configured_limit")
    if unavailable_measurements:
        reasons.append("missing_or_rejected_measurements")
    updated_state = deepcopy(previous_state)
    if advance:
        updated_state = {
            "schema_version": STATE_VERSION, "stream": stream, "configuration_version": version,
            "state_epoch": epoch,
            "configuration_fingerprint": fingerprint, "last_measurement_time": row["timestamp"],
            "thermal_initialized": thermal_initialized, "thermal_parameters_available": not missing_parameters,
            "forecast_initial_oil_temp_c": clean["oil_temperature_c"], "forecast_ambient_temp_c": clean["ambient_temperature_c"],
            "engine": engine.snapshot(),
        }
    status = "insufficient_data" if not advance or metric["thermal_load_pu"] is None else "degraded" if predicted is None or unavailable_measurements else "computed"
    return {
        "electrical_metrics": {
            "phase_loading_pct": [100 * v / core.rated_current_a if v is not None else None for v in currents],
            "max_phase_loading_pct": metric["max_loading_pct"], "thermal_load_pu": metric["thermal_load_pu"],
            "current_magnitude_imbalance_pct": metric["current_imbalance_pct"],
            "voltage_magnitude_imbalance_pct": metric["voltage_imbalance_pct"],
            "apparent_power_kva": power, "apparent_power_method": power_method,
            "capacity_loading_pct": 100 * power / asset_config["rated_kva"] if power is not None else None,
            "symmetrical_components": None, "active_power_kw": None, "reactive_power_kvar": None, "power_factor": None,
            "voltage_convention": asset_config["voltage_convention"], "measurement_side": asset_config["measurement_side"],
        },
        "thermal_assessment": {
            "predicted_top_oil_temperature_c": predicted, "measured_top_oil_temperature_c": clean["oil_temperature_c"],
            "thermal_residual_c": residual, "winding_hot_spot_temperature_c": None,
            "prediction_source": "estimated", "valid": predicted is not None,
            "missing_configuration_parameters": missing_parameters,
            "forecast_initial_oil_temp_c": clean["oil_temperature_c"] if predicted is not None else None,
        },
        "condition_contributors": {**condition, "thermal_aging_acceleration_factor": None, "loss_of_life_rate": None},
        "data_confidence": {"score": confidence, "method": "usable_required_channels_over_8",
                            "unavailable_measurements": unavailable_measurements, "quality_reasons": quality_reasons,
                            "oil_level_available": clean["oil_level_pct"] is not None},
        "anomaly_observations": observations,
        "updated_state": updated_state,
        "metadata": {
            "model_version": MODEL_VERSION, "detector_policy_version": DETECTOR_POLICY_VERSION,
            "configuration_version": version, "configuration_fingerprint": fingerprint,
            "stream": stream, "measurement_time": row["timestamp"],
            "evaluation_time": datetime.now(timezone.utc).isoformat(),
            "parameter_provenance": deepcopy(asset_config.get("parameter_provenance", {})),
            "measurement_source": reading["source"],
            "assumptions": ["First usable oil measurement establishes the initial condition; subsequent measurements are not assimilated.",
                            "No phase angles: magnitude imbalance only; no sequence components or power factor.",
                            "Fixed oil time constant; no winding or aging model. Threshold/persistence and health-score policy are heuristic."]},
        "execution_status": {"status": status, "state_advanced": advance, "state_policy": policy,
                             "unavailable_measurements": unavailable_measurements,
                             "unavailable_estimates": unavailable_estimates, "reasons": sorted(set(reasons))},
    }


def process_reading(reading, quality_flags, asset_config, previous_state=None):
    """Proposed team entrypoint, using normalized_telemetry and immutable ConfigurationResponse.

    Caller serializes and atomically persists state per (asset_id, source, run_id).
    For queued jobs use process_telemetry_response to also enforce admission policy.
    """
    return _process(reading, quality_flags, asset_config, previous_state)


def process_telemetry_response(response, asset_config, previous_state=None):
    """Consume the actual ingestion API result, never original_payload or fault metadata."""
    reading = response["normalized_telemetry"]
    for field in ("asset_id", "source", "configuration_version"):
        if response[field] != reading[field]:
            raise ValueError("Ingestion response envelope differs from normalized telemetry")
    if response.get("run_id") != reading.get("run_id") or _timestamp(response["measurement_time"]) != _timestamp(reading["timestamp"]):
        raise ValueError("Ingestion response stream/time mismatch")
    return _process(reading, response["quality_flags"], asset_config, previous_state,
                    policy=response["processing_job"]["state_policy"], arrival_time=response["arrival_time"])


def compare_what_if(updated_state, scenarios):
    """Action comparison anchored to measured oil, with explicit scenario cooling assumptions."""
    if not updated_state or updated_state.get("schema_version") != STATE_VERSION:
        raise ValueError("A matching analytics state is required")
    engine = TwinEngine.restore(updated_state["engine"])
    initial, ambient = updated_state["forecast_initial_oil_temp_c"], updated_state["forecast_ambient_temp_c"]
    if not updated_state["thermal_parameters_available"] or not engine.state.valid or initial is None or ambient is None:
        raise ValueError("What-if needs configured thermal parameters, valid history and measured initial temperature")
    result = compare_scenarios(ThermalState(initial, ambient, engine.config), scenarios)
    result.update(initial_temperature_source={"device": "measured", "simulator": "simulated", "file_replay": "file_replay"}[updated_state["stream"]["source"]],
                  prediction_source="estimated", stream=deepcopy(updated_state["stream"]),
                  configuration_version=updated_state["configuration_version"])
    return result
