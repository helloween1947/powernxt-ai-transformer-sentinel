import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { conditionRating } from '../src/domain/conditionRating.js';
import { capabilities, anchors, resolveMetrics, calloutMetrics } from '../src/data/capabilities.js';
import { sampleAssets, sampleSnapshot } from '../src/data/workstationSample.js';
import { benchMeasurements, tripEvidence } from '../src/data/workbookEvidence.js';
import { csvCell, exportRows, reportCsv } from '../src/services/reportExport.js';
import { adaptReadingAnalytics, adaptLatestAnalytics } from '../src/services/analyticsAdapter.js';
import { adaptTelemetryReading, usableMeasurement } from '../src/services/telemetryAdapter.js';
import { createTelemetryClient } from '../src/services/telemetryClient.js';
import { loadStreamSnapshot, thermalPoints } from '../src/services/storedStream.js';

const example = JSON.parse(readFileSync(new URL('./fixtures/analytics-worker-result.json', import.meta.url)));
const telemetry = JSON.parse(readFileSync(new URL('../src/data/telemetryResponseSample.json', import.meta.url)));
const select = id => resolveMetrics(sampleSnapshot(sampleAssets[0].asset_id), 'sample').find(metric => metric.id === id);

test('capabilities have unique IDs, exact known units and stable semantic anchors', () => {
  assert.equal(new Set(capabilities.map(metric => metric.id)).size, capabilities.length);
  for (const metric of capabilities.filter(metric => metric.anchor)) assert.ok(anchors[metric.anchor]);
  for (const anchor of Object.values(anchors)) assert.ok(anchor.position.length === 3 && anchor.position.every(Number.isFinite));
  assert.equal(select('rated_capacity').unit, 'kVA');
  assert.equal(select('oil_temperature_c').unit, '°C');
});
test('sample values stay sample and future metrics remain unavailable in either workspace', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01');
  for (const mode of ['sample', 'live']) {
    for (const metric of resolveMetrics(snapshot, mode).filter(metric => metric.type === 'future')) {
      assert.equal(metric.value, null);
      assert.ok(['Planned', 'Unsupported'].includes(metric.state));
      assert.ok(metric.reason.length > 10);
    }
  }
  assert.ok(resolveMetrics(snapshot, 'sample').filter(metric => metric.value != null).every(metric => metric.state === 'Sample'));
  assert.equal(snapshot.analytics.result, null);
  assert.equal(snapshot.latest.arrivalTime, null);
  assert.equal(snapshot.latest.measurementTime, '2026-10-09T12:30:00.000Z');
});
test('missing readings and model outputs do not become healthy zeros', () => {
  for (const metric of resolveMetrics(null, 'live').filter(metric => metric.type !== 'future')) {
    assert.equal(metric.value, null); assert.equal(metric.state, 'Unavailable');
  }
  const snapshot = sampleSnapshot('SAMPLE-TX-01', 'missing');
  const oil = resolveMetrics(snapshot, 'sample').find(metric => metric.id === 'oil_temperature_c');
  assert.equal(oil.value, null); assert.equal(oil.state, 'Unavailable');
  assert.equal(snapshot.points.at(-1).measured, null);
  assert.equal(select('oil_leak').value, null);
});
test('genuine zero is preserved, bad/sanity-failed channels are withheld, suspect values retain quality', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01');
  snapshot.latest.measurements.oil_temperature_c = 0;
  assert.equal(resolveMetrics(snapshot)[11].value, 0);
  snapshot.latest.measurementQuality.oil_temperature_c = 'bad';
  assert.equal(resolveMetrics(snapshot)[11].value, null);
  snapshot.latest.measurementQuality.oil_temperature_c = 'suspect';
  assert.equal(resolveMetrics(snapshot)[11].value, 0);
  assert.equal(resolveMetrics(snapshot)[11].quality, 'suspect');
  snapshot.latest.qualityFlags.oil_temperature_c = ['outside_sanity_range'];
  assert.equal(usableMeasurement(snapshot.latest, 'oil_temperature_c'), null);
});
test('derived values require the descriptor unit and configured capacity is never replaced by a default', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01');
  snapshot.analytics.metrics.find(metric => metric.path.endsWith('apparent_power_kva')).unit = 'kW';
  delete snapshot.details.current_configuration.rated_kva;
  const metrics = resolveMetrics(snapshot);
  assert.equal(metrics.find(metric => metric.id === 'apparent_power').value, null);
  assert.equal(metrics.find(metric => metric.id === 'rated_capacity').value, null);
});
test('mobile callout filter exposes at most two values and desktop maps every metric to an existing region', () => {
  const metrics = resolveMetrics(sampleSnapshot('SAMPLE-TX-01'), 'sample');
  for (const category of ['All', 'Electrical', 'Thermal', 'Condition']) {
    assert.ok(calloutMetrics(metrics, category, true).length <= 2);
    for (const metric of calloutMetrics(metrics, category)) assert.ok(anchors[metric.anchor]);
  }
  assert.deepEqual(calloutMetrics(metrics, 'Condition').map(metric => metric.id), ['oil_level_pct', 'oil_temperature_c']);
});
test('benchmark values use reference minus software while trip tests have the opposite sign', () => {
  assert.equal(benchMeasurements.length, 6);
  assert.ok(benchMeasurements.every(item => item.withinTolerance && item.difference < 0));
  assert.ok(Math.abs(benchMeasurements[0].difference + 0.13) < 1e-10);
  assert.ok(Math.abs(benchMeasurements[0].percent + 0.2610966057) < 1e-6);
  assert.equal(tripEvidence.current[0].software - tripEvidence.current[0].reference > 0, true);
  assert.ok(!('timestamp' in benchMeasurements[0]));
});
test('CSV quotes commas, quotes and newlines and neutralizes formulas without changing numeric signs', () => {
  assert.equal(csvCell('a,"b"\nc'), '"a,""b""\nc"');
  for (const value of ['=HYPERLINK("x")', '+1', '-cmd', '@SUM(1)', ' =1', '\t=1']) assert.ok(csvCell(value).startsWith('"\''));
  assert.equal(csvCell(-1.25), '"-1.25"'); assert.equal(csvCell(null), '""');
});
test('reports export only the retrieved page and retain stream, units, gaps and per-reading provenance', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01', 'missing');
  snapshot.history = snapshot.history.slice(-2);
  snapshot.page.offset = 20;
  const rows = exportRows(snapshot, 'sample');
  assert.equal(rows.length, 2); assert.equal(rows[0].asset_id, 'SAMPLE-TX-01');
  assert.equal(rows[0].run_id, 'ui-illustration'); assert.equal(rows[0].oil_temperature_c, null);
  assert.equal(rows[0].scope, 'Sample UI illustration');
  assert.equal(rows[0].analytics_model_version, '');
  assert.ok(reportCsv(snapshot, 'sample').includes('"oil_temperature_c"'));
  assert.equal(reportCsv({ history: [] }, 'live'), null);
});
test('contradictory model, parameter or schema provenance fails at both envelope adapters', () => {
  for (const key of ['model_id', 'model_version', 'parameter_version', 'result_schema_version']) {
    const copy = structuredClone(example); copy.result.payload.metadata[key] = 'contradiction';
    assert.throws(() => adaptReadingAnalytics(copy), /provenance/);
    assert.throws(() => adaptLatestAnalytics({ schema_version: '1.0.0', latest_completed_reading_id: copy.reading_id, result: copy.result }), /provenance/);
  }
});
test('latest analytics result cannot claim another asset, run or measurement time', () => {
  const latest = { schema_version: '1.0.0', asset_id: example.asset_id, source: example.source, run_id: example.run_id, latest_completed_reading_id: example.reading_id, latest_completed_measurement_time: example.measurement_time, result: example.result };
  assert.equal(adaptLatestAnalytics(latest).result.model_version, example.result.model_version);
  assert.throws(() => adaptLatestAnalytics({ ...latest, run_id: 'other' }), /metadata/);
  assert.throws(() => adaptLatestAnalytics({ ...latest, asset_id: 'other' }), /metadata/);
});
test('telemetry validates normalized envelope identity and unsupported schemas', () => {
  for (const key of ['asset_id', 'source', 'run_id', 'configuration_version', 'message_id', 'timestamp']) {
    const copy = structuredClone(telemetry); copy.normalized_telemetry[key] = 'different';
    assert.throws(() => adaptTelemetryReading(copy), /identity/);
  }
  assert.throws(() => adaptTelemetryReading({ ...telemetry, normalized_telemetry: { ...telemetry.normalized_telemetry, schema_version: '2' } }), /schema/);
});
test('history date filters and page scope are passed to the canonical API, malformed pages are rejected', async () => {
  let captured;
  const client = createTelemetryClient('http://example.test', async url => {
    captured = url; return { ok: true, json: async () => ({ items: [], limit: 20, offset: 40 }) };
  });
  await client.getTelemetryHistory('asset', { source: 'file_replay', runId: 'run', offset: 40, start: '2026-01-01T00:00:00Z', end: '2026-01-02T00:00:00Z' });
  assert.equal(captured.searchParams.get('start'), '2026-01-01T00:00:00Z');
  assert.equal(captured.searchParams.get('end'), '2026-01-02T00:00:00Z');
  await assert.rejects(client.getTelemetryHistory('asset'), /inconsistent page/);
});
test('a missing latest-analytics route keeps genuine telemetry and prevents per-reading request storms', async () => {
  const reading = adaptTelemetryReading(telemetry);
  let individual = 0;
  const client = {
    getAssetDetails: async () => ({ asset_id: reading.assetId }),
    getLatestTelemetry: async () => reading,
    getTelemetryHistory: async () => ({ items: [reading], offset: 0, limit: 20 }),
    getLatestAnalytics: async () => { const error = new Error('404'); error.status = 404; throw error; },
    getReadingAnalytics: async () => { individual++; },
  };
  const snapshot = await loadStreamSnapshot(client, { assetId: reading.assetId, source: reading.source, runId: null }, new AbortController().signal);
  assert.equal(snapshot.latest.readingId, 123); assert.equal(snapshot.analytics, null);
  assert.equal(individual, 0); assert.equal(snapshot.errors.length, 1);
});
test('bad measured oil is a chart gap while source quality and analytics provenance remain available', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01');
  const reading = snapshot.latest; reading.measurementQuality.oil_temperature_c = 'bad';
  const point = thermalPoints([reading], [])[0]; assert.equal(point.measured, null);
});

test('runtime disabling of analytics performs no optional latest or per-reading request', async () => {
  const reading = adaptTelemetryReading(telemetry); let requests = 0;
  const client = { supportsAnalytics: false,
    getAssetDetails: async () => ({ asset_id: reading.assetId }), getLatestTelemetry: async () => reading,
    getTelemetryHistory: async () => ({ items: [reading], offset: 0, limit: 20 }),
    getLatestAnalytics: async () => { requests++; }, getReadingAnalytics: async () => { requests++; },
  };
  const snapshot = await loadStreamSnapshot(client, { assetId: reading.assetId, source: reading.source, runId: null }, new AbortController().signal);
  assert.equal(requests, 0); assert.equal(snapshot.analytics, null); assert.equal(snapshot.points[0].predicted, null);
  assert.equal(snapshot.points[0].measured, reading.measurements.oil_temperature_c);
});

test('telemetry transport delay preserves zero and rejects reversed clocks without becoming sensor response time', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01');
  const latency = () => resolveMetrics(snapshot, 'live').find(item => item.id === 'telemetry_latency');
  assert.equal(latency().value, null);
  snapshot.latest.arrivalTime = snapshot.latest.measurementTime;
  assert.equal(latency().value, 0); assert.equal(latency().state, 'Derived');
  snapshot.latest.arrivalTime = new Date(Date.parse(snapshot.latest.measurementTime) + 3500).toISOString();
  assert.equal(latency().value, 3.5); assert.equal(latency().unit, 's');
  snapshot.latest.arrivalTime = new Date(Date.parse(snapshot.latest.measurementTime) - 1).toISOString();
  assert.equal(latency().value, null);
  assert.equal(resolveMetrics(snapshot, 'live').find(item => item.id === 'response_time').value, null);
  assert.equal(resolveMetrics(snapshot, 'live').find(item => item.id === 'processing_duration').value, null);
});

 test('rating parameter display binds to its mode and inspected identity without replacing authoritative health', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01'); const assessment = conditionRating(snapshot, 'sample');
  const metric = (mode, rating) => resolveMetrics(snapshot, mode, rating).find(item => item.id === 'condition_rating');
  assert.equal(metric('sample', assessment).value, 100); assert.equal(metric('sample', assessment).state, 'Sample');
  assert.equal(metric('live', assessment).value, null);
  assert.equal(metric('sample', { ...assessment, identity: { ...assessment.identity, readingId: 'other' } }).value, null);
  assert.equal(resolveMetrics(snapshot, 'sample', assessment).find(item => item.id === 'health').value, null);
});
