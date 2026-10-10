"""Labelled fixtures for an owned native PostgreSQL/UI review; never development."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from backend.app.analytics.adapter import MODEL_VERSION
from backend.app.services.analytics_worker import run_once


def prepare(base, database_url, token_file, output):
    parsed = make_url(database_url)
    assert parsed.host == '127.0.0.1' and parsed.database.startswith('persond_review_') and parsed.database.endswith('_test')
    assert base.startswith('http://127.0.0.1:') and not base.endswith((':8000', ':8001', ':8801'))
    token = Path(token_file).read_text().strip()
    engine = create_engine(database_url)
    factory = sessionmaker(bind=engine)
    data = {'source': 'simulator', 'run_id': 'synthetic-ui-' + uuid4().hex, 'checks': [], 'sample_task_ids': []}
    with httpx.Client(base_url=base, timeout=15) as client:
        def checked(response, status=200):
            assert response.status_code == status, (response.status_code, response.text)
            return response.json()
        assert checked(client.get('/api/v1/operators/me', headers={'Authorization': 'Bearer ' + token}))['role'] == 'admin'
        data['asset_id'] = asset = 'd-ui-' + uuid4().hex[:12]
        checked(client.post('/api/v1/assets', json={'asset_id': asset, 'name': 'D synthetic integration transformer', 'location': 'Isolated QA laboratory', 'timezone': 'Asia/Kolkata'}), 201)
        fields = {'rated_kva': 1000, 'rated_voltage_v': 11000, 'rated_current_a': 52.49, 'voltage_convention': 'line_to_line', 'measurement_side': 'primary', 'cooling_type': 'ONAN'}
        thermal = {'rated_top_oil_rise_c': 40, 'oil_time_constant_min': 180, 'loss_ratio': 5, 'oil_exponent': .8}
        config = {**fields, 'thermal_parameters': thermal, 'operational_limits': {'max_top_oil_temp_c': 105}, 'parameter_provenance': {**{key: 'assumed' for key in fields}, **{'thermal_parameters.' + key: 'assumed' for key in thermal}, 'operational_limits.max_top_oil_temp_c': 'assumed'}}
        checked(client.post(f'/api/v1/assets/{asset}/configurations', json=config), 201)
        rules = [{'name': name, 'quantity': quantity, 'unit': unit, 'trigger': trigger, 'recovery': recovery, 'persistence_s': 180, 'recovery_s': 120, 'severity': 'warning'} for name, quantity, unit, trigger, recovery in [('synthetic-overload', 'electrical_metrics.capacity_loading_pct', '%', 120, 100), ('synthetic-thermal', 'thermal_assessment.measured_top_oil_temperature_c', 'C', 50, 40)]]
        control = {'schema_version': 'incident-control-1.0.0', 'expected_version': 0, 'idempotency_key': str(uuid4()), 'source': data['source'], 'run_id': data['run_id'], 'configuration_version': 1, 'model_version': MODEL_VERSION, 'detector_version': 'sustained-threshold-1.0.1', 'reason': 'Labelled synthetic browser verification; not physical calibration', 'policy': {'version': 'd-synthetic-browser-v1', 'provenance': 'assumed', 'max_gap_s': 300, 'rules': rules}}
        checked(client.post(f'/api/v1/assets/{asset}/detector-handovers', json=control, headers={'Authorization': 'Bearer ' + token}), 201)
        data['reading_ids'] = []
        start = datetime.now(timezone.utc) - timedelta(minutes=10)
        for seconds in (0, 180, 240):
            packet = {'schema_version': '1.0.0', 'asset_id': asset, 'source': data['source'], 'run_id': data['run_id'], 'configuration_version': 1, 'message_id': str(uuid4()), 'timestamp': (start + timedelta(seconds=seconds)).isoformat(), 'measurements': {**{f'voltage_{p}_v': 11000 for p in 'ryb'}, **{f'current_{p}_a': 52.49 * 1.5 for p in 'ryb'}, 'oil_temperature_c': 55, 'ambient_temperature_c': 30}}
            receipt = checked(client.post('/api/v1/telemetry', json=packet), 201)
            checked(client.post('/api/v1/telemetry', json=packet), 200)
            assert run_once(factory)
            data['reading_ids'].append(receipt['id'])
        incidents = checked(client.get('/api/v1/incidents', params={'asset_id': asset, 'source': data['source'], 'run_id': data['run_id']}, headers={'Authorization': 'Bearer ' + token}))
        assert len(incidents['items']) == 2
        data['incident_ids'] = [item['incident_id'] for item in incidents['items']]
        data['checks'] += ['persisted current-model worker results', 'two persisted synthetic-policy incidents', 'duplicate telemetry receipts']
        for index in range(21):
            task = checked(client.post('/api/v1/maintenance/tasks', json={'alert': {'source': 'sample', 'alert_id': f'sample-d-{index}', 'asset_id': asset, 'summary': 'Labelled synthetic pagination sample'}, 'action': f'D sample pagination task {index}', 'owner': 'QA display label'}), 201)
            data['sample_task_ids'].append(task['id'])
        data['history_task_id'] = data['sample_task_ids'][0]
        for version in range(1, 22):
            checked(client.patch('/api/v1/maintenance/tasks/' + data['history_task_id'], json={'expected_version': version, 'owner': 'QA display label ' + str(version)}, headers={'X-Demo-Actor': 'D isolated sample verifier'}))
        data['checks'] += ['21 persisted sample tasks', '22 history entries on one sample task']
        checked(client.get('/health/ready'))
    engine.dispose()
    Path(output).write_text(json.dumps(data, indent=2) + '\n')
    print('PASS: labelled isolated UI fixtures; identifiers in private review evidence, no credentials logged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('base', 'database-url', 'token-file', 'output'):
        parser.add_argument('--' + arg, required=True)
    args = parser.parse_args()
    prepare(args.base, args.database_url, args.token_file, args.output)
