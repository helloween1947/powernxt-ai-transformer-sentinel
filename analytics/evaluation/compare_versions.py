"""Compare exported implementations on deterministic valid numerical inputs.

Run this file with an absolute implementation root and redirect stdout to temporary
JSON. Compare the two output files: only model-version identifiers are excluded.
This checks behavior preservation, not predictive accuracy against measured data.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import sys


def without_model_version(value):
    if isinstance(value, dict):
        return {key: without_model_version(item) for key, item in value.items()
                if key != "model_version"}
    if isinstance(value, list):
        return [without_model_version(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("implementation_root", type=Path)
    root = parser.parse_args().implementation_root.resolve()
    if not (root / "analytics/worker.py").is_file():
        parser.error("Implementation root must contain analytics/worker.py")
    sys.path.insert(0, str(root))
    from analytics import process_stored_reading

    rng = random.Random(1947)
    base = json.loads((root / "data/sample/asset-configuration-assumed.json").read_text())
    base.update(asset_id="audit", version=1, created_at="2026-01-01T00:00:00Z")
    base["thermal_parameters"] = {"rated_top_oil_rise_c": 40, "oil_time_constant_min": 180,
                                  "loss_ratio": 5, "oil_exponent": 0.8}
    base["parameter_provenance"].update(
        {f"thermal_parameters.{key}": "assumed" for key in base["thermal_parameters"]})
    outputs = []
    for case in range(1000):
        config = json.loads(json.dumps(base))
        config["voltage_convention"] = "line_to_line" if case % 2 else "phase_to_neutral"
        factor = 3**0.5 if case % 2 else 3
        config["rated_kva"] = factor * config["rated_voltage_v"] * config["rated_current_a"] / 1000
        state = None
        stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for sample in range(2):
            stamp += timedelta(seconds=rng.randint(1, 300))
            measurements = {
                **{f"current_{p}_a": rng.uniform(0, 2 * config["rated_current_a"]) for p in "ryb"},
                **{f"voltage_{p}_v": rng.uniform(0.9, 1.1) * config["rated_voltage_v"] for p in "ryb"},
                "ambient_temperature_c": rng.uniform(-20, 50),
                "oil_temperature_c": rng.uniform(20, 100), "oil_level_pct": 80,
            }
            reading = {"schema_version": "1.0.0", "asset_id": "audit", "configuration_version": 1,
                       "source": "simulator", "run_id": f"audit-{case}",
                       "message_id": f"40000000-0000-4000-8000-{case*2+sample+1:012d}",
                       "timestamp": stamp.isoformat(), "measurements": measurements}
            stored = {"id": sample+1,
                      **{key: reading[key] for key in ("asset_id", "source", "run_id", "configuration_version", "message_id")},
                      "measurement_time": reading["timestamp"], "normalized_telemetry": reading,
                      "quality_flags": {}, "processing_job": {"state_policy": "forward_only"}}
            result = process_stored_reading(stored, config, state)
            state = result["updated_state"]
            outputs.append(without_model_version(result))
    print(json.dumps(outputs, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
