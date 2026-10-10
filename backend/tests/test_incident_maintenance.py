"""D integration uses actual fenced-worker incidents, not relabelled samples."""
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text, event
from sqlalchemy.exc import IntegrityError

from backend.tests.test_incidents import actors, configured, monitored, opened, submit, control
from backend.app.models.maintenance import MaintenanceTask, MaintenanceTaskHistory
from backend.app.models.incidents import Incident
from backend.app.services import maintenance
from backend.app.schemas.maintenance import TaskCreate

ROOT = "/api/v1/maintenance/tasks"


def request(incident):
    return {"alert": {"source": "analytics", "incident_id": incident["incident_id"],
                      "asset_id": incident["asset_id"]}, "action": "Inspect persisted overload evidence"}


def create(setup, incident):
    return setup[0].post(ROOT, json=request(incident), headers=setup[3]["operator"])


def test_genuine_workflow_terminal_retry_and_independent_incident(monitored):
    client, _, _, credentials, _ = monitored
    incident = opened(monitored)
    result = create(monitored, incident)
    assert result.status_code == 201, result.text
    task = result.json()
    assert task["alert"]["incident_id"] == incident["incident_id"]
    assert task["alert"]["measurement_source"] == "simulator"
    assert task["alert"]["evidence_id"] > 0
    for update in ({"owner": "Maintenance team"}, {"status": "in_progress"},
                   {"status": "completed", "notes": "Inspected; physical condition remains independently tracked"}):
        result = client.patch(f"{ROOT}/{task['id']}", json={"expected_version": task["version"], **update}, headers=credentials["operator"])
        assert result.status_code == 200, result.text
        task = result.json()
    saved = client.get(f"/api/v1/incidents/{incident['incident_id']}", headers=credentials["reader"]).json()
    assert saved == incident
    retry = create(monitored, incident)
    assert retry.status_code == 200 and retry.json() == task
    changed = request(incident); changed["action"] = "Different action"
    assert client.post(ROOT, json=changed, headers=credentials["operator"]).status_code == 409
    history = client.get(f"{ROOT}/{task['id']}/history", headers=credentials["reader"]).json()["items"]
    assert len(history) == 4 and all(h["identity_source"] == "authenticated_operator" for h in history)
    assert all(h["actor"] == h["actor_id"] for h in history)
    assert client.get(ROOT).json()["items"] == []
    assert len(client.get(ROOT, params={"source":"analytics"}, headers=credentials["reader"]).json()["items"]) == 1


@pytest.mark.parametrize("role", [None, "expired", "revoked", "reader"])
def test_mutation_credentials(monitored, role):
    incident = opened(monitored)
    headers = monitored[3][role] if role else {"X-Demo-Actor":"spoofed"}
    result = monitored[0].post(ROOT, json=request(incident), headers=headers)
    assert result.status_code == (403 if role == "reader" else 401)


def test_genuine_read_access_and_no_demo_mutation_bypass(monitored):
    incident = opened(monitored); task = create(monitored, incident).json(); client = monitored[0]
    for headers in ({}, {"X-Demo-Actor":"spoofed"}, monitored[3]["expired"], monitored[3]["revoked"]):
        for path in (f"{ROOT}/{task['id']}", f"{ROOT}/{task['id']}/history", ROOT+"?source=analytics"):
            assert client.get(path, headers=headers).status_code == 401
        assert client.patch(f"{ROOT}/{task['id']}", json={"expected_version":1,"owner":"Spoof"}, headers=headers).status_code == 401
    assert client.patch(f"{ROOT}/{task['id']}", json={"expected_version":1,"owner":"Reader"}, headers=monitored[3]["reader"]).status_code == 403


def test_binding_strict_input_and_unknown_incident(monitored):
    incident = opened(monitored); client = monitored[0]; headers=monitored[3]["operator"]
    bad=request(incident); bad["alert"]["asset_id"]="other-transformer"
    assert client.post(ROOT,json=bad,headers=headers).status_code == 422
    bad=request(incident); bad["alert"]["incident_id"]=str(uuid4())
    assert client.post(ROOT,json=bad,headers=headers).status_code == 404
    for field in ("summary", "actor", "run_id"):
        bad=request(incident); bad["alert"][field]="browser claim"
        assert client.post(ROOT,json=bad,headers=headers).status_code == 422


def test_ack_recovery_and_interruption_do_not_change_task(monitored):
    client=monitored[0]; incident=opened(monitored); task=create(monitored,incident).json()
    ack={"schema_version":"incident-acknowledgement-1.0.0","expected_version":1,"idempotency_key":str(uuid4())}
    assert client.post(f"/api/v1/incidents/{incident['incident_id']}/acknowledgements",json=ack,headers=monitored[3]["operator"]).status_code==201
    submit(monitored,240,0.5); submit(monitored,360,0.5)
    assert client.get(f"{ROOT}/{task['id']}",headers=monitored[3]["reader"]).json()==task
    assert create(monitored,incident).json()==task
    # Existing terminal task remains one canonical linkage after incident changes.
    result=client.patch(f"{ROOT}/{task['id']}",json={"expected_version":1,"status":"cancelled","notes":"Explicit operator cancellation"},headers=monitored[3]["operator"])
    assert result.status_code==200
    assert create(monitored,incident).json()==result.json()


@pytest.mark.parametrize("state",["recovered","interrupted"])
def test_unsettled_new_creation_policy_fails_closed(monitored,state):
    incident=opened(monitored)
    if state=="recovered":
        submit(monitored,240,0.5); submit(monitored,360,0.5)
    else:
        assert control(monitored[0],monitored[2],monitored[3]["admin"],version=1)[0].status_code==201
    response=create(monitored,incident)
    assert response.status_code==409 and response.json()["code"]=="incident_creation_policy_required"


def test_concurrent_creates_and_conflict_rollback(monitored):
    incident=opened(monitored)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda role: monitored[0].post(ROOT,json=request(incident),headers=monitored[3][role]),["operator","admin"]))
    assert sorted(r.status_code for r in results)==[200,201]
    assert len({r.json()["id"] for r in results})==1
    task=results[0].json(); client=monitored[0]; headers=monitored[3]["operator"]
    assert client.patch(f"{ROOT}/{task['id']}",json={"expected_version":1,"owner":"A"},headers=headers).status_code==200
    assert client.patch(f"{ROOT}/{task['id']}",json={"expected_version":1,"owner":"B"},headers=headers).status_code==409
    def fail(*_): raise IntegrityError("test",{},Exception("test"))
    event.listen(MaintenanceTaskHistory,"before_insert",fail)
    try:
        assert client.patch(f"{ROOT}/{task['id']}",json={"expected_version":2,"owner":"C"},headers=headers).status_code==409
    finally: event.remove(MaintenanceTaskHistory,"before_insert",fail)
    saved=client.get(f"{ROOT}/{task['id']}",headers=headers).json()
    assert saved["owner"]=="A" and saved["version"]==2
    assert len(client.get(f"{ROOT}/{task['id']}/history",headers=headers).json()["items"])==2


def test_composite_fk_unique_and_restrict(monitored):
    incident=opened(monitored); task=create(monitored,incident).json(); engine=monitored[1].kw['bind']
    for sql in ("UPDATE maintenance_tasks SET asset_id='wrong' WHERE incident_id IS NOT NULL",
                "DELETE FROM incidents WHERE id=:id",
                "UPDATE maintenance_tasks SET alert_source='sample' WHERE incident_id IS NOT NULL"):
        with pytest.raises(IntegrityError):
            with engine.begin() as conn: conn.execute(text(sql),{"id":incident["incident_id"]})
    config=Config(str(Path(__file__).resolve().parents[1]/"alembic.ini"))
    with pytest.raises(Exception,match="downgrade refused"):
        with engine.begin() as conn:
            config.attributes['connection']=conn; command.downgrade(config,"a001_incident_registry")


@pytest.mark.parametrize('base',['d004_worker_maintenance','a001_incident_registry'])
def test_upgrade_sample_records_history_and_metadata(registry,asset,base):
    client,factory=registry; engine=factory.kw['bind']; config=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    sample={'alert':{'source':'sample','alert_id':'sample-migration','asset_id':asset['asset_id'],'summary':'Sample fixture'},'action':'Inspect sample'}
    task=client.post(ROOT,json=sample).json()
    task=client.patch(f"{ROOT}/{task['id']}",json={'expected_version':1,'status':'cancelled','notes':'Retained sample reason'},headers={'X-Demo-Actor':'Sample operator'}).json()
    history=client.get(f"{ROOT}/{task['id']}/history").json()
    with engine.begin() as conn:
        config.attributes['connection']=conn
        command.downgrade(config,base); command.upgrade(config,'head'); command.check(config)
        assert conn.scalar(text('SELECT version_num FROM alembic_version'))=='d005_incident_tasks'
    assert client.get(f"{ROOT}/{task['id']}").json()==task
    assert client.get(f"{ROOT}/{task['id']}/history").json()==history
