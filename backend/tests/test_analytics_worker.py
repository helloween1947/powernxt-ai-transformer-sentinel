"""PostgreSQL worker regressions; synchronization uses barriers/events, never sleeps."""

import json
import math
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from backend.app.analytics import adapter
from backend.app.analytics.person_b import compute_analytics
from backend.app.analytics.person_b import worker as model
from backend.app.models.analytics import (
    AnalyticsResult,
    AnalyticsState,
    AnalyticsStream,
)
from backend.app.models.telemetry import ProcessingJob, TelemetryReading
from backend.app.services.analytics_worker import (
    StaleClaim,
    claim_next,
    process_claim,
    record_failure,
    run_once,
)


@pytest.fixture
def configured(registry, asset, configuration):
    client, factory = registry
    thermal = {
        "rated_top_oil_rise_c": 40,
        "oil_time_constant_min": 180,
        "loss_ratio": 5,
        "oil_exponent": 0.8,
    }
    cfg = {
        **configuration,
        "thermal_parameters": thermal,
        "parameter_provenance": {
            **configuration["parameter_provenance"],
            **{"thermal_parameters." + k: "assumed" for k in thermal},
        },
    }
    response = client.post(
        f"/api/v1/assets/{asset['asset_id']}/configurations", json=cfg
    )
    assert response.status_code == 201
    return client, factory, asset["asset_id"], cfg


def packet(asset_id, seconds=0, run="worker-test", version=1):
    p = json.loads(Path("data/sample/telemetry-sample.json").read_text())
    p.update(
        asset_id=asset_id,
        message_id=str(uuid4()),
        configuration_version=version,
        run_id=run,
        timestamp=(
            datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)
        ).isoformat(),
    )
    p["measurements"].update(
        current_r_a=52.49,
        current_y_a=52.49,
        current_b_a=52.49,
        voltage_r_v=11000,
        voltage_y_v=11000,
        voltage_b_v=11000,
        ambient_temperature_c=30,
        oil_temperature_c=55,
    )
    return p


def submit(setup, seconds=0, **kw):
    client, _, asset_id, _ = setup
    p = packet(asset_id, seconds, **kw)
    response = client.post("/api/v1/telemetry", json=p)
    assert response.status_code == 201, response.text
    return p, response.json()


def totals(factory):
    with factory() as db:
        return {
            m.__tablename__: db.scalar(select(func.count()).select_from(m))
            for m in [TelemetryReading, ProcessingJob, AnalyticsResult, AnalyticsState]
        }


def expire(factory, claim):
    with factory.begin() as db:
        db.execute(
            text(
                "UPDATE telemetry_processing_jobs SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:id"
            ),
            {"id": claim.job_id},
        )
        db.execute(
            text(
                "UPDATE analytics_streams SET lease_until=clock_timestamp()-interval '1 second' WHERE active_job_id=:id"
            ),
            {"id": claim.job_id},
        )


def test_flow_api_idempotency_and_elapsed(configured):
    client, factory, asset_id, _ = configured
    p, first = submit(configured)
    _, second = submit(configured, 60)
    pending = client.get(f"/api/v1/telemetry/{first['id']}/analytics").json()
    assert pending["status"] == "pending" and pending["result"] is None
    assert run_once(factory) and run_once(factory) and not run_once(factory)
    result = client.get(f"/api/v1/telemetry/{second['id']}/analytics").json()
    assert result["status"] == "completed"
    thermal = result["result"]["payload"]["thermal_assessment"]
    assert thermal["elapsed_s"] == 60
    assert thermal["predicted_top_oil_temperature_c"] == pytest.approx(
        70 - 15 * math.exp(-60 / 10800)
    )
    before = totals(factory)
    assert client.post("/api/v1/telemetry", json=p).status_code == 200
    assert totals(factory) == before and not run_once(factory)
    with factory() as db:
        assert db.scalar(select(AnalyticsStream)).advances == 2
        assert db.scalar(select(AnalyticsState)).advances == 2
    latest = client.get(
        f"/api/v1/assets/{asset_id}/analytics/latest",
        params={"source": "simulator", "run_id": "worker-test"},
    ).json()
    assert (
        latest["latest_completed_reading_id"]
        == latest["latest_telemetry_reading_id"]
        == second["id"]
    )
    assert (
        client.get(
            f"/api/v1/assets/{asset_id}/telemetry/latest",
            params={"source": "simulator", "run_id": "worker-test"},
        ).json()["analytics_status"]
        == "completed"
    )


def test_competing_workers_and_sequential_stream(configured):
    _, factory, _, _ = configured
    submit(configured)
    submit(configured, 60)
    barrier = threading.Barrier(2)

    def compete():
        barrier.wait()
        return claim_next(factory)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(compete) for _ in range(2)]
        claims = [f.result(timeout=10) for f in futures]
    assert sum(c is not None for c in claims) == 1
    process_claim(factory, next(c for c in claims if c))
    assert run_once(factory)
    with factory() as db:
        assert db.scalar(select(AnalyticsStream)).advances == 2


def test_streams_can_compute_concurrently(configured):
    _, factory, _, _ = configured
    submit(configured, run="one")
    submit(configured, run="two")
    claims = [claim_next(factory), claim_next(factory)]
    assert all(claims)
    barrier = threading.Barrier(2)

    def compute(*args):
        barrier.wait(timeout=10)
        return adapter.compute(*args)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(process_claim, factory, c, compute=compute) for c in claims
        ]
        for f in futures:
            f.result(timeout=10)
    with factory() as db:
        assert len(db.scalars(select(AnalyticsState)).all()) == 2
        assert all(h.advances == 1 for h in db.scalars(select(AnalyticsStream)))


def test_expired_lease_recovery_stale_owner_and_no_double_advance(configured):
    _, factory, _, _ = configured
    submit(configured)
    old = claim_next(factory)
    expire(factory, old)
    current = claim_next(factory)
    assert current.token != old.token
    with pytest.raises(StaleClaim):
        process_claim(factory, old)
    with pytest.raises(StaleClaim):
        record_failure(factory, old, RuntimeError())
    process_claim(factory, current)
    with pytest.raises(StaleClaim):
        process_claim(factory, current)
    with factory() as db:
        assert db.get(ProcessingJob, current.job_id).attempts == 2
        assert db.scalar(select(AnalyticsStream)).advances == 1
        assert db.scalar(select(func.count()).select_from(AnalyticsResult)) == 1


def test_worker_expires_during_computation(configured):
    _, factory, _, _ = configured
    submit(configured)
    claim = claim_next(factory)

    def compute(*args):
        value = adapter.compute(*args)
        expire(factory, claim)
        return value

    with pytest.raises(StaleClaim):
        process_claim(factory, claim, compute=compute)
    assert totals(factory)["analytics_results"] == 0
    assert run_once(factory)


def test_atomic_rollback_and_retry(configured):
    _, factory, _, _ = configured
    submit(configured)
    claim = claim_next(factory)

    def crash(db):
        raise RuntimeError("injected after all writes")

    with pytest.raises(RuntimeError):
        process_claim(factory, claim, before_commit=crash)
    with factory() as db:
        assert db.scalar(select(AnalyticsStream)).advances == 0
        assert db.get(ProcessingJob, claim.job_id).status == "processing"
    assert (
        totals(factory)["analytics_results"] == totals(factory)["analytics_states"] == 0
    )
    process_claim(factory, claim)
    with factory() as db:
        assert db.scalar(select(AnalyticsStream)).advances == 1


def test_bounded_retries_and_sanitized_failure(configured):
    client, factory, _, _ = configured
    _, reading = submit(configured)
    for n in range(3):
        c = claim_next(factory)
        record_failure(
            factory, c, ValueError("SECRET should not persist"), retry_seconds=0
        )
    assert claim_next(factory) is None
    result = client.get(f"/api/v1/telemetry/{reading['id']}/analytics").json()
    assert result["status"] == "failed" and result["attempts"] == 3
    assert (
        result["error_code"] == "invalid_computation_input" and result["result"] is None
    )
    assert totals(factory)["analytics_results"] == 0


def test_crash_attempts_exhaustion_does_not_block_later_job(configured):
    _, factory, _, _ = configured
    submit(configured)
    submit(configured, 60)
    for _ in range(3):
        c = claim_next(factory)
        expire(factory, c)
    assert claim_next(factory) is None  # marks exhausted first job terminal
    assert run_once(factory)
    with factory() as db:
        assert [
            j.status
            for j in db.scalars(select(ProcessingJob).order_by(ProcessingJob.id))
        ] == ["failed", "completed"]


def test_retry_backoff_blocks_only_its_stream(configured):
    _, factory, _, _ = configured
    submit(configured)
    submit(configured, 60)
    submit(configured, run="independent")
    first = claim_next(factory)
    record_failure(factory, first, RuntimeError(), retry_seconds=100)
    assert run_once(factory) and claim_next(factory) is None


def test_late_equal_time_and_latest_lag(configured):
    client, factory, asset_id, _ = configured
    _, first = submit(configured, 60)
    assert run_once(factory)
    _, late = submit(configured, 0)
    _, equal = submit(configured, 60)
    _, future = submit(configured, 120)
    assert run_once(factory) and run_once(factory)
    for reading in [late, equal]:
        result = client.get(f"/api/v1/telemetry/{reading['id']}/analytics").json()
        assert (
            result["status"] == "unavailable"
            and not result["result"]["payload"]["execution_status"]["state_advanced"]
        )
    latest = client.get(
        f"/api/v1/assets/{asset_id}/analytics/latest",
        params={"source": "simulator", "run_id": "worker-test"},
    ).json()
    assert (
        latest["latest_telemetry_reading_id"] == future["id"]
        and latest["latest_completed_reading_id"] == first["id"]
    )
    assert run_once(factory)
    with factory() as db:
        assert db.scalar(select(AnalyticsStream)).advances == 2


def test_processing_watermark_overrides_new_namespace_eligibility(configured):
    client, factory, asset_id, cfg = configured
    submit(configured, 120)
    assert run_once(factory)
    assert (
        client.post(f"/api/v1/assets/{asset_id}/configurations", json=cfg).status_code
        == 201
    )
    _, old = submit(configured, 60, version=2)
    # Simulate a previously eligible job/backlog admitted before the watermark.
    with factory.begin() as db:
        db.execute(
            text(
                "UPDATE telemetry_processing_jobs SET state_policy='forward_only' WHERE reading_id=:id"
            ),
            {"id": old["id"]},
        )
    assert run_once(factory)
    with factory() as db:
        assert db.scalar(select(AnalyticsStream)).advances == 1
        assert db.scalar(select(func.count()).select_from(AnalyticsState)) == 1


def test_configuration_transitions_cold_start_and_preserve_watermark(configured):
    client, factory, asset_id, cfg = configured
    submit(configured)
    assert run_once(factory)
    assert (
        client.post(
            f"/api/v1/assets/{asset_id}/configurations",
            json={**cfg, "rated_current_a": 60},
        ).status_code
        == 201
    )
    _, second = submit(configured, 60, version=2)
    assert run_once(factory)
    _, back = submit(configured, 120, version=1)
    assert run_once(factory)
    for item in [second, back]:
        result = client.get(f"/api/v1/telemetry/{item['id']}/analytics").json()[
            "result"
        ]["payload"]
        assert result["thermal_assessment"]["initial_condition"] is not None
        assert result["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    with factory() as db:
        assert db.scalar(select(AnalyticsStream)).advances == 3
        assert db.scalar(select(func.count()).select_from(AnalyticsState)) == 2


def test_model_transition_is_explicit_namespace_reset(configured, monkeypatch):
    client, factory, _, _ = configured
    submit(configured)
    assert run_once(factory)
    monkeypatch.setattr(adapter, "MODEL_VERSION", "test-next-model")
    monkeypatch.setattr(model, "MODEL_VERSION", "test-next-model")
    _, next_reading = submit(configured, 60)
    assert run_once(factory)
    result = client.get(f"/api/v1/telemetry/{next_reading['id']}/analytics").json()[
        "result"
    ]
    assert result["model_version"] == "test-next-model"
    assert result["payload"]["thermal_assessment"]["initial_condition"] is not None
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(AnalyticsState)) == 2
        assert db.scalar(select(AnalyticsStream)).advances == 2


@pytest.mark.parametrize(
    "mode", ["missing", "bad", "implausible", "zero", "no_thermal"]
)
def test_measurement_and_configuration_availability(configured, mode):
    client, factory, asset_id, cfg = configured
    p = packet(asset_id)
    if mode == "no_thermal":
        cfg = {
            **cfg,
            "thermal_parameters": {},
            "parameter_provenance": {
                k: v
                for k, v in cfg["parameter_provenance"].items()
                if not k.startswith("thermal_parameters.")
            },
        }
        assert (
            client.post(
                f"/api/v1/assets/{asset_id}/configurations", json=cfg
            ).status_code
            == 201
        )
        p["configuration_version"] = 2
    elif mode == "missing":
        p["measurements"]["current_r_a"] = None
        p["measurement_quality"] = {}
    elif mode == "bad":
        p["measurement_quality"]["current_r_a"] = "bad"
    elif mode == "implausible":
        p["measurements"]["current_r_a"] = 10000
    else:
        for phase in "ryb":
            p["measurements"][f"current_{phase}_a"] = 0
    r = client.post("/api/v1/telemetry", json=p)
    assert r.status_code == 201
    assert run_once(factory)
    result = client.get(f"/api/v1/telemetry/{r.json()['id']}/analytics").json()
    metrics = result["result"]["payload"]["electrical_metrics"]
    if mode in ["missing", "bad", "implausible"]:
        assert result["status"] == "unavailable" and metrics["thermal_load_pu"] is None
    elif mode == "zero":
        assert metrics["thermal_load_pu"] == metrics["apparent_power_kva"] == 0
    else:
        assert (
            result["result"]["payload"]["execution_status"]["outcome"]
            == "unsupported_configuration"
        )


@pytest.mark.parametrize("dt", [1, 59, 60, 61, 137, 299, 300, 301])
def test_measurement_elapsed_cadence_and_gap_latch(configured, dt):
    client, factory, _, _ = configured
    submit(configured)
    assert run_once(factory)
    _, r = submit(configured, dt)
    assert run_once(factory)
    output = client.get(f"/api/v1/telemetry/{r['id']}/analytics").json()["result"][
        "payload"
    ]
    assert output["thermal_assessment"]["elapsed_s"] == dt
    if dt <= 300:
        assert output["thermal_assessment"][
            "predicted_top_oil_temperature_c"
        ] == pytest.approx(70 - 15 * math.exp(-dt / 10800))
    else:
        assert (
            "measurement_gap_exceeds_300_s" in output["thermal_assessment"]["reasons"]
        )
        _, next_r = submit(configured, dt + 60)
        assert run_once(factory)
        output = client.get(f"/api/v1/telemetry/{next_r['id']}/analytics").json()[
            "result"
        ]["payload"]
        assert output["thermal_assessment"]["predicted_top_oil_temperature_c"] is None


def test_computation_error_retries_without_advancing(configured):
    _, factory, _, _ = configured
    submit(configured)
    c = claim_next(factory)

    def faulty(*args):
        output = adapter.compute(*args)
        output["execution_status"]["outcome"] = "computation_error"
        return output

    from backend.app.services.analytics_worker import ComputationError

    with pytest.raises(ComputationError):
        process_claim(factory, c, compute=faulty)
    record_failure(factory, c, ComputationError(), retry_seconds=0)
    assert (
        totals(factory)["analytics_results"] == totals(factory)["analytics_states"] == 0
    )
    assert run_once(factory)


def test_result_api_explicit_stream_filters(configured):
    client, factory, asset_id, _ = configured
    for run in ["one", "two"]:
        submit(configured, run=run)
    assert run_once(factory) and run_once(factory)
    path = f"/api/v1/assets/{asset_id}/analytics/latest"
    assert client.get(path).status_code == 422
    assert client.get(path, params={"source": "simulator"}).status_code == 422
    assert (
        client.get(path, params={"source": "device", "run_id": "one"}).status_code
        == 422
    )
    device = client.get(path, params={"source": "device"}).json()
    assert device["result"] is None and device["latest_telemetry_reading_id"] is None
    one = client.get(path, params={"source": "simulator", "run_id": "one"}).json()
    two = client.get(path, params={"source": "simulator", "run_id": "two"}).json()
    assert one["result"]["reading_id"] != two["result"]["reading_id"]
    assert client.get("/api/v1/telemetry/999999/analytics").status_code == 404
    assert (
        client.get(
            "/api/v1/assets/unknown/analytics/latest", params={"source": "device"}
        ).status_code
        == 404
    )


def test_person_b_executed_examples_match_extracted_adapter():
    examples = json.loads(
        Path("backend/app/analytics/person_b/worker-test-examples.json").read_text()
    )["examples"]
    for case in examples:
        request = case["input"]
        stored = request["stored_reading"]
        result = compute_analytics(
            stored["normalized_telemetry"],
            request["asset_config"],
            stored["quality_flags"],
            stored["id"],
            request["previous_state"],
            state_policy=stored["processing_job"]["state_policy"],
        )
        assert result == case["output"]
        json.dumps(result, allow_nan=False)


def test_worker_migration_preserves_populated_admission_and_refuses_history_loss(
    configured,
):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy.exc import DBAPIError

    _, factory, _, _ = configured
    submit(configured)
    with factory.kw["bind"].begin() as connection:
        cfg = Config("backend/alembic.ini")
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, "ce21c3b8140a")
        tables = [
            "assets",
            "asset_configurations",
            "telemetry_readings",
            "telemetry_processing_jobs",
        ]
        columns = {
            t: [
                c["name"]
                for c in __import__("sqlalchemy").inspect(connection).get_columns(t)
            ]
            for t in tables
        }

        def snapshot():
            return {
                t: connection.execute(
                    text(
                        "SELECT "
                        + ",".join(columns[t])
                        + " FROM "
                        + t
                        + " ORDER BY "
                        + columns[t][0]
                    )
                ).all()
                for t in tables
            }

        before = snapshot()
        command.upgrade(cfg, "head")
        assert snapshot() == before
        job = connection.execute(
            text(
                "SELECT status,attempts,claim_token,lease_until,last_error FROM telemetry_processing_jobs"
            )
        ).one()
        assert tuple(job) == ("pending", 0, None, None, None)
        command.check(cfg)
    assert run_once(factory)
    with factory.kw["bind"].connect() as connection:
        cfg = Config("backend/alembic.ini")
        cfg.attributes["connection"] = connection
        with pytest.raises(DBAPIError, match="Worker history exists"):
            command.downgrade(cfg, "ce21c3b8140a")
        connection.rollback()
    assert totals(factory)["analytics_results"] == 1


def test_commit_expiry_rolls_back_every_write(configured, monkeypatch):
    from backend.app.services import analytics_worker as service

    _, factory, _, _ = configured
    submit(configured)
    claim = claim_next(factory)
    actual = service.db_time

    def expire_clock(db):
        monkeypatch.setattr(
            service, "db_time", lambda session: actual(session) + timedelta(seconds=120)
        )

    with pytest.raises(StaleClaim):
        process_claim(factory, claim, before_commit=expire_clock)
    assert (
        totals(factory)["analytics_results"] == totals(factory)["analytics_states"] == 0
    )
    with factory() as db:
        assert db.scalar(select(AnalyticsStream)).advances == 0
        assert db.get(ProcessingJob, claim.job_id).status == "processing"


def test_missing_oil_does_not_assimilate_returning_observation(configured):
    client, factory, asset_id, _ = configured
    submit(configured)
    assert run_once(factory)
    p = packet(asset_id, 60)
    p["measurements"]["oil_temperature_c"] = None
    p["measurement_quality"] = {}
    response = client.post("/api/v1/telemetry", json=p)
    assert response.status_code == 201
    assert run_once(factory)
    result = client.get(f"/api/v1/telemetry/{response.json()['id']}/analytics").json()[
        "result"
    ]["payload"]
    assert result["thermal_assessment"]["predicted_top_oil_temperature_c"] is not None
    assert result["thermal_assessment"]["thermal_residual_c"] is None
    p = packet(asset_id, 120)
    p["measurements"]["oil_temperature_c"] = 100
    response = client.post("/api/v1/telemetry", json=p)
    assert response.status_code == 201
    assert run_once(factory)
    result = client.get(f"/api/v1/telemetry/{response.json()['id']}/analytics").json()[
        "result"
    ]["payload"]
    predicted = 70 - 15 * math.exp(-120 / 10800)
    assert result["thermal_assessment"][
        "predicted_top_oil_temperature_c"
    ] == pytest.approx(predicted)
    assert result["thermal_assessment"]["thermal_residual_c"] == pytest.approx(
        100 - predicted
    )
    assert result["updated_state"]["thermal"]["oil_temp_c"] == pytest.approx(predicted)


def test_missing_held_inputs_invalidates_following_interval(configured):
    client, factory, asset_id, _ = configured
    submit(configured)
    assert run_once(factory)
    p = packet(asset_id, 60)
    p["measurements"]["ambient_temperature_c"] = None
    p["measurement_quality"] = {}
    assert client.post("/api/v1/telemetry", json=p).status_code == 201
    assert run_once(factory)
    _, next_r = submit(configured, 120)
    assert run_once(factory)
    result = client.get(f"/api/v1/telemetry/{next_r['id']}/analytics").json()["result"][
        "payload"
    ]
    assert result["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    assert (
        "preceding_interval_inputs_unavailable"
        in result["thermal_assessment"]["reasons"]
    )


def test_database_result_identity_is_unique(configured):
    from sqlalchemy.exc import IntegrityError

    _, factory, _, _ = configured
    submit(configured)
    assert run_once(factory)
    with factory() as db:
        original = db.scalar(select(AnalyticsResult))
        duplicate = AnalyticsResult(
            **{
                c: getattr(original, c)
                for c in [
                    "reading_id",
                    "model_id",
                    "model_version",
                    "parameter_version",
                    "schema_version",
                    "status",
                    "payload",
                ]
            }
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    assert totals(factory)["analytics_results"] == 1


def test_ground_truth_and_original_payload_never_enter_model(configured, monkeypatch):
    _, factory, _, _ = configured
    submit(configured)
    with factory.begin() as db:
        reading = db.scalar(select(TelemetryReading))
        reading.original_payload = {
            **reading.original_payload,
            "ground_truth": "DO_NOT_USE",
        }
    called = []
    actual = adapter.compute_analytics

    def observe(normalized, config, quality, reading_id, previous_state, **kw):
        assert "ground_truth" not in json.dumps(normalized)
        assert "ground_truth" not in json.dumps(config)
        called.append(reading_id)
        return actual(normalized, config, quality, reading_id, previous_state, **kw)

    monkeypatch.setattr(adapter, "compute_analytics", observe)
    assert run_once(factory) and len(called) == 1


def test_graceful_shutdown_finishes_current_claim(monkeypatch):
    import signal
    import sys

    from backend.app.workers import __main__ as cli

    handlers = {}
    calls = []
    monkeypatch.setattr(sys, "argv", ["worker"])
    monkeypatch.setattr(
        cli.signal, "signal", lambda sig, handler: handlers.update({sig: handler})
    )

    def finish_current(*args, **kwargs):
        calls.append("committed")
        handlers[signal.SIGTERM](signal.SIGTERM, None)
        return True

    monkeypatch.setattr(cli, "run_once", finish_current)
    cli.main()
    assert calls == ["committed"]
