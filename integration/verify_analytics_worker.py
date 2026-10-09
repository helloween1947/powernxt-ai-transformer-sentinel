"""Isolated-only simulator -> jobs -> durable worker -> result API verification."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from backend.app.simulator.client import Client
from backend.app.simulator.generator import RunSpec, canonical, write_artifacts

DB_SCRIPT = """import json,sys
from sqlalchemy import select,func
from backend.app.db.session import SessionLocal,engine
from backend.app.models.analytics import AnalyticsResult,AnalyticsState,AnalyticsStream
from backend.app.models.telemetry import TelemetryReading,ProcessingJob
if not engine.url.database.endswith('_test'): raise RuntimeError('Isolated test DB required')
asset=sys.argv[1]
with SessionLocal() as db:
 counts={m.__tablename__:db.scalar(select(func.count()).select_from(m).where(TelemetryReading.asset_id==asset)) for m in []}
 counts['readings']=db.scalar(select(func.count()).select_from(TelemetryReading).where(TelemetryReading.asset_id==asset))
 counts['jobs']=db.scalar(select(func.count()).select_from(ProcessingJob).join(TelemetryReading,TelemetryReading.id==ProcessingJob.reading_id).where(TelemetryReading.asset_id==asset))
 counts['results']=db.scalar(select(func.count()).select_from(AnalyticsResult).join(TelemetryReading,TelemetryReading.id==AnalyticsResult.reading_id).where(TelemetryReading.asset_id==asset))
 counts['states']=[{'source':s.source,'run_key':s.run_key,'advances':s.advances,'state':s.state} for s in db.scalars(select(AnalyticsState).where(AnalyticsState.asset_id==asset).order_by(AnalyticsState.source,AnalyticsState.run_key))]
 counts['streams']=[{'source':s.source,'run_key':s.run_key,'advances':s.advances,'watermark_reading_id':s.watermark_reading_id} for s in db.scalars(select(AnalyticsStream).where(AnalyticsStream.asset_id==asset).order_by(AnalyticsStream.source,AnalyticsStream.run_key))]
 print(json.dumps(counts,sort_keys=True))
"""
CLAIM_SCRIPT = """from backend.app.db.session import SessionLocal,engine
from backend.app.services.analytics_worker import claim_next
if not engine.url.database.endswith('_test'): raise RuntimeError('Isolated test DB required')
claim=claim_next(SessionLocal,lease_seconds=2)
assert claim is not None
print('Abandoned isolated claim created')
"""


def verify(base_url):
    repo = Path(__file__).resolve().parents[1]
    project = os.environ.get("COMPOSE_PROJECT_NAME", "")
    if not project.startswith("analytics_worker_test_"):
        raise RuntimeError(
            "Use a unique analytics_worker_test_ Compose project and isolated override"
        )

    def compose(*args, **kwargs):
        return subprocess.run(
            ["docker", "compose", "--profile", "analytics", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            **kwargs,
        )

    # Resolve in memory only; configuration may contain credentials.
    config = json.loads(compose("config", "--format", "json").stdout)
    safe = (
        config["services"]["db"]["container_name"] == project + "-db"
        and config["services"]["backend"]["container_name"] == project + "-backend"
        and config["volumes"]["postgres_data"]["name"] == project + "-postgres_data"
        and config["services"]["db"]["environment"]["POSTGRES_DB"]
        == "worker_integration_test"
        and base_url.rstrip("/")
        == "http://" + compose("port", "backend", "8000").stdout.strip()
    )
    if not safe:
        raise RuntimeError(
            "Isolated project/container/volume/database/API mismatch; refusing restarts"
        )
    client = Client(base_url)

    def database(asset):
        return json.loads(
            compose(
                "exec", "-T", "backend", "python", "-", asset, input=DB_SCRIPT
            ).stdout
        )

    def await_result(reading_id):
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            _, response = client.request(f"/api/v1/telemetry/{reading_id}/analytics")
            if response["status"] in ("completed", "unavailable", "failed"):
                assert response["status"] != "failed", response
                return response
            time.sleep(0.2)
        raise RuntimeError("Worker did not complete demonstration job")

    def create_asset(asset):
        client.request(
            "/api/v1/assets",
            canonical(
                {
                    "asset_id": asset,
                    "name": "DEMONSTRATION - durable worker",
                    "location": "Synthetic lab",
                    "timezone": "UTC",
                }
            ).encode(),
            expected=(201,),
        )
        cfg = json.loads(
            (repo / "data/sample/asset-configuration-worker-assumed.json").read_text()
        )
        _, created = client.request(
            f"/api/v1/assets/{asset}/configurations",
            canonical(cfg).encode(),
            expected=(201,),
        )
        return client.configuration(asset, created["version"])

    token = uuid4().hex
    asset = "demo-worker-" + token
    run = "worker-" + token
    # Normal stop only for this independently named test worker.
    compose("stop", "worker")
    selected = create_asset(asset)
    spec = RunSpec(
        asset_id=asset,
        configuration_version=selected.version,
        run_id=run,
        seed=42,
        start="2026-01-01T00:00:00Z",
        duration_seconds=301,
        interval_seconds=60,
        initial_oil_temperature_c=45,
    )
    directory = repo / "data/generated" / run
    packets = write_artifacts(spec, selected, directory)
    readings = []
    for p in packets:
        _, response = client.request(
            "/api/v1/telemetry", canonical(p).encode(), expected=(201,)
        )
        readings.append(response)
    assert database(asset)["results"] == 0
    compose("up", "-d", "--no-build", "worker")
    results = [await_result(r["id"]) for r in readings]
    assert all(r["status"] == "completed" for r in results)
    assert (
        results[0]["result"]["payload"]["thermal_assessment"]["initial_condition"]
        is not None
    )
    assert all(
        r["result"]["payload"]["thermal_assessment"]["elapsed_s"] == 60
        for r in results[1:]
    )
    before = database(asset)
    assert (before["readings"], before["jobs"], before["results"]) == (6, 6, 6)
    assert (
        before["streams"][0]["advances"] == 6 and before["states"][0]["advances"] == 6
    )
    for p in packets:
        client.request("/api/v1/telemetry", canonical(p).encode(), expected=(200,))
    assert database(asset) == before
    compose("restart", "worker")
    assert database(asset) == before
    stream = urlencode({"source": "simulator", "run_id": run})
    _, latest = client.request(f"/api/v1/assets/{asset}/analytics/latest?{stream}")
    assert latest["latest_completed_reading_id"] == readings[-1]["id"]
    _, device = client.request(f"/api/v1/assets/{asset}/analytics/latest?source=device")
    assert device["result"] is None and device["latest_telemetry_reading_id"] is None
    # Leave a real claim unfinished, restart the worker and await lease recovery.
    compose("stop", "worker")
    recovery = dict(packets[-1])
    recovery.update(message_id=str(uuid4()), timestamp="2026-01-01T00:06:00Z")
    _, recover_reading = client.request(
        "/api/v1/telemetry", canonical(recovery).encode(), expected=(201,)
    )
    compose("exec", "-T", "backend", "python", "-", input=CLAIM_SCRIPT)
    compose("up", "-d", "--no-build", "worker")
    recovered = await_result(recover_reading["id"])
    assert recovered["status"] == "completed" and recovered["attempts"] == 2
    after = database(asset)
    assert (after["readings"], after["jobs"], after["results"]) == (7, 7, 7)
    assert after["streams"][0]["advances"] == 7 and after["states"][0]["advances"] == 7
    # A separate run on the same asset must bootstrap independent state.
    independent = dict(packets[0])
    independent.update(message_id=str(uuid4()), run_id=run + "-other")
    _, other = client.request(
        "/api/v1/telemetry", canonical(independent).encode(), expected=(201,)
    )
    other_result = await_result(other["id"])
    assert (
        other_result["result"]["payload"]["thermal_assessment"]["initial_condition"]
        is not None
    )
    final = database(asset)
    assert len(final["states"]) == len(final["streams"]) == 2
    assert sorted(s["advances"] for s in final["streams"]) == [1, 7]
    _, ready = client.request("/health/ready")
    assert ready["status"] == "ready"
    report = {
        "status": "PASS",
        "project": project,
        "asset_id": asset,
        "run_id": run,
        "first_batch_completed": 6,
        "identical_retries": 6,
        "restart_persistence": True,
        "recovery_attempts": recovered["attempts"],
        "final_readings": final["readings"],
        "final_jobs": final["jobs"],
        "final_results": final["results"],
        "stream_advances": sorted(s["advances"] for s in final["streams"]),
        "analytics_model": results[0]["result"]["model_version"],
        "image_basis": os.environ.get(
            "WORKER_VERIFICATION_IMAGE_BASIS", "record build evidence separately"
        ),
        "windows_execution": os.name == "nt",
    }
    (directory / "worker-verification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    verify(parser.parse_args().base_url)
