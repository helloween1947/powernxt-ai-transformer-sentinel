import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { adaptReadingAnalytics } from '../src/services/analyticsAdapter.js';

const example = JSON.parse(readFileSync(new URL('../../data/sample/analytics-worker-result.json', import.meta.url)));
test('stored sample maps units, separate UTC clocks and exact provenance without converting it to live evidence', () => {
  const actual = adaptReadingAnalytics(example);
  assert.equal(actual.metrics.find(m => m.unit === 'kVA').value, example.result.payload.electrical_metrics.apparent_power_kva);
  assert.equal(actual.metrics.find(m => m.path.endsWith('thermal_residual_c')).value, -0.427633925767438);
  assert.equal(actual.measurement_time, example.measurement_time);
  assert.equal(actual.result.created_at, example.result.created_at);
  assert.deepEqual(actual.result.payload.metadata.parameter_provenance, example.result.payload.metadata.parameter_provenance);
  assert.equal(actual.source, 'simulator');
});
test('pending, retry and failed jobs never invent metrics', () => {
  for (const status of ['pending', 'processing', 'retry', 'failed']) {
    const actual = adaptReadingAnalytics({...example, status, result: null, error_code: 'worker_computation_error'});
    assert.deepEqual(actual.metrics, []);
    assert.equal(actual.status, status);
    assert.equal(actual.error_code, 'worker_computation_error');
  }
});
test('availability gates finite values, preserves genuine zero and bootstrap reasons', () => {
  const copy = structuredClone(example);
  const path = 'thermal_assessment.predicted_top_oil_temperature_c';
  copy.result.payload.execution_status.availability[path] = {status: 'unavailable', reasons: ['initialized_from_measurement_prediction_not_independent']};
  copy.result.payload.electrical_metrics.capacity_loading_pct = 0;
  const actual = adaptReadingAnalytics(copy);
  assert.equal(actual.metrics.find(m => m.path === path).value, null);
  assert.deepEqual(actual.metrics.find(m => m.path === path).reasons, ['initialized_from_measurement_prediction_not_independent']);
  assert.equal(actual.metrics[0].value, 0);
  copy.result.payload.electrical_metrics.capacity_loading_pct = Infinity;
  assert.equal(adaptReadingAnalytics(copy).metrics[0].value, null);
});
test('unsupported wire versions fail visibly', () => {
  assert.throws(() => adaptReadingAnalytics({...example, schema_version: '2'}), /Unsupported/);
  assert.throws(() => adaptReadingAnalytics({...example, result: {...example.result, schema_version: '2'}}), /Unsupported/);
});

test('unavailable stored result retains available electrical evidence without inventing thermal metrics', () => {
  const copy = structuredClone(example);
  copy.status = 'unavailable';
  copy.result.status = 'unavailable';
  for (const path of ['thermal_assessment.predicted_top_oil_temperature_c', 'thermal_assessment.thermal_residual_c']) {
    copy.result.payload.execution_status.availability[path] = {status: 'unavailable', reasons: ['missing_thermal_coefficients']};
  }
  const actual = adaptReadingAnalytics(copy);
  assert.equal(actual.metrics[0].value, example.result.payload.electrical_metrics.capacity_loading_pct);
  assert.equal(actual.metrics.at(-1).value, null);
  assert.deepEqual(actual.metrics.at(-1).reasons, ['missing_thermal_coefficients']);
});
test('mismatched result identity fails visibly', () => {
  assert.throws(() => adaptReadingAnalytics({...example, result: {...example.result, reading_id: 999}}), /different reading/);
});

test('B metadata units drive display; unsupported or missing units cannot become Celsius chart values', () => {
  const copy = structuredClone(example);
  copy.result.payload.metadata.units.oil_temperature = 'F';
  const predicted = adaptReadingAnalytics(copy).metrics.find(m => m.path.endsWith('predicted_top_oil_temperature_c'));
  assert.equal(predicted.unit, 'F'); assert.equal(predicted.value, null);
  assert.ok(predicted.reasons.includes('unsupported_metric_unit'));
  delete copy.result.payload.metadata.units.apparent_power_kva;
  assert.equal(adaptReadingAnalytics(copy).metrics.find(m => m.path.endsWith('apparent_power_kva')).value, null);
});

test('null confidence and not-assessed health stay unavailable; coverage counts are not percentages', () => {
  const result = adaptReadingAnalytics(example);
  assert.equal(result.assessment.health, null); assert.equal(result.assessment.healthStatus, 'not_assessed');
  assert.equal(result.assessment.confidence, null); assert.equal(result.assessment.confidenceStatus, 'not_estimated');
  assert.equal(result.assessment.usableChannels, 8); assert.equal(result.assessment.requiredChannels, 8);
});

test('model metadata must match envelope configuration, UTC measurement time and stream', () => {
  for (const change of [{configuration_version:99}, {measurement_time:'2027-01-01T00:00:00Z'}, {measurement_source:'device'}, {stream:{asset_id:'other',source:'simulator',run_id:example.run_id}}]) {
    const copy=structuredClone(example); Object.assign(copy.result.payload.metadata, change);
    assert.throws(()=>adaptReadingAnalytics(copy), /metadata does not match/);
  }
});
