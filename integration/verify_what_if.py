"""Repeatable actual HTTP verification against a dedicated migrated test API/DB.

Creates unique synthetic asset/configurations/readings and retains evidence.
Never restarts services, migrates a database or touches an environment file.
"""

import argparse
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.app.services.analytics_worker import run_once


def verify(base_url, database_url):
    target, database = urlparse(base_url), make_url(database_url)
    if (
        target.scheme != "http"
        or target.hostname not in ("localhost", "127.0.0.1")
        or target.port in (None, 8000, 8001, 18001, 18002)
        or target.path.strip("/")
    ):
        raise ValueError("Dedicated non-development loopback test API required")
    if not database.drivername.startswith(
        "postgresql"
    ) or not database.database.endswith("_test"):
        raise ValueError("Isolated PostgreSQL *_test database required")
    engine = create_engine(database_url)
    factory = sessionmaker(bind=engine)
    asset_id, run_id = "what-if-test-" + uuid4().hex, "what-if-" + uuid4().hex
    origin = datetime.now(timezone.utc)
    cfg = json.loads(Path("data/sample/asset-configuration-assumed.json").read_text())
    # The registry sample intentionally has no thermal coefficients. Reuse the
    # existing worker test's explicitly assumed fixture, never tune a live asset.
    cfg["thermal_parameters"] = {
        "rated_top_oil_rise_c": 40,
        "oil_time_constant_min": 180,
        "loss_ratio": 5,
        "oil_exponent": 0.8,
    }
    cfg["parameter_provenance"].update(
        {"thermal_parameters." + key: "assumed" for key in cfg["thermal_parameters"]}
    )
    payload = {
        "schema_version": "what-if-request-1.0.0",
        "source": "simulator",
        "run_id": run_id,
        "baseline": {
            "duration_s": 86400,
            "thermal_load_pu": 2,
            "ambient_temperature_c": 30,
        },
        "reduced_load": {
            "duration_s": 86400,
            "thermal_load_pu": 1,
            "ambient_temperature_c": 30,
        },
    }
    examples = {}

    def checked(response, status=200):
        assert response.status_code == status, (
            f"Unexpected HTTP status {response.status_code}"
        )
        return response.json()

    def unchanged_worker_rows():
        with factory() as db:
            return {
                t: db.execute(
                    text(f"SELECT to_jsonb(t) FROM {t} t ORDER BY to_jsonb(t)")
                )
                .scalars()
                .all()
                for t in (
                    "analytics_streams",
                    "analytics_states",
                    "analytics_results",
                    "telemetry_processing_jobs",
                    "telemetry_readings",
                    "asset_configurations",
                )
            }

    try:
        with httpx.Client(base_url=base_url, timeout=15) as client:
            assert checked(client.get("/health/ready"))["database"] == "connected"
            checked(
                client.post(
                    "/api/v1/assets",
                    json={
                        "asset_id": asset_id,
                        "name": "Synthetic what-if verification",
                        "location": "Isolated test lab",
                        "timezone": "UTC",
                    },
                ),
                201,
            )
            with factory() as db:
                assert (
                    db.scalar(
                        text("SELECT count(*) FROM assets WHERE asset_id=:asset"),
                        {"asset": asset_id},
                    )
                    == 1
                )

            def reading(seconds, version):
                body = json.loads(Path("data/sample/telemetry-sample.json").read_text())
                body.update(
                    asset_id=asset_id,
                    source="simulator",
                    run_id=run_id,
                    message_id=str(uuid4()),
                    configuration_version=version,
                    timestamp=(origin + timedelta(seconds=seconds)).isoformat(),
                )
                body["measurements"].update(
                    {
                        **{f"current_{p}_a": 52.49 for p in "ryb"},
                        **{f"voltage_{p}_v": 11000 for p in "ryb"},
                        "ambient_temperature_c": 30,
                        "oil_temperature_c": 55,
                    }
                )
                checked(client.post("/api/v1/telemetry", json=body), 201)
                assert run_once(factory)

            version = checked(
                client.post(f"/api/v1/assets/{asset_id}/configurations", json=cfg), 201
            )["version"]
            reading(0, version)
            before = unchanged_worker_rows()
            path = f"/api/v1/assets/{asset_id}/what-if"
            actual = checked(client.post(path, json=payload))
            assert unchanged_worker_rows() == before
            assert (
                actual["baseline"]["points"][0] == actual["reduced_load"]["points"][0]
            )
            assert actual["baseline"]["limit_crossing"]["status"] == "crossing"
            assert actual["final_temperature_difference_c"] < 0
            examples["success"] = {
                "method": "POST",
                "path": path,
                "request": payload,
                "http_status": 200,
                "response": actual,
            }
            fixed = {**payload, "state_ref": actual["state"]["state_ref"]}
            reading(60, version)
            assert checked(client.post(path, json=fixed)) == actual
            examples["explicit_reference_request"] = fixed
            no_limit = deepcopy(cfg)
            no_limit["operational_limits"] = {}
            no_limit["parameter_provenance"] = {
                key: value
                for key, value in no_limit["parameter_provenance"].items()
                if not key.startswith("operational_limits.")
            }
            version = checked(
                client.post(f"/api/v1/assets/{asset_id}/configurations", json=no_limit),
                201,
            )["version"]
            reading(120, version)
            unlimited = checked(client.post(path, json=payload))
            assert unlimited["baseline"]["limit_crossing"]["status"] == "unavailable"
            examples["missing_limit"] = {"http_status": 200, "response": unlimited}
            empty = deepcopy(no_limit)
            empty["thermal_parameters"] = {}
            empty["parameter_provenance"] = {
                k: v
                for k, v in empty["parameter_provenance"].items()
                if not k.startswith("thermal_parameters.")
            }
            version = checked(
                client.post(f"/api/v1/assets/{asset_id}/configurations", json=empty),
                201,
            )["version"]
            reading(180, version)
            errors = {
                "missing_model_parameters": (path, payload, 409),
                "asset_not_found": (
                    "/api/v1/assets/what-if-unregistered-" + uuid4().hex + "/what-if",
                    payload,
                    404,
                ),
                "state_not_found": (path, {**payload, "state_ref": str(uuid4())}, 404),
                "invalid_request": (
                    path,
                    {
                        **payload,
                        "baseline": {**payload["baseline"], "duration_s": True},
                    },
                    422,
                ),
                "incompatible_state_identity": (
                    path,
                    {**fixed, "run_id": "other-run"},
                    409,
                ),
                "state_unavailable": (
                    path,
                    {**payload, "run_id": "not-started-run"},
                    409,
                ),
            }
            examples["errors"] = {}
            for code, (error_path, body, status) in errors.items():
                response = checked(client.post(error_path, json=body), status)
                assert response["detail"]["code"] == code
                examples["errors"][code] = {
                    "path": error_path,
                    "request": body,
                    "http_status": status,
                    "response": response,
                }
            # Restore the original assumed test configuration in a new version;
            # a subsequent measurement gap must reject current state, not fall back.
            version = checked(
                client.post(f"/api/v1/assets/{asset_id}/configurations", json=cfg), 201
            )["version"]
            reading(240, version)
            reading(840, version)
            response = checked(client.post(path, json=payload), 409)
            assert response["detail"]["code"] == "ineligible_state"
            examples["errors"]["ineligible_state"] = {
                "path": path,
                "request": payload,
                "http_status": 409,
                "response": response,
            }
            return {
                "executed_utc": datetime.now(timezone.utc).isoformat(),
                "scope": "Actual isolated HTTP/worker, synthetic inputs; no browser/deployment",
                "asset_id": asset_id,
                "run_id": run_id,
                "examples": examples,
                "checks": {
                    "worker_state_results_jobs_unchanged_by_forecast": True,
                    "shared_initial_state": True,
                    "analytic_crossing": True,
                    "snapshot_retained_after_advancement": True,
                    "missing_limit_is_null_unavailable": True,
                    "versioned_errors": True,
                },
            }
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    Path(args.output).write_text(
        json.dumps(verify(args.base_url, args.database_url), indent=2) + "\n"
    )
    print("PASS: actual isolated what-if HTTP/worker verification")


if __name__ == "__main__":
    main()
