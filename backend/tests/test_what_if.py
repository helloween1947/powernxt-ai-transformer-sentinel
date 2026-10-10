"""Isolated PostgreSQL HTTP comparisons, immutable capture and worker isolation."""

import copy
import json
import math
from concurrent.futures import ThreadPoolExecutor
from itertools import pairwise
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend.app.models.what_if import WhatIfSnapshot
from backend.app.services.analytics_worker import run_once
from backend.tests import test_analytics_worker as worker

configured = worker.configured


def request(**changes):
    result = {
        "schema_version": "what-if-request-1.0.0",
        "source": "simulator",
        "run_id": "worker-test",
        "baseline": {
            "duration_s": 3600,
            "thermal_load_pu": 1.5,
            "ambient_temperature_c": 30,
        },
        "reduced_load": {
            "duration_s": 3600,
            "thermal_load_pu": 0.75,
            "ambient_temperature_c": 30,
        },
    }
    result.update(changes)
    return result


def post(setup, payload=None, asset_id=None):
    client, _, asset, *_ = setup
    return client.post(
        f"/api/v1/assets/{asset_id or asset}/what-if", json=payload or request()
    )


def bootstrap(setup, **options):
    worker.submit(setup, **options)
    assert run_once(setup[1])


def rows(factory):
    with factory() as db:
        return {
            table: db.execute(
                text(f"SELECT to_jsonb(t) FROM {table} t ORDER BY to_jsonb(t)")
            )
            .scalars()
            .all()
            for table in (
                "analytics_streams",
                "analytics_states",
                "analytics_results",
                "telemetry_processing_jobs",
                "telemetry_readings",
                "asset_configurations",
            )
        }


def with_limit(setup, limit):
    client, _, asset, cfg = setup
    cfg = copy.deepcopy(cfg)
    cfg["operational_limits"] = {"max_top_oil_temp_c": limit}
    cfg["parameter_provenance"]["operational_limits.max_top_oil_temp_c"] = "assumed"
    response = client.post(f"/api/v1/assets/{asset}/configurations", json=cfg)
    assert response.status_code == 201
    bootstrap(setup, version=response.json()["version"])


def test_identical_initial_state_zero_time_and_no_worker_writes(configured):
    bootstrap(configured)
    before = rows(configured[1])
    payload = request()
    payload["reduced_load"] = dict(payload["baseline"])
    response = post(configured, payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["baseline"] == body["reduced_load"]
    assert body["final_temperature_difference_c"] == 0
    assert body["baseline"]["points"][0] == {
        "elapsed_s": 0,
        "estimated_top_oil_temperature_c": 55,
    }
    assert body["baseline"]["points"][-1]["elapsed_s"] == 3600
    assert body["state"]["measurement_time"] == "2026-01-01T00:00:00Z"
    assert body["configuration"]["version"] == 1
    assert body["model"]["model_version"] == "stored-reading-top-oil-1.0.1"
    assert rows(configured[1]) == before
    again = post(configured, payload)
    assert again.json() == body
    with configured[1]() as db:
        assert db.scalar(select(func.count()).select_from(WhatIfSnapshot)) == 1


@pytest.mark.parametrize(
    "duration,load,ambient",
    [(5e-324, 0, -50), (1e-6, 0, -50), (60, 10, 80), (86400, 0, 80)],
)
def test_supported_boundaries_and_bounded_sampling(configured, duration, load, ambient):
    bootstrap(configured)
    segment = {
        "duration_s": duration,
        "thermal_load_pu": load,
        "ambient_temperature_c": ambient,
    }
    response = post(configured, request(baseline=segment, reduced_load=segment))
    assert response.status_code == 200, response.text
    body = response.json()
    points = body["baseline"]["points"]
    assert len(points) == max(1, min(96, math.ceil(duration / 60))) + 1
    assert points[0]["elapsed_s"] == 0 and points[-1]["elapsed_s"] == duration
    assert all(a["elapsed_s"] < b["elapsed_s"] for a, b in pairwise(points))
    assert body["baseline"]["peak_top_oil_temperature_c"] == max(
        p["estimated_top_oil_temperature_c"] for p in points
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("duration_s", True),
        ("duration_s", 0),
        ("duration_s", 86401),
        ("duration_s", "60"),
        ("thermal_load_pu", False),
        ("thermal_load_pu", -1),
        ("thermal_load_pu", 10.01),
        ("ambient_temperature_c", True),
        ("ambient_temperature_c", -50.1),
        ("ambient_temperature_c", 80.1),
        ("cooling_factor", 1),
        ("worker_state", {}),
    ],
)
def test_reject_invalid_segment_inputs(registry, asset, field, value):
    client, factory = registry
    payload = request()
    payload["baseline"][field] = value
    response = client.post(f"/api/v1/assets/{asset['asset_id']}/what-if", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_request"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(WhatIfSnapshot)) == 0


@pytest.mark.parametrize(
    "edit",
    [
        {
            "baseline": {
                "duration_s": 60,
                "thermal_load_pu": 1,
                "ambient_temperature_c": 30,
            }
        },
        {
            "reduced_load": {
                "duration_s": 3600,
                "thermal_load_pu": 2,
                "ambient_temperature_c": 30,
            }
        },
        {
            "reduced_load": {
                "duration_s": 3600,
                "thermal_load_pu": 0.75,
                "ambient_temperature_c": 31,
            }
        },
        {"source": "device"},
        {"run_id": None},
        {"state": {}},
        {"thermal_parameters": {}},
        {"schema_version": "unknown"},
    ],
)
def test_exact_schema_and_comparison_constraints(configured, edit):
    response = post(configured, request(**edit))
    assert (
        response.status_code == 422
        and response.json()["detail"]["code"] == "invalid_request"
    )


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "1e999"])
def test_nonfinite_json_rejected(configured, constant):
    body = json.dumps(request()).replace("3600", constant, 1)
    response = configured[0].post(
        f"/api/v1/assets/{configured[2]}/what-if",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert (
        response.status_code == 422
        and response.json()["detail"]["code"] == "invalid_request"
    )


def test_missing_state_asset_and_reference(configured):
    assert (
        post(configured, asset_id="missing").json()["detail"]["code"]
        == "asset_not_found"
    )
    assert post(configured).json()["detail"]["code"] == "state_unavailable"
    response = post(configured, request(state_ref=str(uuid4())))
    assert (
        response.status_code == 404
        and response.json()["detail"]["code"] == "state_not_found"
    )


def test_limit_unavailable_is_not_no_crossing(configured):
    bootstrap(configured)
    body = post(configured).json()
    assert body["configured_top_oil_limit_c"] is None
    assert body["baseline"]["limit_crossing"] == {
        "status": "unavailable",
        "time_s": None,
        "reasons": ["configured_top_oil_limit_missing"],
    }
    assert body["final_temperature_difference_c"] < 0


@pytest.mark.parametrize("limit", [55, 54, 1000])
def test_initial_equality_exceedance_and_no_crossing(configured, limit):
    with_limit(configured, limit)
    body = post(configured).json()
    crossing = body["baseline"]["limit_crossing"]
    assert crossing["status"] == (
        "crossing" if limit <= 55 else "no_crossing_within_horizon"
    )
    assert crossing["time_s"] == (0 if limit <= 55 else None)


def test_calculated_crossing_between_points_and_at_final_endpoint(configured):
    with_limit(configured, 60)
    body = post(configured).json()
    target = 30 + 40 * ((1 + 5 * 1.5**2) / 6) ** 0.8
    expected = -10800 * math.log((target - 60) / (target - 55))
    crossing = body["baseline"]["limit_crossing"]["time_s"]
    assert crossing == pytest.approx(expected)
    assert all(crossing != p["elapsed_s"] for p in body["baseline"]["points"])
    final = body["baseline"]["final_top_oil_temperature_c"]
    client, _, asset, cfg = configured
    cfg = copy.deepcopy(cfg)
    cfg["operational_limits"] = {"max_top_oil_temp_c": final}
    cfg["parameter_provenance"]["operational_limits.max_top_oil_temp_c"] = "assumed"
    version = client.post(f"/api/v1/assets/{asset}/configurations", json=cfg).json()[
        "version"
    ]
    worker.submit(configured, 60, version=version)
    assert run_once(configured[1])
    end = post(configured).json()["baseline"]["limit_crossing"]
    assert end["status"] == "crossing" and end["time_s"] == pytest.approx(3600)


def test_snapshot_stays_fixed_across_cache_config_and_late_results(configured):
    bootstrap(configured)
    first = post(configured).json()
    payload = request(state_ref=first["state"]["state_ref"])
    worker.submit(configured, 60)
    assert run_once(configured[1])
    assert post(configured, payload).json() == first
    latest = post(configured).json()
    assert latest["state"]["state_ref"] != first["state"]["state_ref"]
    worker.submit(configured, 30)
    assert run_once(configured[1])
    assert post(configured).json() == latest
    client, _, asset, cfg = configured
    cfg = copy.deepcopy(cfg)
    cfg["thermal_parameters"]["rated_top_oil_rise_c"] = 50
    client.post(f"/api/v1/assets/{asset}/configurations", json=cfg)
    assert (
        post(configured).json() == latest
    )  # Latest registered configuration is not auto-selected.
    worker.submit(configured, 120, version=2)
    assert run_once(configured[1])
    assert post(configured).json()["configuration"]["version"] == 2
    assert post(configured, payload).json() == first
    wrong = post(
        configured, request(state_ref=first["state"]["state_ref"], run_id="other-run")
    )
    assert (
        wrong.status_code == 409
        and wrong.json()["detail"]["code"] == "incompatible_state_identity"
    )
    assert (
        client.post(
            "/api/v1/assets",
            json={
                "asset_id": "other",
                "name": "Other",
                "location": "Lab",
                "timezone": "UTC",
            },
        ).status_code
        == 201
    )
    assert post(configured, payload, asset_id="other").status_code == 409


def test_latest_invalid_does_not_fall_back_to_prior_snapshot(configured):
    bootstrap(configured)
    old = post(configured).json()
    worker.submit(configured, 600)
    assert run_once(configured[1])
    response = post(configured)
    assert (
        response.status_code == 409
        and response.json()["detail"]["code"] == "ineligible_state"
    )
    assert post(configured, request(state_ref=old["state"]["state_ref"])).json() == old


def test_missing_parameters_rejected(registry, asset, configuration):
    client, factory = registry
    assert (
        client.post(
            f"/api/v1/assets/{asset['asset_id']}/configurations", json=configuration
        ).status_code
        == 201
    )
    setup = client, factory, asset["asset_id"], configuration
    bootstrap(setup)
    response = post(setup)
    assert (
        response.status_code == 409
        and response.json()["detail"]["code"] == "missing_model_parameters"
    )
    assert (
        "thermal_parameters.oil_time_constant_min"
        in response.json()["detail"]["reasons"]
    )


def test_capture_requires_exact_cache_result_identity(configured):
    bootstrap(configured)
    with configured[1].begin() as db:
        db.execute(
            text(
                "UPDATE analytics_states SET state=jsonb_set(state::jsonb,'{thermal,oil_temp_c}','56')::json"
            )
        )
    response = post(configured)
    assert (
        response.status_code == 409
        and response.json()["detail"]["code"] == "incompatible_state_identity"
    )
    with configured[1]() as db:
        assert db.scalar(select(func.count()).select_from(WhatIfSnapshot)) == 0


def test_concurrent_capture_is_one_immutable_reference(configured):
    bootstrap(configured)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: post(configured), range(2)))
    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    with configured[1].begin() as db:
        assert db.scalar(select(func.count()).select_from(WhatIfSnapshot)) == 1
        for query in (
            "UPDATE what_if_snapshots SET state='{}'",
            "DELETE FROM what_if_snapshots",
        ):
            with pytest.raises(IntegrityError), db.begin_nested():
                db.execute(text(query))
        cfg = Config("backend/alembic.ini")
        cfg.attributes["connection"] = db.connection()
        with pytest.raises(DBAPIError), db.begin_nested():
            command.downgrade(cfg, "d004_worker_maintenance")


def test_arithmetic_failure_rolls_back_capture(configured, monkeypatch):
    bootstrap(configured)
    from backend.app.services import what_if

    def fail(*args):
        raise ValueError("synthetic arithmetic injection; do not expose")

    monkeypatch.setattr(what_if, "forecast_from_worker_state", fail)
    before = rows(configured[1])
    response = post(configured)
    assert (
        response.status_code == 422
        and response.json()["detail"]["code"] == "computation_unavailable"
    )
    assert "injection" not in response.text and rows(configured[1]) == before
    with configured[1]() as db:
        assert db.scalar(select(func.count()).select_from(WhatIfSnapshot)) == 0


def test_snapshot_does_not_reconstruct_mutable_result_payload(configured):
    bootstrap(configured)
    first = post(configured).json()
    with configured[1].begin() as db:
        db.execute(
            text(
                "UPDATE analytics_results SET payload=jsonb_set(payload::jsonb,'{updated_state,thermal,oil_temp_c}','99')::json"
            )
        )
    assert (
        post(configured, request(state_ref=first["state"]["state_ref"])).json() == first
    )
    assert post(configured).json()["detail"]["code"] == "incompatible_state_identity"


def test_snapshot_insert_guard_rejects_contradictory_origin(configured):
    bootstrap(configured)
    post(configured)
    # Drop the copied result uniqueness in a private savepoint solely to exercise
    # the binding trigger against an otherwise existing parent result/config.
    with configured[1].begin() as db, pytest.raises(IntegrityError), db.begin_nested():
        db.execute(
            text(
                "ALTER TABLE what_if_snapshots DROP CONSTRAINT uq_what_if_snapshot_result"
            )
        )
        db.execute(
            text("""INSERT INTO what_if_snapshots
                SELECT :id,result_id,asset_id,'file_replay',run_key,configuration_version,
                model_id,model_version,parameter_version,measurement_time,state,captured_at
                FROM what_if_snapshots"""),
            {"id": uuid4()},
        )


def test_upgrade_preserves_existing_worker_data_and_matches_metadata(configured):
    bootstrap(configured)
    before = rows(configured[1])
    cfg = Config("backend/alembic.ini")
    with configured[1].kw["bind"].begin() as db:
        cfg.attributes["connection"] = db
        command.downgrade(cfg, "d004_worker_maintenance")
        command.upgrade(cfg, "head")
        command.check(cfg)
        assert (
            db.scalar(text("SELECT version_num FROM alembic_version"))
            == "d006_combined_integration"
        )
    assert rows(configured[1]) == before
    assert post(configured).status_code == 200


def test_computation_bounds_can_fail_arithmetic_without_fabricated_forecast(configured):
    client, factory, asset, cfg = configured
    cfg = copy.deepcopy(cfg)
    cfg["thermal_parameters"]["rated_top_oil_rise_c"] = 1e308
    assert (
        client.post(f"/api/v1/assets/{asset}/configurations", json=cfg).status_code
        == 201
    )
    bootstrap(configured, version=2)
    segment = {"duration_s": 86400, "thermal_load_pu": 10, "ambient_temperature_c": 80}
    response = post(configured, request(baseline=segment, reduced_load=segment))
    assert (
        response.status_code == 422
        and response.json()["detail"]["code"] == "computation_unavailable"
    )
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(WhatIfSnapshot)) == 0


def test_unsupported_model_namespace_and_bad_parameter_binding(configured):
    bootstrap(configured)
    with configured[1].begin() as db:
        original = db.scalar(text("SELECT last_identity FROM analytics_streams"))
        namespace = json.loads(original)
        namespace[1] = "stored-reading-top-oil-1.0.2"
        db.execute(
            text("UPDATE analytics_streams SET last_identity=:identity"),
            {"identity": json.dumps(namespace)},
        )
    assert post(configured).json()["detail"]["code"] == "incompatible_state_identity"
    with configured[1].begin() as db:
        db.execute(
            text("UPDATE analytics_streams SET last_identity=:identity"),
            {"identity": original},
        )
        db.execute(
            text("UPDATE analytics_results SET parameter_version='wrong-parameter'")
        )
    assert post(configured).json()["detail"]["code"] == "incompatible_state_identity"


def test_uninitialized_state_and_database_failure_have_explicit_errors(
    configured, monkeypatch
):
    from backend.app.services import what_if

    original = what_if.resolve

    def unavailable(*args):
        raise DBAPIError("test-only", {}, Exception("do not expose"))

    monkeypatch.setattr(what_if, "resolve", unavailable)
    response = post(configured)
    assert (
        response.status_code == 503
        and response.json()["detail"]["code"] == "database_unavailable"
    )
    assert "do not expose" not in response.text
    monkeypatch.setattr(what_if, "resolve", original)
    client, factory, asset, _ = configured
    packet = worker.packet(asset)
    packet["measurements"]["oil_temperature_c"] = None
    packet["measurement_quality"]["oil_temperature_c"] = "missing"
    assert client.post("/api/v1/telemetry", json=packet).status_code == 201
    assert run_once(factory)
    response = post(configured)
    assert (
        response.status_code == 409
        and response.json()["detail"]["code"] == "ineligible_state"
    )
