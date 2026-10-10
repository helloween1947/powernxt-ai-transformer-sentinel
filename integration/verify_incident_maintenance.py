"""Isolated live HTTP/worker task verification; retain records for restart checks.

Requires A's deployed dependency plus D005 in an isolated *_test database and
an admin credential. No automatic acknowledgement/task coupling or UI claims.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.app.models.assets import Asset
from backend.app.services.analytics_worker import run_once


def checked(response, status=200):
    assert response.status_code == status, f"Unexpected HTTP status {response.status_code}"
    return response.json()


def verify(base_url, database_url, token_file, state_file, resume=False):
    target, dburl = urlparse(base_url), make_url(database_url)
    if target.scheme != "http" or target.hostname not in ("localhost", "127.0.0.1") or target.port in (None,8000,8001,18001,18002) or target.path.strip('/'):
        raise ValueError("Dedicated non-development loopback API required")
    if not dburl.drivername.startswith('postgresql') or not dburl.database or not dburl.database.endswith('_test'):
        raise ValueError("Isolated PostgreSQL *_test database required")
    token=Path(token_file).read_text().strip()
    with httpx.Client(base_url=base_url, headers={'Authorization':'Bearer '+token},timeout=10) as client:
        assert checked(client.get('/api/v1/operators/me'))['role']=='admin'
        if resume:
            saved=json.loads(Path(state_file).read_text())
            for task in saved['tasks']:
                assert checked(client.get('/api/v1/maintenance/tasks/'+task['id']))==task
                assert checked(client.get('/api/v1/maintenance/tasks/'+task['id']+'/history'))==saved['history'][task['id']]
            assert checked(client.get('/api/v1/incidents/'+saved['incident']['incident_id']))==saved['incident']
            print('PASS: actual API restart retained task/incident/history snapshots')
            return
        engine=create_engine(database_url); factory=sessionmaker(bind=engine)
        asset='d-genuine-test-'+uuid4().hex; run='synthetic-'+uuid4().hex
        checked(client.post('/api/v1/assets',json={'asset_id':asset,'name':'Synthetic D integration','location':'Isolated test','timezone':'UTC'}),201)
        with factory() as db:
            assert db.get(Asset,asset), 'API/database mismatch'
        config={'rated_kva':1000,'rated_voltage_v':11000,'rated_current_a':52.49,'voltage_convention':'line_to_line','measurement_side':'primary','cooling_type':'ONAN'}
        config['parameter_provenance']={k:'assumed' for k in config}
        checked(client.post(f'/api/v1/assets/{asset}/configurations',json=config),201)
        control={'schema_version':'incident-control-1.0.0','expected_version':0,'idempotency_key':str(uuid4()),'source':'simulator','run_id':run,'configuration_version':1,'model_version':'stored-reading-top-oil-1.0.1','detector_version':'sustained-threshold-1.0.1','reason':'Synthetic verification; not physical calibration','policy':{'version':'d-assumed-test-v1','provenance':'assumed','max_gap_s':300,'rules':[{'name':'overload','quantity':'electrical_metrics.capacity_loading_pct','unit':'%','trigger':120,'recovery':100,'persistence_s':180,'recovery_s':120,'severity':'warning'}]}}
        checked(client.post(f'/api/v1/assets/{asset}/detector-handovers',json=control),201)
        def reading(seconds,load):
            packet={'schema_version':'1.0.0','asset_id':asset,'source':'simulator','run_id':run,'configuration_version':1,'message_id':str(uuid4()),'timestamp':(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=seconds)).isoformat(),'measurements':{**{f'voltage_{p}_v':11000 for p in 'ryb'},**{f'current_{p}_a':52.49*load for p in 'ryb'},'oil_temperature_c':55,'ambient_temperature_c':30}}
            checked(client.post('/api/v1/telemetry',json=packet),201); assert run_once(factory)
        reading(0,1.5); reading(180,1.5)
        query={'asset_id':asset,'source':'simulator','run_id':run}
        incident=checked(client.get('/api/v1/incidents',params=query))['items'][0]
        create={'alert':{'source':'analytics','incident_id':incident['incident_id'],'asset_id':asset},'action':'Inspect actual worker overload evidence'}
        task=checked(client.post('/api/v1/maintenance/tasks',json=create),201)
        for update in ({'owner':'Trusted test assignment'},{'status':'in_progress'},{'status':'completed','notes':'Inspected synthetic evidence; no recovery inferred'}):
            task=checked(client.patch('/api/v1/maintenance/tasks/'+task['id'],json={'expected_version':task['version'],**update}))
        assert checked(client.get('/api/v1/incidents/'+incident['incident_id']))==incident
        assert checked(client.post('/api/v1/maintenance/tasks',json=create))==task
        with httpx.Client(base_url=base_url) as anonymous:
            assert anonymous.get('/api/v1/maintenance/tasks/'+task['id']).status_code==401
            assert anonymous.get('/api/v1/maintenance/tasks',params={'source':'analytics'}).status_code==401
            assert all(t['alert']['source']=='sample' for t in checked(anonymous.get('/api/v1/maintenance/tasks'))['items'])
        checked(client.post('/api/v1/incidents/'+incident['incident_id']+'/acknowledgements',json={'schema_version':'incident-acknowledgement-1.0.0','expected_version':incident['incident_version'],'idempotency_key':str(uuid4())}),201)
        reading(240,0.5); reading(360,0.5)
        assert checked(client.get('/api/v1/maintenance/tasks/'+task['id']))==task
        incident=checked(client.get('/api/v1/incidents/'+incident['incident_id']))
        assert incident['condition_status']=='recovered'
        assert checked(client.post('/api/v1/maintenance/tasks',json=create))==task
        sample={'alert':{'source':'sample','alert_id':'sample-'+uuid4().hex,'asset_id':asset,'summary':'Labelled synthetic sample'},'action':'Sample compatibility'}
        sample_task=checked(client.post('/api/v1/maintenance/tasks',json=sample),201)
        sample_task=checked(client.patch('/api/v1/maintenance/tasks/'+sample_task['id'],json={'expected_version':1,'status':'cancelled','notes':'Sample cancellation'},headers={'X-Demo-Actor':'Untrusted sample label'}))
        tasks=[task,sample_task]
        saved={'asset_id':asset,'run_id':run,'tasks':tasks,'incident':incident,'history':{t['id']:checked(client.get('/api/v1/maintenance/tasks/'+t['id']+'/history')) for t in tasks},'limitations':['Synthetic persisted worker evidence; not field calibration','Live HTTP and worker only; no browser or Docker claim']}
        Path(state_file).write_text(json.dumps(saved,indent=2)+'\n')
        engine.dispose()
        print('PASS: live HTTP worker incident, genuine/sample task workflow, independent ack/recovery and terminal retry')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('base-url','database-url','token-file','state-file'): parser.add_argument('--'+name,required=True)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args(); verify(args.base_url,args.database_url,args.token_file,args.state_file,args.resume)
