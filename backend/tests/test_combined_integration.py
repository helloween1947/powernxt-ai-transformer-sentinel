"""Populated branch combinations retain canonical records before the D006 join."""
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from backend.tests.test_incidents import actors, configured, monitored, opened
from backend.tests.test_incident_maintenance import request as task_request
from backend.tests.test_what_if import request as scenario_request


@pytest.mark.parametrize('revisions',[
    ('d004_worker_maintenance',), ('a001_incident_registry',),
    ('a002_incident_outbox',), ('d005_incident_tasks',), ('w001_what_if_snapshots',),
    ('a002_incident_outbox','d005_incident_tasks'),
    ('a002_incident_outbox','w001_what_if_snapshots'),
    ('d005_incident_tasks','w001_what_if_snapshots'),
    ('a002_incident_outbox','d005_incident_tasks','w001_what_if_snapshots'),
])
def test_populated_combined_graph_preserves_records(monitored,revisions):
    client,factory,asset,credentials,_=monitored
    incident=opened(monitored)
    genuine=client.post('/api/v1/maintenance/tasks',json=task_request(incident),headers=credentials['operator'])
    assert genuine.status_code==201
    sample=client.post('/api/v1/maintenance/tasks',json={'alert':{'source':'sample','alert_id':'sample-join','asset_id':asset,'summary':'Preserved sample'},'action':'Inspect sample'})
    assert sample.status_code==201
    snapshot=client.post(f'/api/v1/assets/{asset}/what-if',json=scenario_request(run_id='incident-test'))
    assert snapshot.status_code==200, snapshot.text
    source=factory.kw['bind']
    with source.connect() as db: source_schema=db.scalar(text('SELECT current_schema()'))
    schema='combined_join_'+uuid4().hex
    admin=create_engine(source.url)
    with admin.begin() as db: db.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine=create_engine(source.url,connect_args={'options':f'-csearch_path={schema}'})
    # FK-safe order, using only target-schema columns before additive revisions.
    order=['assets','asset_configurations','telemetry_readings','telemetry_processing_jobs',
           'analytics_results','analytics_streams','analytics_states','incident_operators',
           'incident_detector_epochs','incident_detector_controls','incidents','incident_evidence',
           'incident_events','incident_operations','incident_deliveries',
           'maintenance_tasks','maintenance_task_history','what_if_snapshots']
    cfg=Config('backend/alembic.ini')
    try:
        with engine.begin() as db:
            cfg.attributes['connection']=db
            for revision in revisions: command.upgrade(cfg,revision)
            present=[]
            for table in order:
                cols=db.execute(text('SELECT column_name FROM information_schema.columns WHERE table_schema=:schema AND table_name=:table ORDER BY ordinal_position'),{'schema':schema,'table':table}).scalars().all()
                if not cols: continue
                quoted=','.join('"'+c+'"' for c in cols)
                where=''
                if table=='maintenance_tasks' and 'incident_id' not in cols: where=" WHERE alert_source='sample'"
                if table=='maintenance_task_history' and 'actor_id' not in cols: where=f" WHERE task_id IN (SELECT id FROM \"{schema}\".maintenance_tasks)"
                db.execute(text(f'INSERT INTO "{table}" ({quoted}) SELECT {quoted} FROM "{source_schema}"."{table}"{where}'))
                present.append(table)
            def records():
                return {table:db.execute(text(f'SELECT to_jsonb(t) FROM "{table}" t ORDER BY to_jsonb(t)')).scalars().all() for table in present}
            before=records()
            command.upgrade(cfg,'head')
            assert db.scalar(text('SELECT version_num FROM alembic_version'))=='d006_combined_integration'
            command.check(cfg)
            after=records()
            for table,saved in before.items():
                assert len(after[table])==len(saved)
                for old,new in zip(saved,after[table]):
                    assert all(new[key]==value for key,value in old.items())
                    assert all(value is None for key,value in new.items() if key not in old)
            assert db.scalar(text("SELECT count(*) FROM maintenance_tasks WHERE alert_source='sample' AND incident_id IS NOT NULL"))==0
            if 'incident_events' in present:
                assert db.scalar(text('SELECT count(*) FROM incident_deliveries'))==len(before['incident_events'])
    finally:
        engine.dispose()
        with admin.begin() as db: db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_worker_scenario_ack_and_task_concurrency_keep_axes_independent(monitored):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from backend.tests.test_incidents import submit
    from backend.app.services.analytics_worker import run_once

    client,factory,asset,credentials,_=monitored
    incident=opened(monitored)
    task=client.post('/api/v1/maintenance/tasks',json=task_request(incident),headers=credentials['operator']).json()
    submit(monitored,240,0.5,process=False)
    barrier=Barrier(4)
    def action(kind):
        barrier.wait(timeout=10)
        if kind=='worker': return run_once(factory)
        if kind=='scenario': return client.post(f'/api/v1/assets/{asset}/what-if',json=scenario_request(run_id='incident-test'))
        if kind=='ack': return client.post(f"/api/v1/incidents/{incident['incident_id']}/acknowledgements",json={'schema_version':'incident-acknowledgement-1.0.0','expected_version':1,'idempotency_key':str(uuid4())},headers=credentials['operator'])
        return client.patch('/api/v1/maintenance/tasks/'+task['id'],json={'expected_version':1,'owner':'Independent task assignment'},headers=credentials['operator'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        worker,scenario,ack,updated=list(pool.map(action,['worker','scenario','ack','task']))
    assert worker is True and scenario.status_code==200 and updated.status_code==200
    assert ack.status_code in (201,409)
    if ack.status_code==409: assert ack.json()['code']=='version_conflict'
    saved=client.get('/api/v1/maintenance/tasks/'+task['id'],headers=credentials['reader']).json()
    assert saved['status']=='open' and saved['version']==2 and saved['owner']=='Independent task assignment'
    current=client.get('/api/v1/incidents/'+incident['incident_id'],headers=credentials['reader']).json()
    assert current['condition_status']=='active'
    assert current['incident_version']==(3 if ack.status_code==201 else 2)
    assert current['acknowledgement']['status']==('acknowledged' if ack.status_code==201 else 'unacknowledged')
    # Scenario snapshot's binding trigger plus exact result equality guards torn capture.
    with factory() as db:
        snapshots=db.execute(text('SELECT result_id,state::jsonb FROM what_if_snapshots')).all()
        assert len(snapshots)==1
        result_id,state=snapshots[0]
        assert state==db.scalar(text("SELECT payload::jsonb->'updated_state' FROM analytics_results WHERE id=:id"),{'id':result_id})
