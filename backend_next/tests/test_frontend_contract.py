"""Cross-language contract test using the actual frontend modules and API output."""
import json
import os
import shutil
import subprocess
from pathlib import Path
from fastapi.testclient import TestClient
from powernxt.api import create_app


def test_real_frontend_consumes_the_backend(tmp_path):
    node = os.getenv('NODE_BIN') or shutil.which('node')
    assert node, 'Node is required for the frontend contract test.'
    with TestClient(create_app(tmp_path/'contract.sqlite3',background=False)) as client:
        asset = client.post('/api/v1/assets',json={'asset_id':'CONTRACT-01','name':'Contract transformer'}).json()
        run = client.post('/api/v1/simulator/runs',json={'asset_id':'CONTRACT-01','scenario':'low_oil'}).json()
        params = {'source':'simulator','run_id':run['run_id']}
        reading = client.get('/api/v1/assets/CONTRACT-01/telemetry/latest',params=params).json()
        bundle = {'asset':asset,'reading':reading,
            'analytics':client.get(f"/api/v1/telemetry/{reading['id']}/analytics").json(),
            'latest':client.get('/api/v1/assets/CONTRACT-01/analytics/latest',params=params).json(),
            'spec':client.get('/openapi.json').json()}
    result = subprocess.run([node,str(Path(__file__).with_name('frontend_contract.mjs'))],input=json.dumps(bundle),text=True,capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
