"""Strict live Docker/API acceptance; all mutations require isolated Compose proof.

Host SQL snapshots/outbox dispatcher use the same isolated Docker PostgreSQL.
Analytics run in the actual Docker worker, except the explicitly labelled old
model fixture computed by the preserved old implementation inside the backend
container. No development callbacks, credentials or database URLs are logged.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.app.analytics import adapter
from backend.app.services import incident_outbox

ROOT=Path(__file__).resolve().parents[1]
TABLES=('assets','asset_configurations','telemetry_readings','telemetry_processing_jobs',
        'analytics_streams','analytics_states','analytics_results')

def verify(base, output):
    project=os.environ.get('COMPOSE_PROJECT_NAME','')
    dburl=make_url(os.environ['TEST_DATABASE_URL'])
    assert project.startswith('analytics_worker_test_')
    assert dburl.database=='worker_integration_test' and dburl.host=='127.0.0.1'
    compose=['docker','compose','--profile','analytics']
    def docker(*args, input=None):
        return subprocess.run(compose+list(args),cwd=ROOT,check=True,capture_output=True,text=True,input=input).stdout
    resolved=json.loads(docker('config','--format','json'))
    assert resolved['services']['db']['container_name']==project+'-db'
    assert resolved['volumes']['postgres_data']['name']==project+'-postgres_data'
    assert base=='http://'+docker('port','backend','8000').strip()
    assert str(dburl.port)==str(resolved['services']['db']['ports'][0]['published'])
    engine=create_engine(dburl); factory=sessionmaker(bind=engine)
    result={'timestamp':datetime.now().astimezone().isoformat(),'project':project,'api':base,'checks':{},'identifiers':{}}
    asset='completion-'+uuid4().hex; run='synthetic-'+uuid4().hex
    result['identifiers'].update(asset=asset,source='simulator',run=run,configuration=1)
    name='completion-admin-'+uuid4().hex[:8]; tokenfile='/tmp/'+name
    client=httpx.Client(base_url=base,timeout=15)
    def checked(response,status=200):
        assert response.status_code==status,(response.status_code,response.text)
        return response.json()
    def snapshot(tables=TABLES):
        with engine.connect() as db:
            return {table:db.execute(text(f'SELECT to_jsonb(t) FROM "{table}" t ORDER BY to_jsonb(t)')).scalars().all() for table in tables}
    def await_result(reading):
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            response=checked(client.get(f'/api/v1/telemetry/{reading}/analytics'))
            if response['status'] in ('completed','unavailable','failed'):
                assert response['status']=='completed',response
                return response
            time.sleep(.1)
        raise AssertionError('Bounded worker wait exhausted')
    def packet(seconds,load=1.5,**changes):
        body={'schema_version':'1.0.0','asset_id':asset,'source':'simulator','run_id':run,'configuration_version':1,
              'message_id':str(uuid4()),'timestamp':(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=seconds)).isoformat(),
              'measurements':{**{f'voltage_{p}_v':11000 for p in 'ryb'},**{f'current_{p}_a':52.49*load for p in 'ryb'},'oil_temperature_c':55,'ambient_temperature_c':30}}
        body.update(changes); return body
    def submit(seconds,load=1.5,**changes):
        reading=checked(client.post('/api/v1/telemetry',json=packet(seconds,load,**changes)),201)
        return reading,await_result(reading['id'])
    def scenario(selected_run=run,**changes):
        return {'schema_version':'what-if-request-1.0.0','source':'simulator','run_id':selected_run,
                'baseline':{'duration_s':3600,'thermal_load_pu':1.5,'ambient_temperature_c':30},
                'reduced_load':{'duration_s':3600,'thermal_load_pu':.75,'ambient_temperature_c':30},**changes}
    path=f'/api/v1/assets/{asset}'
    try:
        checked(client.get('/health/ready'))
        openapi=checked(client.get('/openapi.json'))
        Path(output).with_name('actual-openapi.json').write_text(json.dumps(openapi,indent=2)+'\n')
        checked(client.post('/api/v1/assets',json={'asset_id':asset,'name':'Synthetic completion acceptance','location':'Isolated test','timezone':'UTC'}),201)
        config=json.loads((ROOT/'data/sample/asset-configuration-worker-assumed.json').read_text())
        cfg=checked(client.post(path+'/configurations',json=config),201)
        before=snapshot()
        for value in (True,'1000',float('inf')):
            body={**config,'rated_kva':value}
            encoded=json.dumps(body)
            checked(client.post(path+'/configurations',content=encoded,headers={'Content-Type':'application/json'}),422)
        bad=packet(0); bad['timestamp']='0001-01-01T00:00:00+01:00'
        checked(client.post('/api/v1/telemetry',json=bad),422)
        checked(client.post('/api/v1/telemetry',json=packet(0,asset_id='unknown-'+uuid4().hex)),404)
        checked(client.post('/api/v1/telemetry',json=packet(0,configuration_version=999)),422)
        assert snapshot()==before
        result['checks']['validation_rollback']='PASS: boolean/string/nonfinite physical input, UTC underflow, unknown asset/config; no persisted changes'
        docker('exec','-T','backend','python','-m','backend.app.operators','issue','--name',name,'--role','admin','--token-file',tokenfile)
        token=docker('exec','-T','backend','python','-c',f"from pathlib import Path; print(Path('{tokenfile}').read_text().strip())").strip()
        auth={'Authorization':'Bearer '+token}
        checked(client.get('/api/v1/operators/me',headers=auth))
        checked(client.get('/api/v1/operators/me'),401)
        checked(client.get('/api/v1/operators/me',headers={'Authorization':'Bearer invalid'}),401)
        policy={'version':'assumed-completion-v1','provenance':'assumed','max_gap_s':300,'rules':[{'name':'overload','quantity':'electrical_metrics.capacity_loading_pct','unit':'%','trigger':120,'recovery':100,'persistence_s':180,'recovery_s':120,'severity':'warning'}]}
        control={'schema_version':'incident-control-1.0.0','expected_version':0,'idempotency_key':str(uuid4()),'source':'simulator','run_id':run,'configuration_version':1,'model_version':adapter.MODEL_VERSION,'detector_version':'sustained-threshold-1.0.1','reason':'Explicit synthetic assumed policy, not field diagnosis','policy':policy}
        checked(client.post(path+'/detector-handovers',json=control),401)
        checked(client.post(path+'/detector-handovers',json={**control,'model_version':'stored-reading-top-oil-1.0.1'},headers=auth),409)
        adopted=checked(client.post(path+'/detector-handovers',json=control,headers=auth),201)
        assert checked(client.post(path+'/detector-handovers',json=control,headers=auth))==adopted
        first,first_result=submit(0)
        assert first_result['result']['payload']['thermal_assessment']['predicted_top_oil_temperature_c'] is None
        second,second_result=submit(180)
        query={'asset_id':asset,'source':'simulator','run_id':run}
        incident=checked(client.get('/api/v1/incidents',params=query,headers=auth))['items'][0]
        result['identifiers'].update(incident=incident['incident_id'],readings=[first['id'],second['id']])
        task_body={'alert':{'source':'analytics','incident_id':incident['incident_id'],'asset_id':asset},'action':'Review synthetic persisted evidence'}
        task=checked(client.post('/api/v1/maintenance/tasks',json=task_body,headers=auth),201)
        assert checked(client.post('/api/v1/maintenance/tasks',json=task_body,headers=auth))==task
        task_path='/api/v1/maintenance/tasks/'+task['id']
        checked(client.get(task_path),401)
        before=snapshot()
        forecast=checked(client.post(path+'/what-if',json=scenario()))
        assert forecast['model']['model_version']==adapter.MODEL_VERSION
        assert forecast['baseline']['points'][0]==forecast['reduced_load']['points'][0]
        assert forecast['final_temperature_difference_c']<0
        assert forecast['baseline']['limit_crossing']['status'] in ('crossing','no_crossing_within_horizon')
        assert snapshot()==before
        ref=forecast['state']['state_ref']
        assert checked(client.post(path+'/what-if',json=scenario(state_ref=ref)))==forecast
        result['checks']['what_if']='PASS: successful initialized capture, exact replay, units/limit outcomes/difference; zero worker-table mutation (snapshot insert is intentional)'
        # Concurrent identical admissions against real API/worker.
        same=packet(240)
        with ThreadPoolExecutor(max_workers=6) as pool:
            responses=list(pool.map(lambda _:client.post('/api/v1/telemetry',json=same),range(6)))
        assert sorted(r.status_code for r in responses)==[200]*5+[201]
        ids={r.json()['id'] for r in responses}; assert len(ids)==1
        await_result(next(iter(ids)))
        checked(client.post('/api/v1/telemetry',json={**same,'measurements':{**same['measurements'],'oil_temperature_c':56}}),409)
        # Same message UUID in another source is independent.
        separate=checked(client.post('/api/v1/telemetry',json={**same,'source':'file_replay'}),201)
        assert separate['id'] not in ids; await_result(separate['id'])
        pages=[checked(client.get(path+'/telemetry',params={**query,'limit':2,'offset':offset}))['items'] for offset in (0,2)]
        assert [len(page) for page in pages]==[2,1]
        assert checked(client.get(path+'/telemetry/latest',params=query))['id']==next(iter(ids))
        result['checks']['concurrent_ingestion']='PASS: 1x201+5x200, one ID, changed-content409, separate-source result, chronological pagination/latest'
        # Worker update, immutable replay, ack and genuine assignment overlap.
        latest_incident=checked(client.get('/api/v1/incidents/'+incident['incident_id'],headers=auth))
        ack={'schema_version':'incident-acknowledgement-1.0.0','expected_version':latest_incident['incident_version'],'idempotency_key':str(uuid4())}
        barrier=threading.Barrier(4)
        def concurrent(kind):
            barrier.wait(timeout=10)
            if kind=='reading': return client.post('/api/v1/telemetry',json=packet(300))
            if kind=='scenario': return client.post(path+'/what-if',json=scenario(state_ref=ref))
            if kind=='ack': return client.post('/api/v1/incidents/'+incident['incident_id']+'/acknowledgements',json=ack,headers=auth)
            return client.patch(task_path,json={'expected_version':task['version'],'owner':'Synthetic reviewer'},headers=auth)
        with ThreadPoolExecutor(max_workers=4) as pool:
            reading,replay,ack_response,assigned=list(pool.map(concurrent,('reading','scenario','ack','task')))
        reading=checked(reading,201); await_result(reading['id'])
        assert checked(replay)==forecast
        task=checked(assigned)
        assert ack_response.status_code in (201,409)
        if ack_response.status_code==409:
            assert ack_response.json()['code']=='version_conflict'
            current=checked(client.get('/api/v1/incidents/'+incident['incident_id'],headers=auth))
            ack={**ack,'expected_version':current['incident_version'],'idempotency_key':str(uuid4())}
            ack_response=client.post('/api/v1/incidents/'+incident['incident_id']+'/acknowledgements',json=ack,headers=auth)
        receipt=checked(ack_response,201)
        assert checked(client.post('/api/v1/incidents/'+incident['incident_id']+'/acknowledgements',json=ack,headers=auth))==receipt
        for update in ({'status':'in_progress'},{'status':'completed','notes':'Synthetic review; no recovery inferred'}):
            task=checked(client.patch(task_path,json={'expected_version':task['version'],**update},headers=auth))
        active=checked(client.get('/api/v1/incidents/'+incident['incident_id'],headers=auth))
        assert active['condition_status']=='active' and active['acknowledgement']['status']=='acknowledged'
        submit(360,.5); submit(480,.5)
        recovered=checked(client.get('/api/v1/incidents/'+incident['incident_id'],headers=auth))
        assert recovered['condition_status']=='recovered'
        assert checked(client.get(task_path,headers=auth))==task
        assert checked(client.post('/api/v1/maintenance/tasks',json=task_body,headers=auth))==task
        result['checks']['worker_incident_tasks_concurrency']='PASS: worker-backed open/update/recovery; independent acknowledgement, task completion and recovery; concurrent ingestion/replay/ack/assignment'
        result['identifiers'].update(task=task['id'],state_ref=ref)
        # Only a local receiver; simulate publish accepted but receipt lost.
        received=[]
        class Receiver(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(204); self.end_headers()
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Receiver)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        def publish(envelope):
            response=httpx.post(f'http://127.0.0.1:{server.server_port}/',json=envelope,timeout=5)
            assert response.status_code==204
        try:
            claim=incident_outbox.claim_next(factory,lease_seconds=.1); assert claim
            def lost_receipt(envelope):
                publish(envelope); raise RuntimeError('simulated receipt loss')
            try: incident_outbox.publish_claim(factory,claim,lost_receipt)
            except RuntimeError: pass
            else: raise AssertionError('Expected simulated delivery failure')
            time.sleep(.15)
            assert incident_outbox.run_once(factory,publish)
            assert received[0]['event_id']==received[1]['event_id'] and received[0]['data']==received[1]['data']
            while incident_outbox.run_once(factory,publish): pass
            with engine.connect() as db:
                assert db.scalar(text('SELECT count(*) FROM incident_deliveries WHERE delivered_at IS NULL'))==0
            result['checks']['outbox']='PASS: host dispatcher against Docker PostgreSQL, local HTTP receiver, lost receipt/redelivery stable ID, all receipts committed'
            result['outbox_receipts']=[{'event_id':e['event_id'],'event_type':e['event_type']} for e in received]
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
        # Actual preserved old model computes fixture inside Docker, not relabelled .2.
        docker('stop','worker')
        historic_run='historical-'+uuid4().hex
        old_reading=checked(client.post('/api/v1/telemetry',json=packet(0,run_id=historic_run)),201)
        script="""from backend.app.analytics import adapter
from backend.app.analytics.person_b.historical_v101 import worker as old
from backend.app.db.session import SessionLocal
from backend.app.services.analytics_worker import run_once
adapter.MODEL_VERSION=old.MODEL_VERSION
adapter.compute=lambda reading,config,previous,policy:old.compute_analytics(reading.normalized_telemetry,config,reading.quality_flags,reading.id,previous,state_policy=policy)
assert run_once(SessionLocal)
print('Preserved old implementation computed isolated fixture')
"""
        docker('exec','-T','backend','python','-',input=script)
        old_forecast=checked(client.post(path+'/what-if',json=scenario(historic_run)))
        assert old_forecast['model']['model_version']=='stored-reading-top-oil-1.0.1'
        model_control={'schema_version':'model-control-1.0.0','expected_version':0,'idempotency_key':str(uuid4()),'source':'simulator','run_id':historic_run,'configuration_version':1,'model_version':adapter.MODEL_VERSION,'reason':'Explicit isolated old-model adoption'}
        checked(client.post(path+'/model-handovers',json=model_control),401)
        checked(client.post(path+'/model-handovers',json=model_control,headers=auth),201)
        docker('start','worker')
        new_reading,new_result=submit(60,run_id=historic_run)
        assert new_result['result']['model_version']==adapter.MODEL_VERSION
        assert new_result['result']['payload']['thermal_assessment']['predicted_top_oil_temperature_c'] is None
        assert checked(client.post(path+'/what-if',json=scenario(historic_run,state_ref=old_forecast['state']['state_ref'])))==old_forecast
        result['checks']['historical_adoption']='PASS: genuine .1 Docker-computed snapshot; authenticated .2 handover, cold start, exact .1 replay'
        before=snapshot();docker('restart','backend')
        for attempt in range(60):
            try:
                if client.get('/health/ready').status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.5)
        else:raise AssertionError('Restart readiness timeout')
        assert snapshot()==before
        assert checked(client.get(task_path,headers=auth))==task
        assert checked(client.post(path+'/what-if',json=scenario(state_ref=ref)))==forecast
        assert checked(client.get(path+'/configurations'))['items'][0]==cfg
        result['checks']['restart_preservation']='PASS: exact full core table rows, original config, terminal task and immutable forecast'
        docker('exec','-T','backend','python','-m','backend.app.operators','revoke','--name',name)
        checked(client.get('/api/v1/operators/me',headers=auth),401)
        result['checks']['credential_lifecycle']='PASS: container CLI issue, invalid/missing401, successful trusted operations, revoked401; expired/role cases in full PostgreSQL suite'
        result['status']='PASS'
    finally:
        try:
            docker('exec','-T','backend','python','-m','backend.app.operators','revoke','--name',name)
            docker('exec','-T','backend','python','-c',f"from pathlib import Path; Path('{tokenfile}').unlink(missing_ok=True)")
        finally:
            client.close();engine.dispose()
            Path(output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();verify(args.base_url,args.output)
