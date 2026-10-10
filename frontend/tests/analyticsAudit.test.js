import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { adaptReadingAnalytics, adaptLatestAnalytics } from '../src/services/analyticsAdapter.js';

const sample = JSON.parse(readFileSync(new URL('../../data/sample/analytics-worker-result.json', import.meta.url)));
const fields = ['model_id', 'model_version', 'parameter_version'];
function latest(reading) {
  return {schema_version:'1.0.0', asset_id:reading.asset_id, source:reading.source,
    run_id:reading.run_id, latest_telemetry_reading_id:reading.reading_id,
    latest_telemetry_measurement_time:reading.measurement_time, latest_telemetry_status:reading.status,
    latest_completed_reading_id:reading.reading_id,
    latest_completed_measurement_time:reading.measurement_time, result:reading.result};
}

test('per-reading results reject conflicting payload model and parameter references', () => {
  for (const field of fields) {
    for (const side of ['metadata', 'result']) {
      const wire = structuredClone(sample);
      const target = side === 'metadata' ? wire.result.payload.metadata : wire.result;
      target[field] = `contradictory-${field}`;
      assert.throws(() => adaptReadingAnalytics(wire), /model or parameter identity/, `${side}.${field}`);
    }
  }
});

test('latest-completed results reject conflicting payload model and parameter references', () => {
  for (const field of fields) {
    const wire = latest(structuredClone(sample));
    wire.result.payload.metadata[field] = `contradictory-${field}`;
    assert.throws(() => adaptLatestAnalytics(wire), /model or parameter identity/, field);
  }
});

test('matching provenance and absent results remain usable; missing result identity fails closed', () => {
  const future = structuredClone(sample);
  for (const field of fields) {
    future.result[field] = `matching-future-${field}`;
    future.result.payload.metadata[field] = future.result[field];
  }
  assert.equal(adaptReadingAnalytics(future).metrics[0].value, sample.result.payload.electrical_metrics.capacity_loading_pct);
  assert.equal(adaptLatestAnalytics(latest(future)).result, future.result);
  assert.deepEqual(adaptReadingAnalytics({...sample, status:'pending', result:null}).metrics, []);
  assert.equal(adaptLatestAnalytics({...latest(sample), result:null, latest_completed_reading_id:null}).result, null);
  for (const field of fields) {
    const wire = structuredClone(sample);
    delete wire.result.payload.metadata[field];
    assert.throws(() => adaptReadingAnalytics(wire), /model or parameter identity/);
    assert.throws(() => adaptLatestAnalytics(latest(wire)), /model or parameter identity/);
  }
});
