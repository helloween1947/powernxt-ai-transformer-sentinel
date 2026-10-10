"""Focused A review regressions; isolated schemas/databases only."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text


@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_maintenance_nonfinite_json_is_422(registry, method, token):
    client, _ = registry
    if method == "POST":
        path = "/api/v1/maintenance/tasks"
        body = '{"alert":' + token + ',"action":"Inspect"}'
    else:
        path = "/api/v1/maintenance/tasks/" + str(uuid4())
        body = '{"expected_version":1,"notes":' + token + "}"
    response = client.request(
        method,
        path,
        content=body,
        headers={"Content-Type": "application/json", "X-Demo-Actor": "Review demo"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Payload must be valid JSON with finite numbers"


def test_combined_routes_and_cors_allow_prototype_patch(registry):
    client, _ = registry
    paths = client.get("/openapi.json").json()["paths"]
    for path in [
        "/api/v1/maintenance/tasks",
        "/api/v1/maintenance/tasks/{task_id}/history",
        "/api/v1/telemetry/{reading_id}/analytics",
        "/api/v1/assets/{asset_id}/telemetry",
    ]:
        assert path in paths
    response = client.options(
        "/api/v1/maintenance/tasks/" + str(uuid4()),
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type,x-demo-actor",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "x-demo-actor" in response.headers["access-control-allow-headers"].lower()
    rejected = client.options(
        "/api/v1/maintenance/tasks",
        headers={
            "Origin": "https://unconfigured.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert (
        rejected.status_code == 400
        and "access-control-allow-origin" not in rejected.headers
    )


@pytest.mark.parametrize("start", ["d730a91b4c22", "d003_audit_maintenance"])
def test_new_join_preserves_worker_results_state_and_maintenance(
    registry, asset, configuration, start
):
    from backend.app.services.analytics_worker import run_once

    client, factory = registry
    # Populate real API/worker records, then strip only the no-op final join.
    cfg = Config("backend/alembic.ini")
    with factory.kw["bind"].begin() as connection:
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, start)
    assert (
        client.post(
            f"/api/v1/assets/{asset['asset_id']}/configurations", json=configuration
        ).status_code
        == 201
    )
    p = json.loads(Path("data/sample/telemetry-sample.json").read_text())
    p.update(asset_id=asset["asset_id"], message_id=str(uuid4()))
    if start == "d003_audit_maintenance":
        # Attach worker branch before API use but leave two applied heads unjoined.
        with factory.kw["bind"].begin() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "d730a91b4c22")
    reading = client.post("/api/v1/telemetry", json=p)
    assert reading.status_code == 201
    if start == "d730a91b4c22":
        assert run_once(
            factory
        )  # Stores genuine electrical evidence with unsupported thermal reasons.
    else:
        # D003 does not yet have worker tables/columns: populate maintenance first.
        task = client.post(
            "/api/v1/maintenance/tasks",
            json={
                "alert": {
                    "source": "sample",
                    "alert_id": "sample-preserve",
                    "asset_id": asset["asset_id"],
                    "summary": "Labelled review example",
                },
                "action": "Inspect",
            },
        )
        assert task.status_code == 201
        update = client.patch(
            "/api/v1/maintenance/tasks/" + task.json()["id"],
            json={
                "expected_version": 1,
                "owner": "Demo",
                "status": "in_progress",
                "notes": "Review persistence",
            },
            headers={"X-Demo-Actor": "Demo"},
        )
        assert update.status_code == 200
    with factory.kw["bind"].begin() as connection:
        cfg.attributes["connection"] = connection
        names = [
            "assets",
            "asset_configurations",
            "telemetry_readings",
            "telemetry_processing_jobs",
        ]
        names += (
            ["analytics_results", "analytics_states", "analytics_streams"]
            if start == "d730a91b4c22"
            else ["maintenance_tasks", "maintenance_task_history"]
        )
        before = {
            name: connection.execute(
                text("SELECT to_jsonb(t) FROM " + name + " t ORDER BY to_jsonb(t)")
            )
            .scalars()
            .all()
            for name in names
        }
        command.upgrade(cfg, "head")
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalars().all() == ["w001_what_if_snapshots"]
        for name, saved in before.items():
            after = (
                connection.execute(
                    text("SELECT to_jsonb(t) FROM " + name + " t ORDER BY to_jsonb(t)")
                )
                .scalars()
                .all()
            )
            assert len(after) == len(saved)
            assert [
                {key: new[key] for key in old} for old, new in zip(saved, after)
            ] == saved
        command.check(cfg)
    if start == "d003_audit_maintenance":
        assert run_once(factory)
    assert (
        client.get(f"/api/v1/telemetry/{reading.json()['id']}/analytics").json()[
            "status"
        ]
        == "completed"
    )
