"""Executed synthetic evidence demonstration, not validated fault detection."""
import json
from pathlib import Path

from analytics import compute_analytics, evaluate_persistent_rules


def main():
    root = Path(__file__).resolve().parents[2]
    fixtures = json.loads((root/"analytics/examples/worker-test-examples.json").read_text())
    request = fixtures["examples"][0]["input"]
    config = request["asset_config"]
    # Explicit assumed policy; no production recommendation or hidden fallback.
    policy = {"version": "demo-capacity-v1", "provenance": "assumed", "max_gap_s": 300,
              "rules": [{"name": "capacity_overload", "quantity": "electrical_metrics.capacity_loading_pct", "unit": "%",
                         "trigger": 120, "recovery": 100, "persistence_s": 180, "recovery_s": 120, "severity": "warning"}]}
    twin_state, detector_state, frames = None, None, []
    for index, (seconds, load) in enumerate(((0, 1.5), (60, 1.5), (120, 1.5), (180, 1.5), (240, 0.5), (300, 0.5), (360, 0.5)), 1):
        telemetry = json.loads(json.dumps(request["stored_reading"]["normalized_telemetry"]))
        telemetry["timestamp"] = f"2026-01-01T00:{seconds//60:02d}:00Z"
        telemetry["message_id"] = f"00000000-0000-4000-8000-{index:012d}"
        for phase in "ryb":
            telemetry["measurements"][f"current_{phase}_a"] = config["rated_current_a"]*load
        analytics = compute_analytics(telemetry, config, request["stored_reading"]["quality_flags"], index, twin_state)
        prior = detector_state
        detector = evaluate_persistent_rules(analytics, policy, prior)
        frames.append({"analytics_result": analytics, "previous_detector_state": prior, "detector_result": detector})
        twin_state, detector_state = analytics["updated_state"], detector["updated_state"]
    output = {"origin": "Actual synthetic module execution; assumed policy, not measured fault validation or published alerts.",
              "policy": policy, "frames": frames}
    path = root/"analytics/examples/persistent-rules-test-example.json"
    path.write_text(json.dumps(output, indent=2, allow_nan=False)+"\n")
    print("Wrote persistent-rules-test-example.json: opened at180s, resolved at360s.")


if __name__ == "__main__":
    main()
