"""Independent fine-step synthetic plant; labels belong to this evaluator only."""
import json
import math
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from analytics.transformer_twin import TwinEngine


def evaluate_case(name):
    rng = random.Random(42)
    engine = TwinEngine()
    plant_temperature = 55.0
    errors, events = [], []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for minute in range(601):
        fault = 120 <= minute < 300
        currents = [35.0] * 3
        cooling = 1.0
        if fault and name == "overload":
            currents = [65.0] * 3
        if fault and name == "imbalance":
            currents = [65.0, 25.0, 25.0]
        if fault and name == "reduced_cooling":
            cooling = 0.45
        # Physical reference integrated using Euler at 5 s, independently of model update.
        load_squared = sum((v / 50.0) ** 2 for v in currents) / 3
        equilibrium = 30 + 40 * ((1 + 5 * load_squared) / 6) ** 0.8 / cooling
        if minute:
            for _ in range(12):
                plant_temperature += 5 * (equilibrium - plant_temperature) / (10800 / cooling)
        row = {"asset_id": engine.config.asset_id, "timestamp": (start + timedelta(minutes=minute)).isoformat(),
               "source": "simulated", "currents_a": currents, "voltages_v": [260.0] * 3,
               "ambient_temp_c": 30.0, "oil_temp_c": plant_temperature + rng.gauss(0, 0.35)}
        if fault and name == "sensor_failure":
            row["oil_temp_c"] = None
        output = engine.process(row)
        if output["thermal"]["residual_c"] is not None:
            errors.append(output["thermal"]["residual_c"])
        for event in output["alerts"]["events"]:
            events.append({"minute": minute, "type": event["type"], "lifecycle": event["lifecycle"]})
    expected = {"overload": "overload", "imbalance": "current_imbalance", "reduced_cooling": "unexpected_heating", "sensor_failure": "data_unavailable"}.get(name)
    opens = [e for e in events if e["lifecycle"] == "opened"]
    found = next((e for e in opens if e["type"] == expected and e["minute"] >= 120), None)
    return {"case": name, "samples": 601, "oil_residual_rmse_c": math.sqrt(sum(v*v for v in errors) / len(errors)),
            "expected_alert": expected, "detected": found is not None if expected else None,
            "latency_from_injection_s": (found["minute"] - 120) * 60 if found else None,
            "normal_false_openings": len(opens) if name == "normal" else None, "events": events}


def main():
    cases = [evaluate_case(n) for n in ("normal", "overload", "imbalance", "reduced_cooling", "sensor_failure")]
    report = {"scope": "Synthetic consistency checks only; no timestamped real thermal data supplied.",
              "plant": "5 s Euler integration; same nominal thermal assumptions; 0.35 C Gaussian sensor noise; seed 42; 60 s samples; fault at 120-300 min.",
              "limitations": "Shared model family makes this a consistency test, not independent field validation or fault-classification accuracy. Cooling fault latency includes physical heating time.",
              "cases": cases,
              "checks": {"normal_rmse_below_0_5_c": cases[0]["oil_residual_rmse_c"] < 0.5,
                         "normal_no_false_openings": cases[0]["normal_false_openings"] == 0,
                         "all_injected_cases_detected": all(c["detected"] for c in cases[1:])}}
    Path(__file__).with_name("results.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))
    if not all(report["checks"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
