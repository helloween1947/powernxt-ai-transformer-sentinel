"""Create actual-execution test outputs and exact wire schemas; requires backend dev deps.

Run from repository root: python -m analytics.examples.generate_worker_examples
These local numerical inputs are not admitted telemetry or independent measured data.
"""
from copy import deepcopy
import json
from pathlib import Path

from analytics import process_stored_reading
from analytics.worker import MODEL_VERSION, RESULT_VERSION, STATE_VERSION
from backend.app.schemas.assets import ConfigurationResponse
from backend.app.schemas.telemetry import TelemetryCreate


def _schema(values):
    nonnull = [v for v in values if v is not None]
    if not nonnull:
        return {"type": "null"}
    value = nonnull[0]
    if isinstance(value, dict):
        keys = list(dict.fromkeys(key for item in nonnull for key in item))
        common = [key for key in keys if all(key in item for item in nonnull)]
        result = {"type": "object", "required": common, "additionalProperties": False,
                  "properties": {key: _schema([v.get(key) for v in nonnull]) for key in keys}}
    elif isinstance(value, list):
        items = [item for v in nonnull for item in v]
        result = {"type": "array", "items": _schema(items) if items else {"type": "string"}}
    elif isinstance(value, bool):
        result = {"type": "boolean"}
    elif isinstance(value, (int, float)):
        result = {"type": "number"}
    else:
        result = {"type": "string"}
    if len(nonnull) < len(values):
        result["type"] = [result["type"], "null"]
    return result


def main():
    root = Path(__file__).resolve().parents[2]
    base = json.loads((root / "data/sample/asset-configuration-assumed.json").read_text())
    base.update(asset_id="personb-worker-test", version=1, created_at="2026-01-01T00:00:00Z")
    thermal = deepcopy(base)
    thermal["thermal_parameters"] = {"rated_top_oil_rise_c": 40, "oil_time_constant_min": 180, "loss_ratio": 5, "oil_exponent": 0.8}
    thermal["parameter_provenance"].update({f"thermal_parameters.{k}": "assumed" for k in thermal["thermal_parameters"]})
    ConfigurationResponse.model_validate(thermal)
    examples, state = [], None
    for index, (name, cfg, oil) in enumerate((("observed_initialization", thermal, 55), ("analytical_elapsed_response", thermal, 60), ("parameters_unavailable", base, 55)), 1):
        if index == 3:
            state = None
        reading = {"schema_version": "1.0.0", "message_id": f"00000000-0000-4000-8000-{index:012d}", "asset_id": base["asset_id"],
                   "source": "simulator", "run_id": "personb-numerical-test-v1", "configuration_version": 1,
                   "timestamp": f"2026-01-01T00:0{index-1}:00Z",
                   "measurements": {**{f"voltage_{p}_v": 11000 for p in "ryb"}, **{f"current_{p}_a": 52.49 for p in "ryb"},
                                    "oil_temperature_c": oil, "ambient_temperature_c": 30, "oil_level_pct": None}}
        normalized = TelemetryCreate.model_validate(reading).model_dump(mode="json")
        stored = {"id": index, **{key: normalized.get(key) for key in ("asset_id", "source", "run_id", "configuration_version", "message_id")},
                  "measurement_time": normalized["timestamp"], "normalized_telemetry": normalized,
                  "quality_flags": {"oil_level_pct": ["missing"]}, "processing_job": {"state_policy": "forward_only"}}
        inputs = {"stored_reading": stored, "asset_config": cfg, "previous_state": state}
        result = process_stored_reading(**inputs)
        examples.append({"name": name, "input": deepcopy(inputs), "output": result})
        state = result["updated_state"]
    fixture = {"origin": "Actual local module execution on sanitized numerical test inputs; not backend admission, field data, or predictive validation.", "examples": examples}
    output_dir = Path(__file__).parent
    (output_dir / "worker-test-examples.json").write_text(json.dumps(fixture, indent=2, allow_nan=False) + "\n")
    outputs = [e["output"] for e in examples]
    result_schema = _schema(outputs)
    # Domains beyond the example values: missing inputs, historical state and errors.
    p = result_schema["properties"]
    p["updated_state"]["type"] = ["object", "null"]
    state_schema = deepcopy(p["updated_state"])
    held = state_schema["properties"]["held_inputs"]["properties"]
    for field in held.values():
        field["type"] = ["number", "null"]
    state_schema["properties"]["thermal"]["properties"]["reason"]["type"] = ["string", "null"]
    p["updated_state"] = deepcopy(state_schema)
    for key in ("phase_loading_pct",):
        p["electrical_metrics"]["properties"][key]["items"]["type"] = ["number", "null"]
    for key in ("max_phase_loading_pct", "thermal_load_pu", "current_magnitude_imbalance_pct", "voltage_magnitude_imbalance_pct", "apparent_power_kva", "capacity_loading_pct"):
        p["electrical_metrics"]["properties"][key]["type"] = ["number", "null"]
    th = p["thermal_assessment"]["properties"]
    th["measured_top_oil_temperature_c"]["type"] = ["number", "null"]
    # Rule checks may lack measurements or configured thresholds.
    rules = p["anomaly_observations"]["items"]["properties"]
    rules["value"]["type"] = rules["threshold"]["type"] = ["number", "null"]
    rules["breached"]["type"] = ["boolean", "null"]
    meta = p["metadata"]["properties"]
    meta["model_version"] = {"const": MODEL_VERSION}
    meta["result_schema_version"] = {"const": RESULT_VERSION}
    meta["parameter_provenance"] = {"type": "object", "additionalProperties": {"enum": ["assumed", "simulated", "nameplate", "measured"]}}
    state_schema["properties"]["schema_version"] = {"const": STATE_VERSION}
    state_schema["properties"]["binding"]["properties"]["model_version"] = {"const": MODEL_VERSION}
    # Device streams use null run IDs; simulation/replay use strings.
    meta["stream"]["properties"]["run_id"]["type"] = ["string", "null"]
    state_schema["properties"]["binding"]["properties"]["stream"]["properties"]["run_id"]["type"] = ["string", "null"]
    p["updated_state"] = deepcopy(state_schema)
    telemetry_schema = TelemetryCreate.model_json_schema()
    config_schema = ConfigurationResponse.model_json_schema()
    defs = {**telemetry_schema.pop("$defs", {}), **config_schema.pop("$defs", {}), "State": state_schema}
    properties = {"id": {"type": "integer", "minimum": 1},
                  "asset_id": {"type": "string"}, "source": {"enum": ["device", "simulator", "file_replay"]},
                  "run_id": {"type": ["string", "null"]}, "message_id": {"type": "string", "format": "uuid"},
                  "configuration_version": {"type": "integer", "minimum": 1}, "measurement_time": {"type": "string", "format": "date-time"},
                  "normalized_telemetry": telemetry_schema,
                  "quality_flags": {"type": "object", "properties": {"stale": {"type": "boolean"}, "clamped": {"type": "boolean"}},
                                    "propertyNames": {"enum": ["voltage_r_v", "voltage_y_v", "voltage_b_v", "current_r_a", "current_y_a", "current_b_a", "oil_temperature_c", "ambient_temperature_c", "oil_level_pct", "stale", "clamped"]},
                                    "additionalProperties": {"type": "array", "items": {"type": "string"}}},
                  "processing_job": {"type": "object", "required": ["state_policy"], "properties": {"state_policy": {"enum": ["forward_only", "historical_only"]}}}}
    request_schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Person B stored-reading request 1.0.0",
                      "$defs": defs, "type": "object", "required": ["stored_reading", "asset_config"], "additionalProperties": False,
                      "properties": {"stored_reading": {"type": "object", "required": list(properties), "properties": properties},
                                     "asset_config": config_schema, "previous_state": {"$ref": "#/$defs/State"}}}
    result_schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Person B stored-reading result 1.0.0"})
    result_schema["title"] = "Person B analytics result 1.1.0"
    p["execution_status"]["properties"]["outcome"] = {"enum": ["completed", "partially_available", "unsupported_configuration", "insufficient_input_or_state", "computation_error"]}
    normalized_schema = {"$schema": request_schema["$schema"], "$defs": deepcopy(defs),
                         "title": "Person B normalized analytics request 1.0.0", "type": "object", "additionalProperties": False,
                         "required": ["normalized_telemetry", "asset_config", "quality_flags", "reading_id"],
                         "properties": {"normalized_telemetry": telemetry_schema, "asset_config": config_schema,
                                        "quality_flags": properties["quality_flags"], "reading_id": properties["id"],
                                        "previous_state": {"$ref": "#/$defs/State"},
                                        "state_policy": {"enum": ["forward_only", "historical_only"], "default": "forward_only"}}}
    schema_dir = root / "analytics/schemas"
    schema_dir.mkdir(exist_ok=True)
    for name, schema in (("worker-input.schema.json", request_schema), ("worker-output.schema.json", result_schema), ("normalized-input.schema.json", normalized_schema)):
        (schema_dir / name).write_text(json.dumps(schema, indent=2) + "\n")
    print("Generated worker-test-examples.json and worker input/output JSON schemas.")


if __name__ == "__main__":
    main()
