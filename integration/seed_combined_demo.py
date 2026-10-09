"""Create uniquely labelled sample assets/readings for C's optional browser verifier.

No DB administration, reset or deletion. Run against an isolated database only.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--api-base", default="http://127.0.0.1:8000")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
asset = "sample-combined-" + uuid4().hex[:12]
run = "sample-combined-" + uuid4().hex[:12]


def post(route, payload):
    request = Request(args.api_base.rstrip("/") + route, method="POST",
                      data=json.dumps(payload, allow_nan=False).encode(),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:
        assert response.status == 201
        return json.load(response)


post("/api/v1/assets", {"asset_id": asset, "name": "SAMPLE combined verification",
                       "location": "Isolated verification only", "timezone": "Asia/Kolkata"})
fields = {"rated_kva": 1000, "rated_voltage_v": 11000, "rated_current_a": 52.49,
          "voltage_convention": "line_to_line", "measurement_side": "primary", "cooling_type": "ONAN"}
post(f"/api/v1/assets/{asset}/configurations", {**fields, "parameter_provenance": {key: "assumed" for key in fields}})
payload = json.loads((Path(__file__).resolve().parents[1] / "data/sample/telemetry-sample.json").read_text())
start = datetime.now(timezone.utc)
for index in range(6):
    payload.update(asset_id=asset, source="simulator", run_id=run, message_id=str(uuid4()),
                   timestamp=(start + timedelta(seconds=index)).isoformat())
    post("/api/v1/telemetry", payload)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps({"asset_id": asset, "run_id": run, "readings": 6}, indent=2), encoding="utf-8")
print(f"Created labelled SAMPLE asset {asset} and simulator run {run}; six jobs remain pending")
