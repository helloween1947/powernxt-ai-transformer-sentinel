"""Real PostgreSQL delivery isolation, stored bindings and populated A001 upgrade."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text

from backend.app.analytics import adapter
from backend.app.analytics.person_b.incident_orchestration import IncidentPlanningError
from backend.app.models.analytics import AnalyticsResult, AnalyticsState
from backend.app.models.incidents import Incident, IncidentDelivery, IncidentEvent
from backend.app.services import incident_outbox, incidents
from backend.app.services.analytics_worker import (
    ComputationError,
    claim_next,
    process_claim,
)
from backend.tests import test_incidents as incident_fixtures

actors = incident_fixtures.actors
configured = incident_fixtures.configured
monitored = incident_fixtures.monitored
opened = incident_fixtures.opened
submit = incident_fixtures.submit


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_worker_rollback_has_no_deliverable_event(monitored):
    _, factory, *_ = monitored
    submit(monitored, 0)
    submit(monitored, 180, process=False)
    claim = claim_next(factory)

    def fail(db):
        assert count(db, IncidentDelivery) == count(db, IncidentEvent) == 1
        # Independent transaction cannot see event/result/checkpoint before commit.
        assert incident_outbox.claim_next(factory) is None
        with factory() as other:
            assert count(other, Incident) == 0
            assert count(other, AnalyticsResult) == 1
        raise RuntimeError("labelled transactional fault")

    with pytest.raises(RuntimeError):
        process_claim(factory, claim, before_commit=fail)
    with factory() as db:
        assert count(db, IncidentDelivery) == count(db, IncidentEvent) == 0
        assert db.scalar(select(AnalyticsState)).advances == 1
    process_claim(factory, claim)
    with factory() as db:
        assert count(db, IncidentDelivery) == count(db, IncidentEvent) == 1


def test_delivery_concurrent_claims_order_retry_and_fence(monitored):
    _, factory, *_ = monitored
    opened(monitored)
    submit(monitored, 240, load=0.5)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: incident_outbox.claim_next(factory), range(2)))
    claims = [claim for claim in claims if claim is not None]
    assert len(claims) == 1  # Version 2 remains blocked behind version 1.
    claim = claims[0]
    seen = []

    def broken(envelope):
        seen.append(envelope)
        with factory() as db:
            assert count(db, IncidentEvent) == 2
            assert db.get(IncidentDelivery, claim.event_id).delivered_at is None
        raise RuntimeError("labelled transport failure")

    with pytest.raises(RuntimeError):
        incident_outbox.publish_claim(factory, claim, broken)
    assert incident_outbox.claim_next(factory) is None
    with factory.begin() as db:
        db.get(IncidentDelivery, claim.event_id).lease_until = datetime.now(
            timezone.utc
        ) - timedelta(seconds=1)
    replacement = incident_outbox.claim_next(factory)
    assert replacement.event_id == claim.event_id and replacement.token != claim.token
    with pytest.raises(incident_outbox.StaleDelivery):
        incident_outbox.publish_claim(
            factory, claim, lambda _: pytest.fail("stale publish")
        )
    envelope = incident_outbox.publish_claim(factory, replacement, seen.append)
    assert envelope["event_id"] == seen[0]["event_id"]
    assert envelope["data"]["incident"]["incident_version"] == 1
    assert envelope["measurement_source"] == "simulator"
    with factory() as db:
        assert db.get(IncidentDelivery, claim.event_id).attempts == 2
        assert db.get(IncidentDelivery, claim.event_id).delivered_at is not None
    assert incident_outbox.run_once(factory, seen.append)
    assert seen[-1]["data"]["incident"]["incident_version"] == 2
    assert incident_outbox.run_once(factory, seen.append) is False


def test_publish_success_expired_receipt_is_not_acknowledged(monitored):
    _, factory, *_ = monitored
    opened(monitored)
    claim = incident_outbox.claim_next(factory)

    def expires_after_send(_):
        with factory.begin() as db:
            db.get(IncidentDelivery, claim.event_id).lease_until = datetime.now(
                timezone.utc
            ) - timedelta(seconds=1)

    with pytest.raises(incident_outbox.StaleDelivery):
        incident_outbox.publish_claim(factory, claim, expires_after_send)
    with factory() as db:
        assert db.get(IncidentDelivery, claim.event_id).delivered_at is None
    assert incident_outbox.run_once(factory, lambda _: None)


@pytest.mark.parametrize(
    "field", ["stream", "reading_identity", "configuration_version", "measurement_time"]
)
@pytest.mark.parametrize("advancing", [False, True])
def test_authoritative_result_bindings_rejected_without_detector(
    configured, field, advancing
):
    # This also protects streams without detector opt-in and unavailable results.
    _, factory, *_ = configured
    submit(configured, 0, process=False)
    claim = claim_next(factory)

    def contradictory(*args):
        result = adapter.compute(*args)
        result["execution_status"]["state_advanced"] = advancing
        result["metadata"][field] = {
            "stream": {
                "asset_id": "wrong-asset",
                "source": "simulator",
                "run_id": "incident-test",
            },
            "reading_identity": {"reading_id": 987654, "message_id": str(uuid4())},
            "configuration_version": 987,
            "measurement_time": "2025-01-01T00:00:00Z",
        }[field]
        return result

    with pytest.raises(ComputationError, match="reading_binding_mismatch"):
        process_claim(factory, claim, compute=contradictory)
    with factory() as db:
        assert count(db, AnalyticsResult) == count(db, AnalyticsState) == 0
    process_claim(factory, claim)


def test_populated_a001_upgrade_backfills_pending_and_preserves_records(monitored):
    _, factory, *_ = monitored
    opened(monitored)
    submit(monitored, 240, load=0.5)
    source_engine = factory.kw["bind"]
    with source_engine.connect() as db:
        source_schema = db.scalar(text("SELECT current_schema()"))
    target_schema = "a001_upgrade_test_" + uuid4().hex
    admin = create_engine(source_engine.url)
    with admin.begin() as db:
        db.execute(text(f'CREATE SCHEMA "{target_schema}"'))
    engine = create_engine(
        source_engine.url, connect_args={"options": f"-csearch_path={target_schema}"}
    )
    config = Config("backend/alembic.ini")
    # Copy real stored fixtures to an independently migrated A001 schema. The
    # delivery table does not exist there; no destructive downgrade is needed.
    tables = (
        "assets",
        "asset_configurations",
        "telemetry_readings",
        "telemetry_processing_jobs",
        "analytics_results",
        "analytics_streams",
        "analytics_states",
        "maintenance_tasks",
        "maintenance_task_history",
        "incident_operators",
        "incident_detector_epochs",
        "incident_detector_controls",
        "incidents",
        "incident_evidence",
        "incident_events",
        "incident_operations",
    )
    try:
        with engine.begin() as db:
            config.attributes["connection"] = db
            command.upgrade(config, "a001_incident_registry")
            for table in tables:
                names = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema=:schema AND table_name=:table ORDER BY ordinal_position"), {"schema":target_schema,"table":table}).scalars().all()
                columns = ','.join('"'+n+'"' for n in names)
                db.execute(
                    text(
                        f'INSERT INTO "{table}" ({columns}) SELECT {columns} FROM "{source_schema}"."{table}"'
                    )
                )

            def records():
                return {
                    t: db.execute(
                        text(f'SELECT to_jsonb(t) FROM "{t}" t ORDER BY to_jsonb(t)')
                    )
                    .scalars()
                    .all()
                    for t in tables
                }

            before = records()
            command.upgrade(config, "head")
            command.check(config)
            after = records()
            for table, saved in before.items():
                assert len(after[table]) == len(saved)
                for old, new in zip(saved, after[table]):
                    assert all(new[key] == value for key, value in old.items())
                    assert all(value is None for key, value in new.items() if key not in old)
            assert db.scalar(text("SELECT count(*) FROM incident_deliveries")) == 2
            assert (
                db.scalar(
                    text(
                        "SELECT count(*) FROM incident_deliveries WHERE attempts=0 AND delivered_at IS NULL"
                    )
                )
                == 2
            )
            assert (
                db.scalar(text("SELECT version_num FROM alembic_version"))
                == "d006_combined_integration"
            )
    finally:
        engine.dispose()
        with admin.begin() as db:
            db.execute(text(f'DROP SCHEMA "{target_schema}" CASCADE'))
        admin.dispose()


@pytest.mark.parametrize(
    "field",
    ["asset_id", "detector_epoch", "stream", "result_id", "reading_id", "message_id"],
)
def test_contradictory_planner_commands_roll_back(monitored, monkeypatch, field):
    _, factory, *_ = monitored
    submit(monitored, 0)
    submit(monitored, 180, process=False)
    claim = claim_next(factory)
    planner = incidents.evaluate_incident_candidates

    def contradictory(*args, **kwargs):
        plan = planner(*args, **kwargs)
        command = plan["mutations"][0]
        if field in ("asset_id", "detector_epoch"):
            command["mapping_key"][field] = "wrong-binding"
        elif field == "stream":
            command["stream"]["run_id"] = "wrong-run"
        else:
            command["evidence"][field] = 999999
        return plan

    monkeypatch.setattr(incidents, "evaluate_incident_candidates", contradictory)
    with pytest.raises(IncidentPlanningError, match="Contradictory command binding"):
        process_claim(factory, claim)
    with factory() as db:
        assert count(db, AnalyticsResult) == 1
        assert count(db, IncidentDelivery) == count(db, Incident) == 0


def test_ack_and_handover_enqueue_once_without_recovering(monitored):
    client, factory, asset_id, actors, _ = monitored
    incident = opened(monitored)
    path = f"/api/v1/incidents/{incident['incident_id']}/acknowledgements"
    body = {
        "schema_version": "incident-acknowledgement-1.0.0",
        "expected_version": 1,
        "idempotency_key": str(uuid4()),
    }
    assert client.post(path, json=body, headers=actors["operator"]).status_code == 201
    assert client.post(path, json=body, headers=actors["operator"]).status_code == 200
    from backend.tests.test_incidents import control

    response, request = control(client, asset_id, actors["admin"], version=1)
    assert response.status_code == 201
    response = client.post(
        f"/api/v1/assets/{asset_id}/detector-handovers",
        json=request,
        headers=actors["admin"],
    )
    assert response.status_code == 200
    with factory() as db:
        assert count(db, IncidentDelivery) == count(db, IncidentEvent) == 3
        current = db.scalar(select(Incident))
        assert current.condition_status == "active" and current.actor_id is not None
        assert current.monitoring_status == "interrupted"
