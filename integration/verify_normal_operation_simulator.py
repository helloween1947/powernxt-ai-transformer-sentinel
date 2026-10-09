"""Verify the real local Docker API; retain unique demo records and output artifacts."""

import argparse
import json
import subprocess
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from backend.app.simulator.client import Client
from backend.app.simulator.generator import RunSpec, canonical, write_artifacts
from integration.verify_telemetry_ingestion import COUNT_SCRIPT


def verify(base_url):
    repo = Path(__file__).resolve().parents[1]
    client = Client(base_url)

    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    def counts(asset_id):
        # stdin avoids native PowerShell quote changes and never emits connection settings.
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "backend", "python", "-", asset_id],
            input=COUNT_SCRIPT,
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    _, ready = client.request("/health/ready")
    require(
        ready["status"] == "ready" and ready["database"] == "connected",
        "Backend is not ready",
    )
    token = uuid4().hex
    asset_id = "demo-normal-" + token
    run_id = "normal-" + token
    client.request(
        "/api/v1/assets",
        canonical(
            {
                "asset_id": asset_id,
                "name": "DEMONSTRATION - synthetic normal-operation",
                "location": "Assumed simulator lab",
                "timezone": "UTC",
            }
        ).encode(),
        expected=(201,),
    )
    configuration = json.loads(
        (repo / "data/sample/asset-configuration-assumed.json").read_text()
    )
    _, configured = client.request(
        f"/api/v1/assets/{asset_id}/configurations",
        canonical(configuration).encode(),
        expected=(201,),
    )
    selected = client.configuration(asset_id, configured["version"])
    spec = RunSpec(
        asset_id=asset_id,
        configuration_version=selected.version,
        run_id=run_id,
        seed=42,
        start="2026-01-01T00:00:00Z",
        duration_seconds=301,
        interval_seconds=60,
        initial_oil_temperature_c=45,
    )
    directory = repo / "data/generated" / run_id
    packets = write_artifacts(spec, selected, directory)
    data = (directory / "telemetry.jsonl").read_bytes().splitlines(keepends=True)
    first = client.send(data)
    require(
        first == {"created": 6, "identical_duplicates": 0, "failures": 0},
        "Unexpected first submission summary",
    )
    require(counts(asset_id) == [6, 6], "Expected six readings and six processing jobs")
    second = client.send(data)
    require(
        second == {"created": 0, "identical_duplicates": 6, "failures": 0},
        "Identical resend did not deduplicate",
    )
    require(counts(asset_id) == [6, 6], "Resend duplicated readings or jobs")
    stream = urlencode({"source": "simulator", "run_id": run_id})
    items = []
    offset = 0
    while True:
        _, page = client.request(
            f"/api/v1/assets/{asset_id}/telemetry?{stream}&limit=2&offset={offset}"
        )
        if not page["items"]:
            break
        items.extend(page["items"])
        offset += len(page["items"])
    require(
        [item["original_payload"] for item in items] == packets,
        "History does not preserve every packet in order",
    )
    require(
        all(
            item["configuration_version"] == selected.version
            and item["analytics_status"]
            == item["processing_job"]["status"]
            == "pending"
            and not item["out_of_order"]
            for item in items
        ),
        "Configuration/pending/order mismatch",
    )
    require(
        len({item["processing_job"]["id"] for item in items}) == 6,
        "Expected six distinct jobs",
    )
    _, empty = client.request(f"/api/v1/assets/{asset_id}/telemetry")
    require(empty["items"] == [], "Simulator data leaked into default device stream")
    _, latest = client.request(f"/api/v1/assets/{asset_id}/telemetry/latest?{stream}")
    require(
        latest == items[-1] and latest["measurement_time"] == packets[-1]["timestamp"],
        "Latest is not final measurement",
    )
    result = {
        "status": "PASS",
        "asset_id": asset_id,
        "source": "simulator",
        "run_id": run_id,
        "configuration_version": selected.version,
        "sample_count": len(packets),
        "first_submission": first,
        "resubmission": second,
        "database_counts": {"readings": 6, "jobs": 6},
        "latest_measurement_time": latest["measurement_time"],
        "latest_reading_id": latest["id"],
        "analytics_status": "pending",
        "default_device_history_count": 0,
        "output_directory": str(directory.relative_to(repo)),
    }
    (directory / "verification-result.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    verify(parser.parse_args().base_url)
