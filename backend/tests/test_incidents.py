"""Real PostgreSQL incident transactions, authentication and worker orchestration."""

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from backend.app.analytics import adapter
from backend.app.analytics.person_b.incident_orchestration import IncidentPlanningError
from backend.app.models.analytics import (
    AnalyticsResult,
    AnalyticsState,
)
from backend.app.models.incidents import (
    DetectorControl,
    DetectorEpoch,
    Incident,
    IncidentEvent,
    IncidentEvidence,
    Operator,
)
from backend.app.schemas.incidents import Acknowledgement
from backend.app.services import incidents
from backend.app.services.analytics_worker import (
    StaleClaim,
    claim_next,
    process_claim,
    record_failure,
    run_once,
)
from backend.tests import test_analytics_worker as worker_tests
from backend.tests.test_analytics_worker import expire, packet

configured = worker_tests.configured


@pytest.fixture
def actors(registry):
    _, factory = registry
    credentials = {}
    with factory.begin() as db:
        for role in ("reader", "operator", "admin", "revoked", "expired"):
            token = "test-only-" + uuid4().hex
            actor = Operator(
                id=uuid4(),
                name=role,
                role=role if role in ("reader", "operator", "admin") else "operator",
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                active=role != "revoked",
                expires_at=datetime.now(timezone.utc)
                + timedelta(hours=-1 if role == "expired" else 1),
            )
            db.add(actor)
            credentials[role] = {"Authorization": "Bearer " + token}
    return credentials


def policy(quantity="electrical_metrics.capacity_loading_pct"):
    return {
        "version": "explicit-assumed-test-v1",
        "provenance": "assumed",
        "max_gap_s": 300,
        "rules": [
            {
                "name": "overload",
                "quantity": quantity,
                "unit": "%" if quantity.startswith("electrical") else "C",
                "trigger": 120 if quantity.startswith("electrical") else 50,
                "recovery": 100 if quantity.startswith("electrical") else 40,
                "persistence_s": 180,
                "recovery_s": 120,
                "severity": "warning",
            }
        ],
    }


def control(
    client, asset_id, headers, *, run="incident-test", version=0, config=1, **changes
):
    body = {
        "schema_version": "incident-control-1.0.0",
        "expected_version": version,
        "idempotency_key": str(uuid4()),
        "source": "simulator",
        "run_id": run,
        "configuration_version": config,
        "model_version": adapter.MODEL_VERSION,
        "detector_version": "sustained-threshold-1.0.1",
        "policy": policy(),
        "reason": "Explicit isolated test policy",
    }
    body.update(changes)
    return client.post(
        f"/api/v1/assets/{asset_id}/detector-handovers", json=body, headers=headers
    ), body


@pytest.fixture
def monitored(configured, actors):
    client, factory, asset_id, _ = configured
    response, _ = control(client, asset_id, actors["admin"])
    assert response.status_code == 201, response.text
    return client, factory, asset_id, actors, response.json()


def submit(
    setup,
    seconds,
    load=1.5,
    *,
    run="incident-test",
    version=1,
    missing_oil=False,
    process=True,
):
    client, factory, asset_id = setup[:3]
    body = packet(asset_id, seconds, run=run, version=version)
    body["measurements"].update({f"current_{p}_a": 52.49 * load for p in "ryb"})
    if missing_oil:
        body["measurements"]["oil_temperature_c"] = None
        body["measurement_quality"]["oil_temperature_c"] = "missing"
    response = client.post("/api/v1/telemetry", json=body)
    assert response.status_code == 201, response.text
    if process:
        assert run_once(factory)
    return response.json(), body


def listing(setup, **parameters):
    client, _, asset_id, actors = setup[:4]
    params = {
        "asset_id": asset_id,
        "source": "simulator",
        "run_id": "incident-test",
        **parameters,
    }
    return client.get(
        "/api/v1/incidents",
        params={k: v for k, v in params.items() if v is not None},
        headers=actors["reader"],
    )


def opened(setup):
    submit(setup, 0)
    submit(setup, 180)
    result = listing(setup)
    assert result.status_code == 200, result.text
    assert len(result.json()["items"]) == 1
    return result.json()["items"][0]


def test_real_lifecycle_ack_evidence_reopen(monitored):
    client, factory, _, actors, _ = monitored
    incident = opened(monitored)
    assert UUID(incident["incident_id"]).version == 4
    assert (
        incident["source"] == "analytics" and incident["condition_status"] == "active"
    )
    assert incident["acknowledgement"]["status"] == "unacknowledged"
    iid = incident["incident_id"]
    ack = {
        "schema_version": "incident-acknowledgement-1.0.0",
        "expected_version": 1,
        "idempotency_key": str(uuid4()),
    }
    response = client.post(
        f"/api/v1/incidents/{iid}/acknowledgements",
        json=ack,
        headers=actors["operator"],
    )
    assert response.status_code == 201, response.text
    acknowledged = response.json()
    assert (
        acknowledged["incident_version"] == 2
        and acknowledged["condition_status"] == "active"
    )
    submit(monitored, 240, 0.5)
    submit(monitored, 360, 0.5)
    latest = client.get(f"/api/v1/incidents/{iid}", headers=actors["reader"]).json()
    assert latest["condition_status"] == "recovered" and latest["incident_version"] == 4
    assert latest["acknowledgement"] == acknowledged["acknowledgement"]
    retry = client.post(
        f"/api/v1/incidents/{iid}/acknowledgements",
        json=ack,
        headers=actors["operator"],
    )
    assert retry.status_code == 200 and retry.json() == acknowledged
    evidence = client.get(
        f"/api/v1/incidents/{iid}/evidence", headers=actors["reader"]
    ).json()["items"]
    assert [e["payload"]["observation_kind"] for e in evidence] == [
        "opened",
        "updated",
        "recovered",
    ]
    for e in evidence:
        p = e["payload"]
        assert p["data_confidence"]["score"] is None and p["temperature_unit"] == "C"
        assert p["versions"]["model_version"] == adapter.MODEL_VERSION
        exact = client.get(
            f"/api/v1/analytics/results/{p['result_id']}", headers=actors["reader"]
        )
        assert (
            exact.status_code == 200
            and exact.json()["result"]["reading_id"] == p["reading_id"]
        )
        assert "ground_truth" not in json.dumps(p)
        with factory() as db:
            result = db.get(AnalyticsResult, p["result_id"])
            assert result.reading_id == p["reading_id"]
            assert (
                result.payload["metadata"]["reading_identity"]["message_id"]
                == p["message_id"]
            )
            t = p["temperatures"]
            if t["thermal_residual_c"] is not None:
                assert t["thermal_residual_c"] == pytest.approx(
                    t["measured_top_oil_temperature_c"]
                    - t["predicted_top_oil_temperature_c"]
                )
    events = client.get(
        f"/api/v1/incidents/{iid}/events", headers=actors["reader"]
    ).json()["items"]
    assert [e["event_type"] for e in events] == [
        "incident.opened",
        "incident.acknowledged",
        "incident.updated",
        "incident.recovered",
    ]
    assert len({e["event_id"] for e in events}) == 4
    submit(monitored, 420)
    submit(monitored, 600)
    assert len(listing(monitored).json()["items"]) == 2
    assert len(listing(monitored, condition_status="active").json()["items"]) == 1


@pytest.mark.parametrize("role", [None, "revoked", "expired"])
def test_untrusted_actor_rejected(registry, actors, role):
    client, _ = registry
    headers = (
        {"X-Demo-Actor": "pretend administrator"} if role is None else actors[role]
    )
    response = client.get("/api/v1/incidents/" + str(uuid4()), headers=headers)
    assert response.status_code == 401 and response.json()["code"] == "unauthenticated"
    assert response.headers["www-authenticate"] == "Bearer"


def test_roles_validation_not_found_and_cors(monitored):
    client, _, asset_id, actors, _ = monitored
    iid = opened(monitored)["incident_id"]
    path = f"/api/v1/incidents/{iid}/acknowledgements"
    body = {
        "schema_version": "incident-acknowledgement-1.0.0",
        "expected_version": 1,
        "idempotency_key": str(uuid4()),
    }
    assert client.post(path, json=body, headers=actors["reader"]).status_code == 403
    assert (
        control(client, asset_id, actors["operator"], version=1)[0].status_code == 403
    )
    assert (
        client.get(
            "/api/v1/incidents/" + str(uuid4()), headers=actors["reader"]
        ).status_code
        == 404
    )
    missing = client.get("/api/v1/analytics/results/99999999", headers=actors["reader"])
    assert missing.status_code == 404 and missing.json()["code"] == "result_not_found"
    for edit in (
        {"schema_version": "future"},
        {"expected_version": True},
        {"actor_ref": "spoof"},
    ):
        response = client.post(path, json={**body, **edit}, headers=actors["operator"])
        assert (
            response.status_code == 422
            and response.json()["schema_version"] == "incident-error-1.0.0"
        )
    response = client.post(
        path,
        content='{"expected_version":NaN}',
        headers={**actors["operator"], "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert listing(monitored, limit=101).status_code == 422
    assert listing(monitored, source="device").status_code == 422
    preflight = client.options(
        path,
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert preflight.status_code == 200
    schema = client.get("/openapi.json").json()
    assert schema["paths"][path.replace(iid, "{incident_id}")]["post"]["security"] == [
        {"IncidentBearer": []}
    ]


def test_version_and_idempotency_conflicts(monitored):
    client, _, _, actors, _ = monitored
    iid = opened(monitored)["incident_id"]
    path = f"/api/v1/incidents/{iid}/acknowledgements"
    payload = {
        "schema_version": "incident-acknowledgement-1.0.0",
        "expected_version": 2,
        "idempotency_key": str(uuid4()),
    }
    stale = client.post(path, json=payload, headers=actors["operator"])
    assert stale.status_code == 409 and stale.json()["current_version"] == 1
    payload["expected_version"] = 1
    assert (
        client.post(path, json=payload, headers=actors["operator"]).status_code == 201
    )
    conflict = client.post(
        path, json={**payload, "expected_version": 2}, headers=actors["operator"]
    )
    assert conflict.json()["code"] == "idempotency_conflict"
    conflict = client.post(path, json=payload, headers=actors["admin"])
    assert (
        conflict.status_code == 409
        and conflict.json()["code"] == "idempotency_conflict"
    )
    again = client.post(
        path,
        json={**payload, "expected_version": 2, "idempotency_key": str(uuid4())},
        headers=actors["operator"],
    )
    assert again.json()["code"] == "already_acknowledged"


@pytest.mark.parametrize("equivalent", [True, False])
def test_concurrent_acknowledgements(monitored, equivalent):
    _, factory, _, _, _ = monitored
    iid = UUID(opened(monitored)["incident_id"])
    barrier = threading.Barrier(2)
    shared = uuid4()

    def action(index):
        with factory() as db:
            actor = db.scalar(select(Operator).where(Operator.name == "operator"))
            payload = Acknowledgement(
                schema_version="incident-acknowledgement-1.0.0",
                expected_version=1,
                idempotency_key=shared if equivalent else uuid4(),
            )
            barrier.wait(timeout=10)
            try:
                return incidents.acknowledge(
                    db, iid, payload, actor, datetime.now(timezone.utc)
                )[1]
            except incidents.IncidentError as exc:
                db.rollback()
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(action, range(2)))
    assert outcomes.count(True) == 1
    assert (False in outcomes) if equivalent else ("version_conflict" in outcomes)
    with factory() as db:
        assert db.get(Incident, iid).version == 2
        assert db.scalar(select(func.count()).select_from(IncidentEvent)) == 2


def test_stream_isolation_pagination_and_duplicate_ingestion(monitored):
    client, factory, _, actors, _ = monitored
    iid = opened(monitored)["incident_id"]
    reading, body = submit(monitored, 240)
    assert client.post("/api/v1/telemetry", json=body).status_code == 200
    assert not run_once(factory)
    for params in (
        {"run_id": "other"},
        {"source": "file_replay"},
        {"source": "device", "run_id": None},
    ):
        assert listing(monitored, **params).json()["items"] == []
    pages = client.get(
        f"/api/v1/incidents/{iid}/events", params={"limit": 1}, headers=actors["reader"]
    ).json()
    assert pages["next_cursor"] == 1
    follow = client.get(
        f"/api/v1/incidents/{iid}/events",
        params={"cursor": 1, "limit": 1},
        headers=actors["reader"],
    ).json()
    assert follow["items"][0]["incident_version"] == 2 and follow["next_cursor"] is None
    assert (
        client.get(
            f"/api/v1/incidents/{iid}/evidence",
            params={"cursor": 1},
            headers=actors["reader"],
        ).json()["items"][0]["payload"]["reading_id"]
        == reading["id"]
    )
    # Unconfigured stream continues analytics, but cannot create operational incidents.
    submit(monitored, 0, run="not-enabled")
    submit(monitored, 180, run="not-enabled")
    assert listing(monitored, run_id="not-enabled").json()["items"] == []
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Incident)) == 1


def test_historical_results_do_not_advance_context_or_latest(monitored):
    client, factory, _, actors, _ = monitored
    incident = opened(monitored)
    with factory() as db:
        before = db.scalar(select(DetectorEpoch)).context
    submit(monitored, 60, 0.5)
    submit(monitored, 180, 0.5)
    with factory() as db:
        assert db.scalar(select(DetectorEpoch)).context == before
        assert db.scalar(select(func.count()).select_from(IncidentEvidence)) == 1
    assert (
        client.get(
            "/api/v1/incidents/" + incident["incident_id"], headers=actors["reader"]
        ).json()
        == incident
    )


def test_atomic_rollback_and_stale_claim(monitored):
    _, factory, _, _, _ = monitored
    submit(monitored, 0)
    submit(monitored, 180, process=False)
    claim = claim_next(factory)

    def fail(db):
        assert db.scalar(select(func.count()).select_from(Incident)) == 1
        assert db.scalar(select(func.count()).select_from(IncidentEvidence)) == 1
        assert db.scalar(select(func.count()).select_from(IncidentEvent)) == 1
        raise RuntimeError("labelled rollback injection")

    with pytest.raises(RuntimeError):
        process_claim(factory, claim, before_commit=fail)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Incident)) == 0
        assert db.scalar(select(func.count()).select_from(AnalyticsResult)) == 1
        assert db.scalar(select(AnalyticsState)).advances == 1
    process_claim(factory, claim)
    with pytest.raises(StaleClaim):
        process_claim(factory, claim)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Incident)) == 1


def test_failure_barrier_and_gap_do_not_credit_missing_endpoints(monitored):
    _, factory, _, _, _ = monitored
    submit(monitored, 0)
    submit(monitored, 60, process=False)
    claim = claim_next(factory, max_attempts=1)
    record_failure(factory, claim, ValueError("labelled failure"), max_attempts=1)
    with factory() as db:
        assert db.scalar(select(DetectorControl)).continuity_break
    submit(monitored, 180)
    assert listing(monitored).json()["items"] == []
    with factory() as db:
        assert not db.scalar(select(DetectorControl)).continuity_break
    submit(monitored, 360)
    assert len(listing(monitored).json()["items"]) == 1


def test_unavailable_evidence_does_not_recover(monitored):
    client, _, asset_id, actors, _ = monitored
    response, _ = control(
        client,
        asset_id,
        actors["admin"],
        version=1,
        policy=policy("thermal_assessment.measured_top_oil_temperature_c"),
    )
    assert response.status_code == 201
    iid = opened(monitored)["incident_id"]
    submit(monitored, 240, missing_oil=True)
    incident = client.get("/api/v1/incidents/" + iid, headers=actors["reader"]).json()
    assert (
        incident["condition_status"] == "active"
        and incident["last_evidence_status"] == "unavailable"
    )
    current = client.get(
        f"/api/v1/incidents/{iid}/evidence", headers=actors["reader"]
    ).json()["items"][-1]["payload"]
    assert (
        current["rule_evidence"]["value"] is None
        and current["rule_evidence"]["reasons"]
    )
    assert current["observation_kind"] == "evidence_unavailable"


def test_recorded_handover_preserves_active_incident_and_cold_starts(monitored):
    client, factory, asset_id, actors, first = monitored
    incident = opened(monitored)
    response, body = control(client, asset_id, actors["admin"], version=1)
    assert response.status_code == 201
    successor = response.json()
    with factory() as db:
        saved_epoch = db.get(DetectorEpoch, UUID(successor["detector_epoch"]))
        assert (
            saved_epoch.previous_twin_state["state"]
            == db.scalar(select(AnalyticsState)).state
        )
    assert (
        successor["previous_epoch"] == first["detector_epoch"]
        and successor["detector_epoch"] != first["detector_epoch"]
    )
    retry = client.post(
        f"/api/v1/assets/{asset_id}/detector-handovers",
        json=body,
        headers=actors["admin"],
    )
    assert retry.status_code == 200 and retry.json() == successor
    submit(monitored, 240)
    submit(monitored, 420)
    current = client.get(
        "/api/v1/incidents/" + incident["incident_id"], headers=actors["reader"]
    ).json()
    assert (
        current["condition_status"] == "active"
        and current["monitoring_status"] == "interrupted"
    )
    assert current["recovered_at"] is None
    assert len(listing(monitored).json()["items"]) == 2
    with factory() as db:
        result = db.scalar(
            select(AnalyticsResult).order_by(AnalyticsResult.id.desc()).offset(1)
        )
        assert (
            result.payload["thermal_assessment"]["predicted_top_oil_temperature_c"]
            is None
        )


def test_namespace_mismatch_requires_handover_and_busy_stream_rejects(monitored):
    client, factory, asset_id, actors, _ = monitored
    cfg = client.get("/api/v1/assets/" + asset_id).json()["current_configuration"]
    remove = {"asset_id", "version", "created_at"}
    next_cfg = client.post(
        f"/api/v1/assets/{asset_id}/configurations",
        json={k: v for k, v in cfg.items() if k not in remove},
    )
    assert next_cfg.status_code == 201, next_cfg.text
    submit(monitored, 0, version=2, process=False)
    claim = claim_next(factory)
    busy, _ = control(client, asset_id, actors["admin"], version=1, config=2)
    assert busy.status_code == 409 and busy.json()["code"] == "stream_busy"
    with pytest.raises(IncidentPlanningError, match="Recorded handover"):
        process_claim(factory, claim)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(AnalyticsResult)) == 0
    expire(factory, claim)
    changed, _ = control(client, asset_id, actors["admin"], version=1, config=2)
    assert changed.status_code == 201
    assert run_once(factory)
    assert listing(monitored).json()["items"] == []


def test_database_constraints_immutability_and_populated_downgrade(monitored):
    _, factory, _, _, _ = monitored
    opened(monitored)
    with factory.begin() as db:
        for query in (
            "UPDATE incident_evidence SET payload='{}'",
            "DELETE FROM incident_events",
            "UPDATE incident_detector_epochs SET policy='{}'",
            "DELETE FROM incident_operations",
        ):
            with pytest.raises(IntegrityError), db.begin_nested():
                db.execute(text(query))
        config = Config("backend/alembic.ini")
        config.attributes["connection"] = db.connection()
        with pytest.raises(RuntimeError, match="downgrade refused"), db.begin_nested():
            command.downgrade(config, "d004_worker_maintenance")
        assert db.scalar(select(func.count()).select_from(Incident)) == 1


def test_ack_failure_rolls_back_incident_and_history(monitored, monkeypatch):
    client, factory, _, actors, _ = monitored
    iid = opened(monitored)["incident_id"]
    original = incidents.event

    def fail(*args, **kw):
        original(*args, **kw)
        raise IntegrityError("labelled fault injection", {}, Exception())

    monkeypatch.setattr(incidents, "event", fail)
    body = {
        "schema_version": "incident-acknowledgement-1.0.0",
        "expected_version": 1,
        "idempotency_key": str(uuid4()),
    }
    response = client.post(
        f"/api/v1/incidents/{iid}/acknowledgements",
        json=body,
        headers=actors["operator"],
    )
    assert (
        response.status_code == 503
        and response.json()["code"] == "database_unavailable"
    )
    with factory() as db:
        assert db.get(Incident, UUID(iid)).version == 1
        assert db.scalar(select(func.count()).select_from(IncidentEvent)) == 1


def test_canonical_asset_and_result_binding_database_enforced(monitored):
    client, factory, _, _, _ = monitored
    iid = opened(monitored)["incident_id"]
    submit(monitored, 240, run="different-stream")
    assert (
        client.post(
            "/api/v1/assets",
            json={
                "asset_id": "different-asset",
                "name": "Other",
                "location": "Isolated test",
                "timezone": "UTC",
            },
        ).status_code
        == 201
    )
    with factory.begin() as db:
        evidence = db.scalar(select(IncidentEvidence))
        other = db.scalar(select(AnalyticsResult).order_by(AnalyticsResult.id.desc()))
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(
                text("UPDATE incidents SET asset_id=:asset WHERE id=:id"),
                {"asset": "different-asset", "id": iid},
            )
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(
                text("""INSERT INTO incident_evidence
                (incident_id,incident_version,result_id,reading_id,detector_version,policy_fingerprint,payload)
                VALUES (:id,10,:result,:reading,:detector,:policy,'{}')"""),
                {
                    "id": iid,
                    "result": other.id,
                    "reading": other.reading_id,
                    "detector": evidence.detector_version,
                    "policy": evidence.policy_fingerprint,
                },
            )


def test_gap_and_expired_terminal_lease_preserve_continuity(monitored):
    _, factory, _, _, _ = monitored
    submit(monitored, 0)
    submit(monitored, 60, process=False)
    claim = claim_next(factory, max_attempts=1)
    expire(factory, claim)
    assert not run_once(factory, max_attempts=1)
    with factory() as db:
        assert db.scalar(select(DetectorControl)).continuity_break
    submit(monitored, 180)
    assert listing(monitored).json()["items"] == []
    submit(monitored, 481)  # Beyond configured 300-second continuity window.
    assert listing(monitored).json()["items"] == []
    submit(monitored, 661)
    assert len(listing(monitored).json()["items"]) == 1


def test_private_operator_provision_rotate_revoke(
    registry, tmp_path, monkeypatch, capsys
):
    from backend.app import operators

    client, factory = registry
    monkeypatch.setattr(operators, "SessionLocal", factory)
    token_file = tmp_path / "private-token"
    monkeypatch.setattr(
        "sys.argv",
        [
            "operators",
            "issue",
            "--name",
            "Trusted operator",
            "--role",
            "operator",
            "--token-file",
            str(token_file),
        ],
    )
    operators.main()
    token = token_file.read_text().strip()
    assert token not in capsys.readouterr().out
    headers = {"Authorization": "Bearer " + token}
    result = client.get("/api/v1/operators/me", headers=headers)
    assert result.status_code == 200 and result.json()["role"] == "operator"
    assert "token_hash" not in result.json()
    actor_id = result.json()["actor_ref"]
    rotate_file = tmp_path / "rotated-token"
    monkeypatch.setattr(
        "sys.argv",
        [
            "operators",
            "issue",
            "--name",
            "Trusted operator",
            "--role",
            "reader",
            "--token-file",
            str(rotate_file),
        ],
    )
    operators.main()
    assert client.get("/api/v1/operators/me", headers=headers).status_code == 401
    new_headers = {"Authorization": "Bearer " + rotate_file.read_text().strip()}
    result = client.get("/api/v1/operators/me", headers=new_headers)
    assert result.json()["actor_ref"] == actor_id and result.json()["role"] == "reader"
    monkeypatch.setattr(
        "sys.argv", ["operators", "revoke", "--name", "Trusted operator"]
    )
    operators.main()
    assert client.get("/api/v1/operators/me", headers=new_headers).status_code == 401


def test_handover_bad_policy_configuration_unknown_asset_and_conflicting_retry(
    monitored,
):
    client, _, asset_id, actors, _ = monitored
    wrong, _ = control(client, "absent-asset", actors["admin"])
    assert wrong.status_code == 404 and wrong.json()["code"] == "asset_not_found"
    wrong, _ = control(client, asset_id, actors["admin"], version=1, config=999)
    assert (
        wrong.status_code == 404 and wrong.json()["code"] == "configuration_not_found"
    )
    invalid = policy()
    invalid["rules"][0]["recovery"] = 130
    assert (
        control(client, asset_id, actors["admin"], version=1, policy=invalid)[
            0
        ].status_code
        == 422
    )
    assert (
        control(
            client,
            asset_id,
            actors["admin"],
            version=1,
            model_version="stored-reading-top-oil-1.0.2",
        )[0].status_code
        == 422
    )
    success, body = control(client, asset_id, actors["admin"], version=1)
    assert success.status_code == 201
    response = client.post(
        f"/api/v1/assets/{asset_id}/detector-handovers",
        json={**body, "reason": "Changed"},
        headers=actors["admin"],
    )
    assert (
        response.status_code == 409
        and response.json()["code"] == "idempotency_conflict"
    )


def test_concurrent_workers_can_commit_one_opening_only(monitored):
    _, factory, _, _, _ = monitored
    submit(monitored, 0)
    submit(monitored, 180, process=False)
    claim = claim_next(factory)
    barrier = threading.Barrier(2)

    def compute(*args):
        value = adapter.compute(*args)
        barrier.wait(timeout=10)
        return value

    def action(_):
        try:
            process_claim(factory, claim, compute=compute)
            return "committed"
        except StaleClaim:
            return "fenced"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(action, range(2))) == ["committed", "fenced"]
    with factory() as db:
        for model in (Incident, IncidentEvidence, IncidentEvent):
            assert db.scalar(select(func.count()).select_from(model)) == 1


def test_registry_upgrade_preserves_completed_cancelled_sample_history(
    registry, asset, configuration
):
    client, factory = registry
    assert (
        client.post(
            f"/api/v1/assets/{asset['asset_id']}/configurations", json=configuration
        ).status_code
        == 201
    )
    cfg = Config("backend/alembic.ini")
    with factory.kw["bind"].begin() as connection:
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, "d004_worker_maintenance")
        for status in ("open", "completed", "cancelled"):
            tid = uuid4()
            connection.execute(
                text("""INSERT INTO maintenance_tasks
                (id,asset_id,alert_source,alert_id,alert_summary,action,status,owner,notes,version)
                VALUES (:id,:asset,'sample',:alert,'Original sample','Inspect',:status,'Demo actor','Original notes',3)"""),
                {
                    "id": tid,
                    "asset": asset["asset_id"],
                    "alert": "sample-" + status,
                    "status": status,
                },
            )
            connection.execute(
                text("""INSERT INTO maintenance_task_history
                (task_id,version,event_type,new_status,new_owner,notes,actor,identity_source)
                VALUES (:id,3,'updated',:status,'Demo actor','Original notes','Demo actor','demo_header')"""),
                {"id": tid, "status": status},
            )
        tables = (
            "assets",
            "asset_configurations",
            "maintenance_tasks",
            "maintenance_task_history",
        )

        def records():
            return {
                t: connection.execute(
                    text(f"SELECT to_jsonb(t) FROM {t} t ORDER BY to_jsonb(t)")
                )
                .scalars()
                .all()
                for t in tables
            }

        before = records()
        command.upgrade(cfg, "head")
        command.check(cfg)
        assert records() == before
