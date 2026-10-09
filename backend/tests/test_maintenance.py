"""Use A's migrated, isolated PostgreSQL fixture; no finished analytics required."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError

from backend.app.models.maintenance import MaintenanceTask
from backend.app.services import maintenance
from backend.app.schemas.maintenance import TaskCreate

ROOT = "/api/v1/maintenance/tasks"


@pytest.fixture
def task_payload(asset):
    fixture = Path(__file__).resolve().parents[2] / "integration/fixtures/sample-maintenance-task.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["alert"]["asset_id"] = asset["asset_id"]
    return payload


def test_create_retrieve_retry_and_conflict(registry, task_payload):
    client, factory = registry
    created = client.post(ROOT, json=task_payload)
    assert created.status_code == 201
    task = created.json()
    assert task["alert"] == task_payload["alert"]
    assert task["asset_id"] == task["alert"]["asset_id"]
    assert task["status"] == "open"
    assert task["action"] == task_payload["action"]
    assert task["created_at"].endswith(("Z", "+00:00"))
    assert created.headers["location"] == f"{ROOT}/{task['id']}"
    assert client.get(created.headers["location"]).json() == task
    retry = client.post(ROOT, json=task_payload)
    assert retry.status_code == 200
    assert retry.json() == task
    for field in ("action", "summary"):
        changed = copy.deepcopy(task_payload)
        if field == "action":
            changed[field] = "Different action"
        else:
            changed["alert"][field] = "Different alert description"
        assert client.post(ROOT, json=changed).status_code == 409
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(MaintenanceTask)) == 1
    assert client.get(created.headers["location"]).json() == task


@pytest.mark.parametrize("change", [
    {"alert": None}, {"action": "  "}, {"action": "x" * 1001},
    {"alert.source": "analytics"}, {"alert.alert_id": "real-alert"},
    {"alert.asset_id": ""}, {"alert.summary": "  "},
    {"status": "completed"}, {"asset_id": "another-asset"},
])
def test_invalid_payloads(registry, task_payload, change):
    client, _ = registry
    payload = copy.deepcopy(task_payload)
    for field, value in change.items():
        if "." in field:
            parent, key = field.split(".")
            payload[parent][key] = value
        else:
            payload[field] = value
    assert client.post(ROOT, json=payload).status_code == 422


def test_unknown_asset_and_task(registry, task_payload):
    client, _ = registry
    task_payload["alert"]["asset_id"] = "missing"
    assert client.post(ROOT, json=task_payload).status_code == 404
    assert client.get(ROOT, params={"asset_id": "missing"}).status_code == 404
    assert client.get(f"{ROOT}/{uuid4()}").status_code == 404
    assert client.get(f"{ROOT}/not-a-uuid").status_code == 422
    assert client.get(ROOT).json()["items"] == []


def test_asset_filter_and_pagination(registry, task_payload):
    client, _ = registry
    other = {"asset_id": "other", "name": "Other", "location": "Lab", "timezone": "UTC"}
    assert client.post("/api/v1/assets", json=other).status_code == 201
    for index in range(3):
        payload = copy.deepcopy(task_payload)
        payload["alert"]["alert_id"] = f"sample-{index}"
        if index == 2:
            payload["alert"]["asset_id"] = "other"
        assert client.post(ROOT, json=payload).status_code == 201
    page = client.get(ROOT, params={"asset_id": "test-transformer", "limit": 1}).json()
    second = client.get(ROOT, params={"asset_id": "test-transformer", "limit": 1, "offset": 1}).json()
    assert page["limit"] == 1 and page["offset"] == 0
    assert page["items"][0]["id"] != second["items"][0]["id"]
    assert client.get(ROOT, params={"asset_id": "other"}).json()["items"][0]["asset_id"] == "other"
    assert client.get(ROOT, params={"limit": 0}).status_code == 422
    assert client.get(ROOT, params={"limit": 101}).status_code == 422
    assert client.get(ROOT, params={"offset": -1}).status_code == 422


def test_concurrent_retries_create_one_task(registry, task_payload):
    _, factory = registry

    def create():
        with factory() as db:
            return maintenance.create_task(db, TaskCreate.model_validate(task_payload))

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: create(), range(4)))
    assert len({str(task.id) for task, _ in results}) == 1
    assert sum(created for _, created in results) == 1


def test_database_failure_is_masked(registry, task_payload, monkeypatch):
    client, _ = registry

    def unavailable(*args, **kwargs):
        raise OperationalError("statement", {}, Exception("private database details"))

    monkeypatch.setattr(maintenance, "create_task", unavailable)
    response = client.post(ROOT, json=task_payload)
    assert response.status_code == 503
    assert "private database details" not in response.text


def test_task_survives_fresh_application_process(registry, task_payload):
    client, factory = registry
    created = client.post(ROOT, json=task_payload).json()
    with factory() as db:
        schema = db.scalar(text("select current_schema()"))
        url = db.bind.url.set(query={"options": f"-csearch_path={schema}"})
    env = {**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False)}
    # Each invocation imports a fresh app/engine, reads the saved task via HTTP
    # TestClient, then exits. No parent Session or in-memory store is shared.
    code = (
        "from fastapi.testclient import TestClient; "
        "from backend.app.main import create_app; "
        "import json; "
        "client=TestClient(create_app()); "
        f"response=client.get('{ROOT}/{created['id']}'); "
        "assert response.status_code == 200; print(json.dumps(response.json()))"
    )
    for _ in range(2):
        result = subprocess.run([sys.executable, "-c", code], env=env,
                                capture_output=True, text=True, timeout=20, check=True)
        assert json.loads(result.stdout) == created
