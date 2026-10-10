import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { adaptReadingAnalytics, adaptLatestAnalytics } from '../src/services/analyticsAdapter.js';
import { loadStreamSnapshot } from '../src/services/storedStream.js';

const sample = JSON.parse(readFileSync(new URL('../../data/sample/analytics-worker-result.json', import.meta.url)));
const fields = ['model_id', 'model_version', 'parameter_version'];

test('labelled 1.0.1/1.0.2 fixtures preserve provenance and independent metrics when arithmetic is unavailable', () => {
  for (const version of ['stored-reading-top-oil-1.0.1','stored-reading-top-oil-1.0.2']) {
    const wire=structuredClone(sample);
    wire.result.model_version=wire.result.payload.metadata.model_version=version;
    const path='electrical_metrics.capacity_loading_pct';
    wire.result.payload.electrical_metrics.capacity_loading_pct=null;
    wire.result.payload.execution_status.availability[path]={status:'unavailable',reasons:['electrical_arithmetic_unavailable']};
    const adapted=adaptReadingAnalytics(wire);
    assert.equal(adaptLatestAnalytics(latest(wire)).result.model_version,version);
    const gap=adapted.metrics.find(m=>m.path===path);
    assert.equal(gap.value,null);assert.ok(gap.reasons.includes('electrical_arithmetic_unavailable'));
    assert.ok(Number.isFinite(adapted.metrics.find(m=>m.path==='electrical_metrics.apparent_power_kva').value));
    assert.equal(adapted.result.parameter_version,wire.result.payload.metadata.parameter_version);
  }
});
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

test('both adapters reject absent, blank or non-string outer identities even when metadata agrees', () => {
  for (const field of fields) {
    for (const value of [undefined, null, '', ' \t ', 42]) {
      const wire = structuredClone(sample);
      wire.result[field] = value;
      wire.result.payload.metadata[field] = value;
      assert.throws(() => adaptReadingAnalytics(wire), /model or parameter identity/);
      assert.throws(() => adaptLatestAnalytics(latest(wire)), /model or parameter identity/);
    }
  }
});

test('both adapters fail closed when a non-null result has no provenance container', () => {
  for (const mutate of [wire => { wire.result.payload = null; }, wire => { delete wire.result.payload.metadata; }]) {
    const wire = structuredClone(sample);
    mutate(wire);
    assert.throws(() => adaptReadingAnalytics(wire), /model or parameter identity/);
    assert.throws(() => adaptLatestAnalytics(latest(wire)), /model or parameter identity/);
  }
});

test('rejected reading/latest identities replace stale analytics while retaining usable telemetry', async () => {
  const reference = {readingId:sample.reading_id,assetId:sample.asset_id,source:sample.source,runId:sample.run_id,
    configurationVersion:sample.configuration_version,measurementTime:sample.measurement_time,
    measurements:{oil_temperature_c:44}};
  const selection = {assetId:sample.asset_id,source:sample.source,runId:sample.run_id};
  let badReading = false, badLatest = false;
  function wire(invalid) {
    const value = structuredClone(sample);
    if (invalid) value.result.payload.metadata.model_version = 'labelled-invalid-fixture';
    return value;
  }
  const client = {
    getAssetDetails:async () => ({asset_id:sample.asset_id}),
    getLatestTelemetry:async () => reference,
    getTelemetryHistory:async () => ({items:[reference],limit:20,offset:0}),
    getReadingAnalytics:async () => adaptReadingAnalytics(wire(badReading)),
    getLatestAnalytics:async () => adaptLatestAnalytics(latest(wire(badLatest))),
  };
  const load = () => loadStreamSnapshot(client,selection,new AbortController().signal);
  assert.ok((await load()).analytics.result);
  badReading = true;
  const rejected = await load();
  assert.equal(rejected.latest,reference);
  assert.equal(rejected.analytics,null);
  assert.equal(rejected.completedAnalytics,null);
  assert.equal(rejected.points[0].measured,44);
  assert.equal(rejected.points[0].predicted,null);
  assert.equal(rejected.points[0].residual,null);
  assert.match(rejected.errors.join(' '), /model or parameter identity/);
  badReading = false; badLatest = true;
  const rejectedLatest = await load();
  assert.equal(rejectedLatest.latest,reference);
  assert.equal(rejectedLatest.latestEnvelope,null);
  assert.equal(rejectedLatest.completedAnalytics,null);
  assert.ok(rejectedLatest.analytics.result); // Independent valid per-reading response remains usable.
  badLatest = false;
  assert.equal((await load()).errors.length,0);
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
