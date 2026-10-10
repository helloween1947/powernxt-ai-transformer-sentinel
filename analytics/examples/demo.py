"""Repository-root command: python -m analytics.examples.demo (stdlib only)."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from analytics import process_reading, compare_what_if
from analytics.transformer_twin import TwinEngine, update_thermal_state


def main():
    root = Path(__file__).resolve().parents[2]
    configuration = json.loads((root / "data/sample/asset-configuration-assumed.json").read_text())
    configuration.update(asset_id="XFR-SUB04-TX01", version=1)
    configuration["thermal_parameters"] = {
        "rated_top_oil_rise_c": 40, "oil_time_constant_min": 180,
        "loss_ratio": 5, "oil_exponent": 0.8,
    }
    configuration["parameter_provenance"].update({f"thermal_parameters.{k}": "assumed" for k in configuration["thermal_parameters"]})
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state, frames, readings = None, [], []
    for minute in range(12):
        load = 0.7 if minute < 3 else 1.3
        measurements = {f"voltage_{p}_v": 11000 for p in ("r", "y", "b")}
        measurements.update({f"current_{p}_a": configuration["rated_current_a"] * load for p in ("r", "y", "b")})
        measurements.update(oil_temperature_c=55, ambient_temperature_c=30, oil_level_pct=80)
        if state is not None:
            twin = TwinEngine.restore(state["engine"])
            expected = update_thermal_state(twin.state, {
                "currents_a": [configuration["rated_current_a"] * load] * 3,
                "ambient_temp_c": 30,
            }, 60).predicted_oil_temp_c
            measurements["oil_temperature_c"] = expected + (12 if minute >= 4 else 0)
        reading = {
            "schema_version": "1.0.0", "asset_id": configuration["asset_id"], "configuration_version": 1,
            "message_id": f"30000000-0000-4000-8000-{minute+1:012d}", "timestamp": (start + timedelta(minutes=minute)).isoformat(),
            "source": "simulator", "run_id": "personb-offset-demo", "measurements": measurements,
            "measurement_quality": {k: "good" for k in measurements},
        }
        output = process_reading(reading, {}, configuration, state)
        state = output["updated_state"]
        frames.append(output)
        readings.append(reading)
    scenarios = [{"name": name, "profile": [{"duration_s": 14400, "load_pu": load, "ambient_temp_c": 30, "cooling_factor": cooling}]}
                 for name, load, cooling in [("keep_load", 1.3, 1), ("reduce_load", 0.7, 1), ("improve_cooling", 1.3, 1.3)]]
    comparison = compare_what_if(state, scenarios)
    destination = Path(__file__).with_name("analytics_response.json")
    fixture = {
        "description": "Illustrative adapter fixture, not a persisted backend response. Thermal parameters are explicitly assumed. +12 C sensor offset is injected after minute 4; scenarios assume the stated cooling behavior.",
        "bound_configuration": configuration, "normalized_telemetry": readings,
        "analytics": frames, "what_if": comparison,
    }
    destination.write_text(json.dumps(fixture, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"fixture": str(destination), "opened_alerts": [a for f in frames for a in f["anomaly_observations"] if a["lifecycle"] == "opened"],
                      "scenario_final_temperatures_c": {s["name"]: round(s["forecast"]["final_oil_temp_c"], 2) for s in comparison["scenarios"]}}, indent=2))


if __name__ == "__main__":
    main()
