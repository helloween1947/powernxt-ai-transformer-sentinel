"""Workflow, migration and atomic-history checks against isolated PostgreSQL schemas."""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
from datetime import datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

from backend.app.models.maintenance import MaintenanceTaskHistory
from backend.app.schemas.maintenance import TaskUpdate
from backend.app.services import maintenance

ROOT = "/api/v1/maintenance/tasks"
HEADERS = {"X-Demo-Actor": "Person D demo operator"}


@pytest.fixture
def workflow_task(registry, asset):
    client, _ = registry
    response = client.post(ROOT, json={
        "alert": {"source": "sample", "alert_id": "sample-workflow",
                  "asset_id": asset["asset_id"], "summary": "Workflow test fixture"},
        "action": "Sample inspection",
    })
    assert response.status_code == 201
    return response.json()


def update(client, task, **changes):
    return client.patch(f"{ROOT}/{task['id']}", headers=HEADERS,
                        json={"expected_version": task["version"], **changes})


def history(client, task):
    return client.get(f"{ROOT}/{task['id']}/history").json()["items"]


def test_assignment_start_complete_and_history(registry, workflow_task):
    client, _ = registry
    assert workflow_task["owner"] is None and workflow_task["version"] == 1
    initial = history(client, workflow_task)[0]
    assert initial["event_type"] == "created"
    assert initial["actor"] is None and initial["identity_source"] == "unattributed_creation"
    assigned = update(client, workflow_task, owner="  Demo maintainer  ").json()
    assert assigned["owner"] == "Demo maintainer" and assigned["version"] == 2
    started = update(client, assigned, status="in_progress", notes="Inspection started").json()
    completed = update(client, started, status="completed", notes="Sample inspection finished").json()
    assert completed["status"] == "completed" and completed["version"] == 4
    rows = history(client, completed)
    assert [row["version"] for row in rows] == [1, 2, 3, 4]
    assert rows[-1]["previous_status"] == "in_progress" and rows[-1]["new_status"] == "completed"
    assert rows[-1]["previous_notes"] == "Inspection started"
    assert rows[-1]["notes"] == "Sample inspection finished"
    assert rows[1]["previous_owner"] is None and rows[1]["new_owner"] == "Demo maintainer"
    assert all(row["actor"] == HEADERS["X-Demo-Actor"] and row["identity_source"] == "demo_header" for row in rows[1:])
    assert completed["alert"] == workflow_task["alert"]  # Completion never resolves an alert.
    assert completed["created_at"] == workflow_task["created_at"]
    assert completed["updated_at"] != completed["created_at"]


@pytest.mark.parametrize("start", [False, True])
def test_cancel_requires_reason_and_is_terminal(registry, workflow_task, start):
    client, _ = registry
    task = workflow_task
    if start:
        task = update(client, task, owner="Demo", status="in_progress").json()
    cancelled = update(client, task, status="cancelled", notes="Sample task no longer needed")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert update(client, cancelled.json(), status="open").status_code == 409
    assert update(client, cancelled.json(), notes="Rewrite reason").status_code == 409


@pytest.mark.parametrize("changes", [
    {"status": "completed", "notes": ""}, {"status": "cancelled", "notes": "   "},
    {"status": "completed"}, {"status": "cancelled"}, {"owner": "  "},
    {"status": "Completed"}, {"status": None}, {"notes": None},
    {"notes": "x" * 2001}, {"actor": "spoofed"}, {},
])
def test_invalid_updates_have_no_history_side_effect(registry, workflow_task, changes):
    client, _ = registry
    assert update(client, workflow_task, **changes).status_code == 422
    assert client.get(f"{ROOT}/{workflow_task['id']}").json() == workflow_task
    assert len(history(client, workflow_task)) == 1


def test_assignment_and_transition_rules(registry, workflow_task):
    client, _ = registry
    assert update(client, workflow_task, status="in_progress").status_code == 422
    assert update(client, workflow_task, status="completed", notes="Done").status_code == 409
    assert update(client, workflow_task, status="open").status_code == 422  # no-op
    started = update(client, workflow_task, owner="Demo", status="in_progress").json()
    assert update(client, started, status="open").status_code == 409
    assert update(client, started, owner=None).status_code == 422
    completed = update(client, started, status="completed", notes="Finished").json()
    assert update(client, completed, owner="Other demo").status_code == 409


def test_demo_actor_and_expected_version_are_required(registry, workflow_task):
    client, _ = registry
    path = f"{ROOT}/{workflow_task['id']}"
    payload = {"expected_version": 1, "owner": "Demo"}
    assert client.patch(path, json=payload).status_code == 422
    assert client.patch(path, headers={"X-Demo-Actor": "  "}, json=payload).status_code == 422
    assert client.patch(path, headers=HEADERS, json={"owner": "Demo"}).status_code == 422
    for invalid in (0, True, "1"):
        assert client.patch(path, headers=HEADERS, json={**payload, "expected_version": invalid}).status_code == 422


def test_unassign_open_task_and_stale_version(registry, workflow_task):
    client, _ = registry
    assigned = update(client, workflow_task, owner="Demo").json()
    assert update(client, workflow_task, notes="Stale update").status_code == 409
    unassigned = update(client, assigned, owner=None)
    assert unassigned.status_code == 200 and unassigned.json()["owner"] is None
    assert [row["version"] for row in history(client, workflow_task)] == [1, 2, 3]


def test_unknown_task_and_history_pagination(registry, workflow_task):
    client, _ = registry
    unknown = {**workflow_task, "id": str(uuid4())}
    assert update(client, unknown, owner="Demo").status_code == 404
    assert client.get(f"{ROOT}/{unknown['id']}/history").status_code == 404
    assigned = update(client, workflow_task, owner="Demo").json()
    page = client.get(f"{ROOT}/{assigned['id']}/history", params={"limit": 1, "offset": 1}).json()
    assert page["limit"] == 1 and page["offset"] == 1 and page["items"][0]["version"] == 2
    assert client.get(f"{ROOT}/{assigned['id']}/history", params={"limit": 101}).status_code == 422


def test_concurrent_updates_reject_one_stale_writer(registry, workflow_task):
    client, factory = registry

    def write(owner):
        with factory() as db:
            try:
                result = maintenance.update_task(db, workflow_task["id"], TaskUpdate(expected_version=1, owner=owner), "Demo")
                return result.owner
            except maintenance.TaskUpdateConflict:
                db.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ["Demo A", "Demo B"]))
    assert results.count("conflict") == 1
    assert client.get(f"{ROOT}/{workflow_task['id']}").json()["version"] == 2
    assert len(history(client, workflow_task)) == 2


def test_task_and_history_rollback_together(registry, workflow_task):
    client, _ = registry

    def fail_history(*args):
        raise OperationalError("insert history", {}, Exception("private history storage error"))

    event.listen(MaintenanceTaskHistory, "before_insert", fail_history)
    try:
        response = update(client, workflow_task, owner="Demo")
        assert response.status_code == 503 and "private" not in response.text
    finally:
        event.remove(MaintenanceTaskHistory, "before_insert", fail_history)
    assert client.get(f"{ROOT}/{workflow_task['id']}").json() == workflow_task
    assert len(history(client, workflow_task)) == 1
    assert update(client, workflow_task, owner="Demo").status_code == 200


def test_history_survives_fresh_application_process(registry, workflow_task):
    client, factory = registry
    updated = update(client, workflow_task, owner="Demo", status="in_progress", notes="Started").json()
    expected = history(client, workflow_task)
    with factory() as db:
        schema = db.scalar(text("select current_schema()"))
        url = db.bind.url.set(query={"options": f"-csearch_path={schema}"})
    env = {**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False)}
    code = (
        "import json; from fastapi.testclient import TestClient; "
        "from backend.app.main import create_app; client=TestClient(create_app()); "
        f"task=client.get('{ROOT}/{updated['id']}'); "
        f"history=client.get('{ROOT}/{updated['id']}/history'); "
        "assert task.status_code==200 and history.status_code==200; "
        "print(json.dumps([task.json(),history.json()['items']]))"
    )
    for _ in range(2):
        result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True,
                                text=True, check=True, timeout=20)
        assert json.loads(result.stdout) == [updated, expected]


def test_d001_upgrade_preserves_existing_task_and_labels_import(registry, asset):
    client, factory = registry
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    task_id = str(uuid4())
    with factory.kw["bind"].begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "d001_maintenance")
        connection.execute(text("""INSERT INTO maintenance_tasks
            (id, asset_id, alert_source, alert_id, alert_summary, action, status)
            VALUES (:id, :asset, 'sample', 'sample-legacy', 'Old sample', 'Old action', 'open')"""),
            {"id": task_id, "asset": asset["asset_id"]})
        old_time = connection.scalar(text("SELECT created_at FROM maintenance_tasks WHERE id=:id"), {"id": task_id})
        command.upgrade(config, "head")
    task = client.get(f"{ROOT}/{task_id}").json()
    assert task["id"] == task_id and task["action"] == "Old action"
    assert task["owner"] is None and task["version"] == 1
    assert task["updated_at"] == task["created_at"]
    assert datetime.fromisoformat(task["created_at"].replace("Z", "+00:00")) == old_time
    row = history(client, task)[0]
    assert row["event_type"] == "legacy_import" and row["actor"] is None


def test_downgrade_refuses_to_discard_workflow(registry, workflow_task):
    client, factory = registry
    assert update(client, workflow_task, owner="Demo").status_code == 200
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with pytest.raises(RuntimeError, match="Workflow data exists"):
        with factory.kw["bind"].begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "d001_maintenance")
    assert client.get(f"{ROOT}/{workflow_task['id']}").json()["version"] == 2
    assert len(history(client, workflow_task)) == 2
