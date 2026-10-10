"""Real old records, explicit fenced adoption and version-specific HTTP forecasts."""

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.app.analytics import adapter
from backend.app.analytics.person_b import worker as current
from backend.app.analytics.person_b.historical_v101 import worker as old
from backend.app.models.analytics import AnalyticsResult, AnalyticsState
from backend.app.models.incidents import DetectorEpoch, Operator
from backend.app.schemas.incidents import Handover
from backend.app.services import incidents
from backend.app.services.analytics_worker import (
    StaleClaim,
    claim_next,
    process_claim,
    run_once,
)
from backend.tests import test_analytics_worker as worker_tests
from backend.tests import test_incidents as incident_tests
from backend.tests.test_analytics_worker import expire, submit
from backend.tests.test_incident_maintenance import request as task_request
from backend.tests.test_incidents import control, opened
from backend.tests.test_what_if import request as forecast_request
from backend.tests.test_what_if import rows

configured = worker_tests.configured
actors = incident_tests.actors


@contextmanager
def legacy_runtime(monkeypatch):
    """Simulate the actual pre-adoption implementation; never relabel .2 output."""
    with monkeypatch.context() as patch:
        patch.setattr(adapter, "MODEL_VERSION", old.MODEL_VERSION)
        patch.setattr(
            adapter,
            "compute",
            lambda reading, config, previous, policy: old.compute_analytics(
                reading.normalized_telemetry,
                config,
                reading.quality_flags,
                reading.id,
                previous,
                state_policy=policy,
            ),
        )
        yield


def handover_request(**changes):
    body = {
        "schema_version": "model-control-1.0.0",
        "expected_version": 0,
        "idempotency_key": str(uuid4()),
        "source": "simulator",
        "run_id": "worker-test",
        "configuration_version": 1,
        "model_version": current.MODEL_VERSION,
        "reason": "Explicit isolated model adoption",
    }
    body.update(changes)
    return body


def snapshot(client, asset, **changes):
    return client.post(
        f"/api/v1/assets/{asset}/what-if", json=forecast_request(**changes)
    )


def test_unmonitored_handover_fences_old_claim_preserves_old_forecast_and_bootstraps(
    configured, actors, monkeypatch
):
    client, factory, asset, _ = configured
    with legacy_runtime(monkeypatch):
        submit(configured)
        assert run_once(factory)
        historic = snapshot(client, asset).json()
        assert historic["model"]["model_version"] == old.MODEL_VERSION
        submit(configured, 60)
        claim = claim_next(factory)
        assert claim
    with factory() as db:
        prior = db.scalar(select(AnalyticsState))
        state_id = (
            prior.asset_id,
            prior.source,
            prior.run_key,
            prior.model_id,
            prior.model_version,
            prior.configuration_version,
            prior.parameter_version,
        )
        state_json, advances = prior.state, prior.advances
    path = f"/api/v1/assets/{asset}/model-handovers"
    body = handover_request()
    busy = client.post(path, json=body, headers=actors["admin"])
    assert busy.status_code == 409 and busy.json()["code"] == "stream_busy"
    expire(factory, claim)
    result = client.post(path, json=body, headers=actors["admin"])
    assert result.status_code == 201, result.text
    assert (
        result.json()["boundary_measurement_time"]
        == historic["state"]["measurement_time"]
    )
    assert client.post(path, json=body, headers=actors["admin"]).json() == result.json()
    conflict = client.post(
        path, json={**body, "reason": "different"}, headers=actors["admin"]
    )
    assert (
        conflict.status_code == 409
        and conflict.json()["code"] == "idempotency_conflict"
    )
    with pytest.raises(StaleClaim):
        process_claim(factory, claim)
    assert run_once(factory)
    with factory() as db:
        new_result = db.scalar(
            select(AnalyticsResult).order_by(AnalyticsResult.id.desc())
        )
        thermal = new_result.payload["thermal_assessment"]
        assert new_result.model_version == current.MODEL_VERSION
        assert thermal["predicted_top_oil_temperature_c"] is None
        assert thermal["thermal_residual_c"] is None
        assert (
            "initialized_from_measurement_prediction_not_independent"
            in thermal["reasons"]
        )
        assert db.get(AnalyticsState, state_id).state == state_json
        assert db.get(AnalyticsState, state_id).advances == advances
        epoch = db.get(DetectorEpoch, result.json()["detector_epoch"])
        assert epoch.previous_twin_state["state"] == state_json
        assert epoch.previous_twin_state["namespace"][1] == old.MODEL_VERSION
        assert epoch.context is None
        assert db.scalar(text("SELECT count(*) FROM incidents")) == 0
    before = rows(factory)
    reference = historic["state"]["state_ref"]
    assert snapshot(client, asset, state_ref=reference).json() == historic
    assert rows(factory) == before
    latest = snapshot(client, asset).json()
    assert latest["model"]["model_version"] == current.MODEL_VERSION
    assert latest["state"]["state_ref"] != reference
    submit(configured, 120)
    assert run_once(factory)
    with factory() as db:
        thermal = db.scalar(
            select(AnalyticsResult).order_by(AnalyticsResult.id.desc())
        ).payload["thermal_assessment"]
        assert thermal["predicted_top_oil_temperature_c"] is not None
        assert thermal["thermal_residual_c"] == pytest.approx(
            55 - thermal["predicted_top_oil_temperature_c"]
        )
    # Equal/late boundary evidence cannot initialize or advance the new namespace.
    submit(configured, 0)
    assert run_once(factory)
    assert snapshot(client, asset, state_ref=reference).json() == historic


def test_existing_stream_blocks_without_mutating_jobs_and_other_stream_progresses(
    configured, actors, monkeypatch
):
    client, factory, asset, _ = configured
    with legacy_runtime(monkeypatch):
        submit(configured)
        assert run_once(factory)
    submit(configured, 60)
    before = rows(factory)
    assert not run_once(factory)
    assert rows(factory) == before
    submit(configured, 120, run="independent-stream")
    assert run_once(factory)
    with factory() as db:
        assert (
            db.scalar(
                text(
                    "SELECT attempts FROM telemetry_processing_jobs WHERE reading_id=(SELECT id FROM telemetry_readings WHERE run_key='worker-test' AND measurement_time>'2026-01-01')"
                )
            )
            == 0
        )
    path = f"/api/v1/assets/{asset}/model-handovers"
    body = handover_request()
    for role, status in [("reader", 403), ("operator", 403), ("expired", 401)]:
        assert client.post(path, json=body, headers=actors[role]).status_code == status
    assert (
        client.post(path, json=body, headers={"X-Demo-Actor": "admin"}).status_code
        == 401
    )
    assert (
        client.post(
            path,
            json={**body, "model_version": old.MODEL_VERSION},
            headers=actors["admin"],
        ).status_code
        == 422
    )
    assert (
        client.post(
            path, json={**body, "policy": {}}, headers=actors["admin"]
        ).status_code
        == 422
    )
    assert (
        client.post(
            path, json={**body, "expected_version": 1}, headers=actors["admin"]
        ).status_code
        == 409
    )
    assert client.post(path, json=body, headers=actors["admin"]).status_code == 201
    assert run_once(factory)


def test_monitored_handover_preserves_ack_tasks_evidence_and_interrupts_active_identity(
    configured, actors, monkeypatch
):
    client, factory, asset, _ = configured
    # Historical migration fixture executes .1's actual code/policy, including .1 records.
    with legacy_runtime(monkeypatch):
        from backend.tests.test_incidents import policy

        payload = Handover.model_validate(
            {
                **handover_request(run_id="incident-test"),
                "schema_version": "incident-control-1.0.0",
                "detector_version": "sustained-threshold-1.0.1",
                "policy": policy(),
                "model_version": current.MODEL_VERSION,
            }
        ).model_copy(update={"model_version": old.MODEL_VERSION})
        with factory() as db:
            token = actors["admin"]["Authorization"].split()[1]
            actor = db.scalar(
                select(Operator).where(
                    Operator.token_hash == hashlib.sha256(token.encode()).hexdigest()
                )
            )
            from backend.app.services.analytics_worker import db_time

            origin, _ = incidents.handover(db, asset, payload, actor, db_time(db))
        setup = (client, factory, asset, actors, origin)
        incident = opened(setup)
        historic = snapshot(client, asset, run_id="incident-test").json()
    retry = client.post(
        f"/api/v1/assets/{asset}/detector-handovers",
        json=payload.model_dump(mode="json"),
        headers=actors["admin"],
    )
    assert retry.status_code == 200 and retry.json() == origin
    unsupported = client.post(
        f"/api/v1/assets/{asset}/detector-handovers",
        json={
            **payload.model_dump(mode="json"),
            "idempotency_key": str(uuid4()),
            "expected_version": 1,
        },
        headers=actors["admin"],
    )
    assert (
        unsupported.status_code == 409
        and unsupported.json()["code"] == "unsupported_model_version"
    )
    iid = incident["incident_id"]
    ack = client.post(
        f"/api/v1/incidents/{iid}/acknowledgements",
        json={
            "schema_version": "incident-acknowledgement-1.0.0",
            "expected_version": 1,
            "idempotency_key": str(uuid4()),
        },
        headers=actors["operator"],
    )
    assert ack.status_code == 201
    task = client.post(
        "/api/v1/maintenance/tasks",
        json=task_request(incident),
        headers=actors["operator"],
    )
    assert task.status_code == 201
    evidence = client.get(
        f"/api/v1/incidents/{iid}/evidence", headers=actors["reader"]
    ).json()
    result, _ = control(client, asset, actors["admin"], version=1)
    assert result.status_code == 201, result.text
    now = client.get(f"/api/v1/incidents/{iid}", headers=actors["reader"]).json()
    assert (
        now["condition_status"] == "active"
        and now["monitoring_status"] == "interrupted"
    )
    assert now["acknowledgement"] == ack.json()["acknowledgement"]
    assert (
        client.get(f"/api/v1/incidents/{iid}/evidence", headers=actors["reader"]).json()
        == evidence
    )
    assert (
        client.get(
            "/api/v1/maintenance/tasks/" + task.json()["id"], headers=actors["reader"]
        ).json()
        == task.json()
    )
    assert (
        snapshot(
            client,
            asset,
            run_id="incident-test",
            state_ref=historic["state"]["state_ref"],
        ).json()
        == historic
    )
    from backend.tests.test_incidents import submit as incident_submit

    incident_submit(setup, 240)
    incident_submit(setup, 420)
    items = client.get(
        "/api/v1/incidents",
        params={"asset_id": asset, "source": "simulator", "run_id": "incident-test"},
        headers=actors["reader"],
    ).json()["items"]
    assert len(items) == 2 and {x["incident_id"] for x in items} != {iid}
    assert len({x["detector_epoch"] for x in items}) == 2
    with factory() as db:
        assert db.scalar(text("SELECT count(*) FROM analytics_states")) == 2
        assert (
            db.scalar(
                text(
                    "SELECT count(*) FROM incident_events e LEFT JOIN incident_deliveries d USING(event_id) WHERE d.event_id IS NULL"
                )
            )
            == 0
        )
        versions = (
            db.execute(text("SELECT DISTINCT model_version FROM analytics_results"))
            .scalars()
            .all()
        )
        assert set(versions) == {old.MODEL_VERSION, current.MODEL_VERSION}


@pytest.mark.parametrize("rating", [1e308, 5e-324])
def test_adopted_extreme_arithmetic_preserves_finite_metrics(rating):
    cases = json.loads(
        Path("backend/app/analytics/person_b/worker-test-examples.json").read_text()
    )["examples"]
    request = cases[0]["input"]
    config = request["asset_config"]
    reading = request["stored_reading"]
    if rating == 1e308:
        config["rated_current_a"] = rating
        for phase in "ryb":
            reading["normalized_telemetry"]["measurements"][f"current_{phase}_a"] = (
                rating
            )
    else:
        config["rated_kva"] = rating
    output = current.process_stored_reading(reading, config)
    metrics = output["electrical_metrics"]
    assert metrics["thermal_load_pu"] == pytest.approx(1)
    assert metrics["current_magnitude_imbalance_pct"] == 0
    assert metrics["max_phase_loading_pct"] == pytest.approx(100)
    assert metrics["capacity_loading_pct"] is None
    assert output["execution_status"]["availability"][
        "electrical_metrics.capacity_loading_pct"
    ]["reasons"] == ["electrical_arithmetic_unavailable"]
    json.dumps(output, allow_nan=False)


def test_historical_arithmetic_error_never_substitutes_current_computation(
    configured, monkeypatch
):
    client, factory, asset, _ = configured
    with legacy_runtime(monkeypatch):
        submit(configured)
        assert run_once(factory)
        historic = snapshot(client, asset).json()
    from backend.app.services import what_if

    def fail(*args):
        raise OverflowError("Synthetic historical arithmetic failure")

    monkeypatch.setattr(
        what_if.historical_scenarios, "forecast_from_worker_state", fail
    )
    before = rows(factory)
    error = snapshot(client, asset, state_ref=historic["state"]["state_ref"])
    assert (
        error.status_code == 422
        and error.json()["detail"]["code"] == "computation_unavailable"
    )
    assert rows(factory) == before
    with factory() as db:
        assert db.scalar(text("SELECT count(*) FROM what_if_snapshots")) == 1


def test_unknown_result_schema_cannot_capture_a_forecast(configured):
    client, factory, asset, _ = configured
    submit(configured)
    assert run_once(factory)
    with factory.begin() as db:
        db.execute(
            text(
                "UPDATE analytics_results SET schema_version='unsupported-result-schema'"
            )
        )
    before = rows(factory)
    response = snapshot(client, asset)
    assert (
        response.status_code == 409
        and response.json()["detail"]["code"] == "incompatible_state_identity"
    )
    assert rows(factory) == before
    with factory() as db:
        assert db.scalar(text("SELECT count(*) FROM what_if_snapshots")) == 0
