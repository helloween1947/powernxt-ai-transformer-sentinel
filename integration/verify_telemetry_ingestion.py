"""Repeatable telemetry API, dedup/job-count and restart-persistence verification.

Run from the repository root with Python 3.12 and the Compose backend running.
Creates a uniquely labelled demonstration asset/run; never removes records/volumes.
All sample values are synthetic and its configuration parameters are assumed.
"""

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

COUNT_SCRIPT = """
import json, sys
from sqlalchemy import select, func
from backend.app.db.session import SessionLocal
from backend.app.models import TelemetryReading, ProcessingJob
try:
    with SessionLocal() as db:
        readings = db.scalar(select(func.count()).select_from(TelemetryReading).where(TelemetryReading.asset_id == sys.argv[1]))
        jobs = db.scalar(select(func.count()).select_from(ProcessingJob).join(TelemetryReading, ProcessingJob.reading_id == TelemetryReading.id).where(TelemetryReading.asset_id == sys.argv[1]))
    print(json.dumps([readings, jobs]))
except Exception:
    raise SystemExit('Database count inspection unavailable') from None
"""


def verify(base_url):
    repo = Path(__file__).resolve().parents[1]

    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    def request(path, payload=None, expected=200):
        req = Request(
            base_url.rstrip("/") + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=5) as response:
            require(response.status == expected, f"Unexpected HTTP status for {path}")
            return json.load(response)

    def ready():
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                result = request("/health/ready")
                if result["status"] == "ready" and result["database"] == "connected":
                    return
            except (URLError, TimeoutError, ConnectionError):
                pass
            time.sleep(1)
        raise RuntimeError("Backend not ready within 60 seconds")

    def counts(asset_id):
        result = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "backend",
                "python",
                "-c",
                COUNT_SCRIPT,
                asset_id,
            ],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    ready()
    require(request("/health/live")["status"] == "live", "Liveness failed")
    asset_id = "demo-telemetry-" + uuid4().hex
    request(
        "/api/v1/assets",
        {
            "asset_id": asset_id,
            "name": "DEMONSTRATION - synthetic telemetry",
            "location": "Demo lab",
            "timezone": "Asia/Kolkata",
        },
        expected=201,
    )
    configuration = json.loads(
        (repo / "data/sample/asset-configuration-assumed.json").read_text()
    )
    configured = request(
        f"/api/v1/assets/{asset_id}/configurations", configuration, expected=201
    )
    packet = json.loads((repo / "data/sample/telemetry-sample.json").read_text())
    packet.update(
        asset_id=asset_id,
        message_id=str(uuid4()),
        run_id="demo-run-" + uuid4().hex,
        configuration_version=configured["version"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    first = request("/api/v1/telemetry", packet, expected=201)
    require(first["original_payload"] == packet, "Original payload was not retained")
    require(
        first["analytics_status"] == first["processing_job"]["status"] == "pending",
        "Analytics must remain pending",
    )
    selected = urlencode({"source": packet["source"], "run_id": packet["run_id"]})
    history = f"/api/v1/assets/{asset_id}/telemetry?{selected}"
    latest = f"/api/v1/assets/{asset_id}/telemetry/latest?{selected}"
    require(request(latest) == first, "Latest reading differs from accepted result")
    require(request(history)["items"] == [first], "Unexpected initial history")
    require(
        counts(asset_id) == [1, 1],
        "Expected exactly one reading and one processing job",
    )
    retry = request("/api/v1/telemetry", packet, expected=200)
    require(retry == first, "Identical retry did not return the existing result")
    require(request(history)["items"] == [first], "Retry duplicated the reading")
    require(counts(asset_id) == [1, 1], "Retry duplicated a reading or job")
    # Defaults select the live device stream; replay must not leak into it.
    require(
        request(f"/api/v1/assets/{asset_id}/telemetry")["items"] == [],
        "Replay leaked into live history",
    )
    subprocess.run(
        ["docker", "compose", "restart", "db", "backend"], cwd=repo, check=True
    )
    ready()
    require(
        request("/health/live")["status"] == "live", "Liveness failed after restart"
    )
    require(request(latest) == first, "Stored reading changed after restart")
    require(request(history)["items"] == [first], "History changed after restart")
    require(counts(asset_id) == [1, 1], "Reading/job counts changed after restart")
    require(
        request("/api/v1/telemetry", packet, expected=200) == first,
        "Retry after restart changed result",
    )
    require(counts(asset_id) == [1, 1], "Retry after restart duplicated the job")
    print(
        f"PASS: asset={asset_id}; reading={first['id']}; job={first['processing_job']['id']}; "
        "identical retries and backend/database restart retained exactly one reading and one pending job"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    verify(parser.parse_args().base_url)
