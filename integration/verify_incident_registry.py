"""Repeatable isolated HTTP + fenced-worker verification. No development services.

Requires an already migrated test database, an API using that database on a
non-development loopback port, and a privately provisioned admin credential.
Creates unique synthetic test records and leaves them available for inspection.
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.app.models.assets import Asset
from backend.app.models.incidents import Incident, IncidentEvent, IncidentEvidence
from backend.app.services.analytics_worker import run_once


def verify(base_url, database_url, token_file):
    target, parsed = urlparse(base_url), make_url(database_url)
    if (
        target.hostname not in ("localhost", "127.0.0.1")
        or target.scheme != "http"
        or target.port in (None, 8000, 8001, 18001, 18002)
        or target.path.strip("/")
    ):
        raise ValueError("Use a dedicated non-development loopback test API port")
    if not parsed.drivername.startswith("postgresql") or not parsed.database.endswith(
        "_test"
    ):
        raise ValueError("Isolated PostgreSQL database ending in _test required")
    engine = create_engine(database_url)
    factory = sessionmaker(bind=engine)
    token = Path(token_file).read_text().strip()
    asset_id, run = "incident-test-" + uuid4().hex, "registry-" + uuid4().hex

    def checked(response, status=200):
        assert response.status_code == status, (
            f"Unexpected HTTP status {response.status_code}"
        )
        return response.json()

    try:
        with httpx.Client(
            base_url=base_url, headers={"Authorization": "Bearer " + token}, timeout=10
        ) as client:
            assert checked(client.get("/health/ready"))["database"] == "connected"
            actor = checked(client.get("/api/v1/operators/me"))
            assert actor["role"] == "admin"
            checked(
                client.post(
                    "/api/v1/assets",
                    json={
                        "asset_id": asset_id,
                        "name": "Synthetic incident verification",
                        "location": "Isolated test database",
                        "timezone": "UTC",
                    },
                ),
                201,
            )
            with factory() as db:
                assert db.get(Asset, asset_id), (
                    "API/database mismatch; do not run worker"
                )
            configuration = {
                "rated_kva": 1000,
                "rated_voltage_v": 11000,
                "rated_current_a": 52.49,
                "voltage_convention": "line_to_line",
                "measurement_side": "primary",
                "cooling_type": "ONAN",
            }
            configuration["parameter_provenance"] = {
                k: "assumed" for k in configuration
            }
            cfg = checked(
                client.post(
                    f"/api/v1/assets/{asset_id}/configurations", json=configuration
                ),
                201,
            )
            handover = {
                "schema_version": "incident-control-1.0.0",
                "expected_version": 0,
                "idempotency_key": str(uuid4()),
                "source": "simulator",
                "run_id": run,
                "configuration_version": cfg["version"],
                "model_version": "stored-reading-top-oil-1.0.1",
                "detector_version": "sustained-threshold-1.0.1",
                "reason": "Explicit synthetic test only, not calibration",
                "policy": {
                    "version": "isolated-assumed-v1",
                    "provenance": "assumed",
                    "max_gap_s": 300,
                    "rules": [
                        {
                            "name": "capacity_overload",
                            "quantity": "electrical_metrics.capacity_loading_pct",
                            "unit": "%",
                            "trigger": 120,
                            "recovery": 100,
                            "persistence_s": 180,
                            "recovery_s": 120,
                            "severity": "warning",
                        }
                    ],
                },
            }
            control = checked(
                client.post(
                    f"/api/v1/assets/{asset_id}/detector-handovers", json=handover
                ),
                201,
            )
            assert (
                checked(
                    client.post(
                        f"/api/v1/assets/{asset_id}/detector-handovers", json=handover
                    )
                )
                == control
            )
            query = {"asset_id": asset_id, "source": "simulator", "run_id": run}
            packets = []

            def reading(seconds, load):
                body = {
                    "schema_version": "1.0.0",
                    "asset_id": asset_id,
                    "source": "simulator",
                    "run_id": run,
                    "configuration_version": cfg["version"],
                    "message_id": str(uuid4()),
                    "timestamp": (
                        datetime(2026, 1, 1, tzinfo=timezone.utc)
                        + timedelta(seconds=seconds)
                    ).isoformat(),
                    "measurements": {
                        **{f"voltage_{p}_v": 11000 for p in "ryb"},
                        **{f"current_{p}_a": 52.49 * load for p in "ryb"},
                        "oil_temperature_c": 55,
                        "ambient_temperature_c": 30,
                    },
                }
                packets.append(body)
                admitted = checked(client.post("/api/v1/telemetry", json=body), 201)
                assert run_once(factory)
                assert (
                    checked(
                        client.get(f"/api/v1/telemetry/{admitted['id']}/analytics")
                    )["status"]
                    == "completed"
                )
                return admitted

            reading(0, 1.5)
            assert checked(client.get("/api/v1/incidents", params=query))["items"] == []
            reading(180, 1.5)
            opened = checked(client.get("/api/v1/incidents", params=query))["items"][0]
            iid = opened["incident_id"]
            ack = {
                "schema_version": "incident-acknowledgement-1.0.0",
                "expected_version": 1,
                "idempotency_key": str(uuid4()),
            }
            acknowledged = checked(
                client.post(f"/api/v1/incidents/{iid}/acknowledgements", json=ack), 201
            )
            assert acknowledged["condition_status"] == "active"
            reading(240, 0.5)
            reading(360, 0.5)
            recovered = checked(client.get(f"/api/v1/incidents/{iid}"))
            assert (
                recovered["incident_id"] == iid
                and recovered["condition_status"] == "recovered"
            )
            assert recovered["acknowledgement"] == acknowledged["acknowledgement"]
            assert (
                checked(
                    client.post(f"/api/v1/incidents/{iid}/acknowledgements", json=ack)
                )
                == acknowledged
            )
            for body in packets:
                checked(client.post("/api/v1/telemetry", json=body))
            assert not run_once(factory)
            evidence = checked(client.get(f"/api/v1/incidents/{iid}/evidence"))
            events = checked(client.get(f"/api/v1/incidents/{iid}/events"))
            assert len(evidence["items"]) == 3 and len(events["items"]) == 4
            for snapshot in evidence["items"]:
                bound = snapshot["payload"]
                exact = checked(
                    client.get(f"/api/v1/analytics/results/{bound['result_id']}")
                )
                assert exact["result"]["reading_id"] == bound["reading_id"]
            assert (
                checked(
                    client.get(
                        "/api/v1/incidents", params={**query, "run_id": "absent-run"}
                    )
                )["items"]
                == []
            )
            with factory() as db:
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(Incident)
                        .where(Incident.asset_id == asset_id)
                    )
                    == 1
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(IncidentEvidence)
                        .where(IncidentEvidence.incident_id == iid)
                    )
                    == 3
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(IncidentEvent)
                        .where(IncidentEvent.incident_id == iid)
                    )
                    == 4
                )
            return {
                "executed_utc": datetime.now(timezone.utc).isoformat(),
                "scope": "Actual HTTP and fenced worker; isolated PostgreSQL only; synthetic inputs",
                "asset_id": asset_id,
                "run_id": run,
                "control": control,
                "opened": opened,
                "acknowledged": acknowledged,
                "recovered": recovered,
                "evidence": evidence,
                "events": events,
                "checks": {
                    "canonical_episode": True,
                    "independent_ack_recovery": True,
                    "duplicate_no_extra_records": True,
                    "source_run_isolation": True,
                    "incident_count": 1,
                    "evidence_count": 3,
                    "event_count": 4,
                },
                "limitations": [
                    "No browser, production detector calibration, real device fault or maintenance FK verification",
                    "No development data or services changed; no restarts",
                ],
            }
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = verify(args.base_url, args.database_url, args.token_file)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: isolated HTTP/worker incident registry verification")


if __name__ == "__main__":
    main()
