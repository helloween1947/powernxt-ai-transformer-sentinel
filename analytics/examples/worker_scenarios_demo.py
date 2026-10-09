"""Sanitized conditional forecasts for Person C; no recommended actions."""
import json
from pathlib import Path

from analytics import compare_worker_scenarios


def main():
    root = Path(__file__).resolve().parents[2]
    case = json.loads((root/"analytics/examples/worker-test-examples.json").read_text())["examples"][1]
    scenarios = [{"name": name, "profile": [{"duration_s": 7200, "thermal_load_pu": k, "ambient_temp_c": ambient}]}
                 for name, k, ambient in (("baseline", 1.0, 30), ("reduced_load", 0.5, 30), ("warmer_ambient", 1.0, 40))]
    inputs = {"current_state": case["output"]["updated_state"], "asset_config": case["input"]["asset_config"], "scenarios": scenarios}
    result = compare_worker_scenarios(**inputs)
    output = {"origin": "Actual synthetic execution using assumed thermal parameters; healthy continuation, not measured validation or maintenance advice.",
              "input": inputs, "output": result}
    (root/"analytics/examples/worker-scenarios-test-example.json").write_text(json.dumps(output, indent=2, allow_nan=False)+"\n")
    print("Wrote three conditional 2-hour scenarios sharing the identical initial state.")


if __name__ == "__main__":
    main()
