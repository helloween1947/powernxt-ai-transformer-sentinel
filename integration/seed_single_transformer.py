"""Seed one deterministic synthetic transformer via supported APIs in the owned stack."""
import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from uuid import UUID, uuid5, NAMESPACE_URL
import hashlib
from sqlalchemy import select, func
from backend.app.db.session import engine, SessionLocal
from backend.app.models.assets import Asset
from backend.app.analytics.adapter import MODEL_VERSION

ASSET = 'powernxt-single-transformer'
RUN = 'single-transformer-demo-v1'

def request(base, route, payload=None, token=None, expected=(200,)):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(base + route, data=None if payload is None else json.dumps(payload, allow_nan=False).encode(), headers=headers)
    try:
        with urlopen(req, timeout=15) as response:
            assert response.status in expected, (route, response.status)
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f'{route}: HTTP {error.code}: {error.read().decode()}') from None

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://localhost:8000')
    parser.add_argument('--token-file', default='/evidence/private/admin.txt')
    parser.add_argument('--output', default='/evidence/seed.json')
    args = parser.parse_args()
    assert engine.url.host == 'db' and engine.url.database == 'single_transformer_app_test', 'Owned application database required'
    with SessionLocal() as db:
        asset_ids = list(db.scalars(select(Asset.asset_id)))
    assert asset_ids in ([], [ASSET]), 'Refusing to seed a database containing another transformer'
    token = Path(args.token_file).read_text().strip()
    if not asset_ids:
        request(args.base, '/api/v1/assets', {'asset_id': ASSET, 'name': 'PowerNXT synthetic transformer', 'location': 'Isolated demonstration laboratory', 'timezone': 'Asia/Kolkata'}, expected=(201,))
        fields = {'rated_kva': 1000, 'rated_voltage_v': 11000, 'rated_current_a': 52.49, 'voltage_convention': 'line_to_line', 'measurement_side': 'primary', 'cooling_type': 'ONAN'}
        thermal = {'rated_top_oil_rise_c': 40, 'oil_time_constant_min': 180, 'loss_ratio': 5, 'oil_exponent': .8}
        config = {**fields, 'thermal_parameters': thermal, 'operational_limits': {'max_top_oil_temp_c': 105}, 'parameter_provenance': {**{key: 'assumed' for key in fields}, **{'thermal_parameters.' + key: 'assumed' for key in thermal}, 'operational_limits.max_top_oil_temp_c': 'assumed'}}
        created = request(args.base, f'/api/v1/assets/{ASSET}/configurations', config, expected=(201,))
        assert created['version'] == 1
        rules = [{'name': name, 'quantity': quantity, 'unit': unit, 'trigger': trigger, 'recovery': recovery, 'persistence_s': 180, 'recovery_s': 120, 'severity': 'warning'} for name, quantity, unit, trigger, recovery in [('synthetic-overload', 'electrical_metrics.capacity_loading_pct', '%', 120, 100), ('synthetic-thermal', 'thermal_assessment.measured_top_oil_temperature_c', 'C', 50, 40)]]
        request(args.base, f'/api/v1/assets/{ASSET}/detector-handovers', {'schema_version': 'incident-control-1.0.0', 'expected_version': 0, 'idempotency_key': str(uuid5(NAMESPACE_URL, RUN + '-control')), 'source': 'simulator', 'run_id': RUN, 'configuration_version': 1, 'model_version': MODEL_VERSION, 'detector_version': 'sustained-threshold-1.0.1', 'reason': 'Deterministic synthetic application demonstration, assumed policy, no physical calibration', 'policy': {'version': 'single-synthetic-v1', 'provenance': 'assumed', 'max_gap_s': 300, 'rules': rules}}, token, (201,))
    packets = []
    readings = []
    for index in range(6):
        packet = {'schema_version': '1.0.0', 'asset_id': ASSET, 'source': 'simulator', 'run_id': RUN, 'configuration_version': 1, 'message_id': str(UUID(bytes=hashlib.sha256((RUN + str(index)).encode()).digest()[:16], version=4)), 'timestamp': f'2026-10-10T12:0{index}:00Z', 'measurements': {**{f'voltage_{p}_v': 11000 for p in 'ryb'}, **{f'current_{p}_a': 52.49 * 1.5 for p in 'ryb'}, 'oil_temperature_c': 55, 'ambient_temperature_c': 30}}
        packets.append(packet)
        readings.append(request(args.base, '/api/v1/telemetry', packet, expected=(200, 201)))
    results = []
    for reading in readings:
        deadline = time.monotonic() + 60
        while True:
            result = request(args.base, f"/api/v1/telemetry/{reading['id']}/analytics")
            if result['status'] in ('completed', 'unavailable', 'failed'):
                assert result['status'] == 'completed', result
                results.append(result)
                break
            assert time.monotonic() < deadline, 'Worker completion timed out'
            time.sleep(.25)
    results.sort(key=lambda value: value['measurement_time'])
    for index, result in enumerate(results):
        assert result['asset_id'] == ASSET and result['run_id'] == RUN and result['configuration_version'] == 1
        thermal = result['result']['payload']['thermal_assessment']
        if index == 0:
            assert thermal['initial_condition'] is not None and thermal['predicted_top_oil_temperature_c'] is None and thermal['thermal_residual_c'] is None
        else:
            import math
            assert thermal['elapsed_s'] == 60
            assert math.isfinite(thermal['predicted_top_oil_temperature_c']) and math.isfinite(thermal['thermal_residual_c'])
            assert abs(thermal['thermal_residual_c'] - (55 - thermal['predicted_top_oil_temperature_c'])) < 1e-9
    incidents = request(args.base, f'/api/v1/incidents?asset_id={ASSET}&source=simulator&run_id={RUN}', token=token)
    assert len(incidents['items']) == 2 and all(item['asset_id'] == ASSET for item in incidents['items'])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    history = request(args.base, f'/api/v1/assets/{ASSET}/configurations?limit=100&offset=0')
    config = next(item for item in history['items'] if item['version'] == 1)
    report = {'status': 'PASS', 'asset_id': ASSET, 'source': 'simulator', 'run_id': RUN, 'configuration_version': 1, 'model_version': MODEL_VERSION, 'reading_ids': [r['id'] for r in readings], 'incident_ids': [r['incident_id'] for r in incidents['items']], 'synthetic': True, 'assumed_coefficients': True}
    output.write_text(json.dumps(report, indent=2) + '\n')
    (output.parent / 'packets.jsonl').write_text(''.join(json.dumps(p, allow_nan=False) + '\n' for p in packets))
    (output.parent / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    (output.parent / 'configuration.json').write_text(json.dumps(config, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
