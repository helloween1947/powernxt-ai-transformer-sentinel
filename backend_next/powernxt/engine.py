"""Pure electrical calculations and explainable configured-condition checks.
These checks identify observed operating conditions, not root-cause diagnoses.
"""
import math
from .schemas import CHANNELS

MODEL = 'powernxt-configured-condition'
VERSION = '1.0.0'
UNITS = {'capacity_loading_pct': '%', 'phase_loading_pct': '%',
         'apparent_power_kva': 'kVA', 'thermal_load_pu': 'pu',
         'magnitude_imbalance': '%', 'oil_temperature': 'C', 'thermal_residual': 'C'}

def imbalance(values):
    mean = sum(values) / len(values)
    return max(abs(v - mean) for v in values) / mean * 100 if mean > 0 else 0

def assess(measurements, configuration):
    rated_current = configuration['rated_current_a']
    voltage = [measurements[f'voltage_{p}_v'] for p in 'ryb']
    current = [measurements[f'current_{p}_a'] for p in 'ryb']
    electrical = dict.fromkeys(['capacity_loading_pct', 'max_phase_loading_pct', 'apparent_power_kva', 'thermal_load_pu', 'current_magnitude_imbalance_pct', 'voltage_magnitude_imbalance_pct'])
    if all(v is not None for v in current):
        electrical.update(max_phase_loading_pct=max(current) / rated_current * 100,
                          thermal_load_pu=math.sqrt(sum(v*v for v in current)/3) / rated_current,
                          current_magnitude_imbalance_pct=imbalance(current))
    if all(v is not None for v in voltage):
        electrical['voltage_magnitude_imbalance_pct'] = imbalance(voltage)
    if all(v is not None for v in voltage + current):
        kva = math.sqrt(3) * sum(voltage)/3 * sum(current)/3 / 1000
        electrical.update(apparent_power_kva=kva, capacity_loading_pct=kva/configuration['rated_kva']*100)
    limits = configuration['operational_limits']
    observations = []
    def check(code, quantity, value, threshold, unit, relation, advice):
        available = value is not None
        breached = (value > threshold if relation == 'gt' else value < threshold) if available else None
        observations.append({'code': code, 'kind': 'configured_limit_check', 'quantity': quantity,
            'value': value, 'threshold': threshold, 'unit': unit, 'relation': relation,
            'breached': breached, 'status': 'available' if available else 'unavailable',
            'reasons': [] if available else ['missing_required_channel'],
            'interpretation': advice})
    check('overload', 'capacity_loading_pct', electrical.get('capacity_loading_pct'), limits['max_load_pct'], '%', 'gt', 'Loading exceeds the configured capacity limit; review load and rating.')
    check('overheating', 'measured_top_oil_temperature_c', measurements['oil_temperature_c'], limits['max_top_oil_temp_c'], 'C', 'gt', 'Oil temperature exceeds the configured limit; inspect loading and cooling.')
    check('low_oil', 'oil_level_pct', measurements['oil_level_pct'], limits['min_oil_level_pct'], '%', 'lt', 'Oil level is below the configured minimum; inspect level sensing and possible leakage.')
    check('phase_imbalance', 'current_magnitude_imbalance_pct', electrical.get('current_magnitude_imbalance_pct'), limits['max_current_imbalance_pct'], '%', 'gt', 'Current magnitudes differ excessively; inspect phase loading. Phase angles are not available.')
    for p, value in zip('ryb', voltage):
        pu = value / configuration['rated_voltage_v'] if value is not None else None
        check('undervoltage', f'voltage_{p}_pu', pu, limits['min_voltage_pu'], 'pu', 'lt', 'Phase voltage is below its configured lower limit.')
        check('overvoltage', f'voltage_{p}_pu', pu, limits['max_voltage_pu'], 'pu', 'gt', 'Phase voltage is above its configured upper limit.')
    return electrical, observations

def result_for(reading, configuration, previous=None):
    """Build the frontend's stored-result envelope with explicit provenance."""
    m = reading['normalized_telemetry']['measurements']
    electrical, observations = assess(m, configuration)
    predicted = None
    elapsed = None
    # Use previous observed oil as initial condition and a first-order thermal response.
    # This estimate is deliberately separate from direct measured-temperature checks.
    if previous is not None and m['ambient_temperature_c'] is not None and electrical.get('thermal_load_pu') is not None:
        from datetime import datetime
        elapsed = (datetime.fromisoformat(reading['measurement_time']) - datetime.fromisoformat(previous['measurement_time'])).total_seconds()
        old_oil = previous['normalized_telemetry']['measurements']['oil_temperature_c']
        if old_oil is not None and elapsed > 0:
            target = m['ambient_temperature_c'] + configuration['rated_top_oil_rise_c'] * electrical['thermal_load_pu']**1.6
            predicted = old_oil + (target-old_oil) * -math.expm1(-elapsed/configuration['oil_time_constant_s'])
    thermal = {'predicted_top_oil_temperature_c': predicted,
               'measured_top_oil_temperature_c': m['oil_temperature_c'],
               'thermal_residual_c': m['oil_temperature_c'] - predicted if m['oil_temperature_c'] is not None and predicted is not None else None,
               'elapsed_s': elapsed, 'prediction_source': 'estimated'}
    availability = {f'{group}.{key}': {'status': 'available' if value is not None else 'unavailable', 'reasons': [] if value is not None else ['insufficient_inputs']}
                    for group, values in [('electrical_metrics', electrical), ('thermal_assessment', thermal)]
                    for key, value in values.items() if key != 'prediction_source'}
    parameter_version = f"asset-config-{reading['configuration_version']}"
    metadata = {'model_id': MODEL, 'model_version': VERSION, 'parameter_version': parameter_version,
        'result_schema_version': 'stored-reading-result-1.1.0', 'configuration_version': reading['configuration_version'],
        'stream': {key: reading[key] for key in ['asset_id', 'source', 'run_id']},
        'measurement_time': reading['measurement_time'], 'measurement_source': reading['source'],
        'reading_identity': {'reading_id': reading['id'], 'message_id': reading['message_id']}, 'units': UNITS,
        'parameter_provenance': configuration['parameter_provenance']}
    payload = {'metadata': metadata, 'electrical_metrics': electrical, 'thermal_assessment': thermal,
        'condition_contributors': {'status': 'not_assessed', 'health_index': None},
        'data_confidence': {'status': 'not_estimated', 'score': None,
            'usable_required_channel_count': sum(m[c] is not None for c in CHANNELS), 'required_channel_count': len(CHANNELS)},
        'anomaly_observations': observations, 'execution_status': {'status': 'computed', 'availability': availability}}
    result = {'id': reading['id'], 'reading_id': reading['id'], 'model_id': MODEL, 'model_version': VERSION,
        'parameter_version': parameter_version, 'schema_version': 'stored-reading-result-1.1.0',
        'status': 'completed', 'payload': payload, 'created_at': reading['arrival_time']}
    return {'schema_version': '1.0.0', 'reading_id': reading['id'], 'configuration_version': reading['configuration_version'],
        **metadata['stream'], 'measurement_time': reading['measurement_time'], 'status': 'completed', 'result': result}
