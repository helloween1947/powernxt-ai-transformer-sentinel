"""Read-only development runtime identity and preserved thermal stream snapshot."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import subprocess

import httpx

ASSET='demo-normal-85203b1018bc498c8b90873f383cc740'
RUN='thermal-144c79522cbd4cd092b7718fea4b05fe'

def capture():
    result={'timestamp':datetime.now().astimezone().isoformat(),'read_only':True,'containers':[]}
    for name in ('sentinel-backend','sentinel-postgres','powernxt-ai-transformer-sentinel-worker-1'):
        data=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]
        result['containers'].append({k:v for k,v in {'name':data['Name'],'image_id':data['Image'],'image_tag':data['Config']['Image'],'started_at':data['State']['StartedAt']}.items()})
    script="""import json,hashlib
from pathlib import Path
from sqlalchemy import text
from backend.app.db.session import engine
files={str(p):hashlib.sha256(p.read_bytes().replace(b'\\r\\n',b'\\n')).hexdigest() for root in ['backend/app','backend/migrations'] for p in Path(root).rglob('*.py')}
with engine.connect() as db: heads=list(db.execute(text('SELECT version_num FROM alembic_version')).scalars())
print(json.dumps({'files':files,'revisions':heads}))
"""
    result['backend_runtime']=json.loads(subprocess.check_output(['docker','exec','sentinel-backend','python','-c',script],text=True))
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=10) as client:
        paths={'openapi':'/openapi.json','configuration_history':f'/api/v1/assets/{ASSET}/configurations','readings':f'/api/v1/assets/{ASSET}/telemetry?source=simulator&run_id={RUN}&limit=100'}
        result['responses']={}
        for label,path in paths.items():
            response=client.get(path);assert response.status_code==200
            result['responses'][label]=response.json()
        readings=result['responses']['readings']['items']
        result['responses']['analytics']={str(r['id']):client.get(f"/api/v1/telemetry/{r['id']}/analytics").json() for r in readings}
    result['preservation_hash']=hashlib.sha256(json.dumps(result['responses'],sort_keys=True).encode()).hexdigest()
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    result=capture();Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'preservation_hash':result['preservation_hash'],'revisions':result['backend_runtime']['revisions'],'containers':result['containers']},indent=2))
