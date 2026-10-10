"""Append labelled readings; the separately started normal worker must process them."""
import argparse
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
import httpx

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base', required=True)
parser.add_argument('--evidence', required=True)
args = parser.parse_args()
assert args.base.startswith('http://127.0.0.1:') and int(args.base.rsplit(':', 1)[1]) > 15000
folder = Path(args.evidence)
seed = json.loads((folder / 'seed.json').read_text())
assert seed['asset_id'].startswith('d-ui-') and seed['run_id'].startswith('synthetic-ui-')
with httpx.Client(base_url=args.base, timeout=15) as client:
    latest = client.get(f"/api/v1/assets/{seed['asset_id']}/telemetry/latest", params={'source': seed['source'], 'run_id': seed['run_id']})
    latest.raise_for_status()
    start = datetime.fromisoformat(latest.json()['measurement_time'])
    ids = []
    for second in range(1, 23):
        packet = {'schema_version': '1.0.0', 'asset_id': seed['asset_id'], 'source': seed['source'], 'run_id': seed['run_id'], 'configuration_version': 1, 'message_id': str(uuid4()), 'timestamp': (start + timedelta(seconds=second)).isoformat(), 'measurements': {**{f'voltage_{p}_v': 11000 for p in 'ryb'}, **{f'current_{p}_a': 52.49 * 1.5 for p in 'ryb'}, 'oil_temperature_c': 55, 'ambient_temperature_c': 30}}
        receipt = client.post('/api/v1/telemetry', json=packet)
        assert receipt.status_code == 201
        ids.append(receipt.json()['id'])
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if all(client.get(f'/api/v1/telemetry/{item}/analytics').json()['status'] == 'completed' for item in ids):
            break
        time.sleep(.2)
    else:
        raise AssertionError('Normal worker did not complete all readings')
    token = (folder / 'private' / 'admin.txt').read_text().strip()
    pages = {}
    for kind in ('events', 'evidence'):
        page = client.get(f"/api/v1/incidents/{seed['incident_ids'][0]}/{kind}", headers={'Authorization': 'Bearer ' + token}).json()
        assert page['next_cursor'] is not None
        pages[kind] = {'first_page_count': len(page['items']), 'next_cursor': page['next_cursor']}
    (folder / 'normal-worker.json').write_text(json.dumps({'reading_ids': ids, 'completed': len(ids), 'pages': pages}, indent=2) + '\n')
print('PASS normal worker CLI processed 22 appended readings; incident record pagination available')
