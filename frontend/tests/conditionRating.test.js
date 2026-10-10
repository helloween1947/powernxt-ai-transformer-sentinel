import test from 'node:test';
import assert from 'node:assert/strict';
import { CONDITION_POLICY, classifyFactor, computeConditionRating, conditionRating } from '../src/domain/conditionRating.js';
import { sampleSnapshot } from '../src/data/workstationSample.js';
import { inspectHistoryRecord, metricTrend } from '../src/domain/inspection.js';
import { inspectRuntimeContract, discoverRuntimeContract } from '../src/services/runtimeContract.js';
const now = Date.parse('2026-10-10T12:00:00Z');
const identity = { assetId: 'TX-1', source: 'device', runId: null, readingId: 1, configurationVersion: 1, measurementTime: new Date(now).toISOString() };
const factor = (id, overrides = {}) => ({ id, label: id, value: 50, unit: CONDITION_POLICY.units[id], limit: 100, relation: 'maximum', quality: 'good', ruleVerified: true, limitProvenance: 'nameplate', identity, ...overrides });
const calculate = (factors, overrides = {}) => computeConditionRating({ factors, identity, now, ...overrides });
test('prototype policy is immutable and maximum/minimum comparisons use documented exact boundaries', () => {
  assert.equal(CONDITION_POLICY.version, 'condition-rating-prototype-v1');
  assert.ok(Object.isFrozen(CONDITION_POLICY.weights));
  for (const id of Object.keys(CONDITION_POLICY.weights)) {
    assert.equal(calculate([factor(id, { value: 90 })]).factors.find(f => f.id === id).classification, 'warning');
    assert.equal(classifyFactor(100, 100), 'warning');
    assert.equal(classifyFactor(100.01, 100), 'critical');
    assert.equal(classifyFactor(89.99, 100), 'normal');
    assert.equal(classifyFactor(100, 100, 'minimum'), 'warning');
    assert.equal(classifyFactor(99.99, 100, 'minimum'), 'critical');
    assert.equal(classifyFactor(112, 100, 'minimum'), 'normal');
  }
  for (const value of [NaN, Infinity, null]) assert.equal(classifyFactor(value, 100), null);
  for (const limit of [0, -1, NaN]) assert.equal(classifyFactor(5, limit), null);
});
test('both minimum factors and coverage gates apply; missing evidence never becomes a healthy zero', () => {
  assert.equal(calculate([]).score, null);
  assert.equal(calculate([factor('loading')]).score, null);
  assert.equal(calculate([factor('oil'), factor('electrical')]).score, null);
  assert.equal(calculate([factor('loading'), factor('oil')]).coverage, 50);
  assert.equal(calculate([factor('loading'), factor('oil')]).score, 100);
  const result = calculate([factor('loading', { value: 0 }), factor('thermal', { value: 0 })]);
  assert.equal(result.coverage, 70); assert.equal(result.score, 100);
});
test('bad, suspect, missing, unverified, malformed units and limits reduce coverage without a physical penalty', () => {
  for (const overrides of [{ quality: 'bad' }, { quality: 'suspect' }, { quality: 'missing' }, { value: null }, { value: NaN }, { unit: 'kW' }, { ruleVerified: false }, { limitProvenance: undefined }, { limitProvenance: 'guessed' }, { limit: 0 }, { relation: 'unknown' }]) {
    const result = calculate([factor('loading'), factor('thermal', overrides)]);
    assert.equal(result.score, null, JSON.stringify(overrides)); assert.equal(result.coverage, 35);
    assert.equal(result.breaches.length, 0); assert.ok(result.factors[1].reason);
  }
});
test('every reading, configuration and stream identity component must agree; duplicates are excluded', () => {
  for (const [key, value] of Object.entries({ assetId: 'other', source: 'simulator', runId: 'other', readingId: 2, configurationVersion: 2, measurementTime: '2026-10-10T11:00:00Z' })) {
    assert.equal(calculate([factor('loading'), factor('thermal', { identity: { ...identity, [key]: value } })]).coverage, 35);
  }
  assert.equal(calculate([factor('loading'), factor('loading'), factor('thermal')]).coverage, 35);
  assert.equal(calculate([factor('loading'), factor('thermal')], { identity: { ...identity, configurationVersion: 0 } }).score, null);
});
test('breaches remain explicit even when aggregation gives a lower indication; scoring is deterministic', () => {
  const inputs = [factor('loading'), factor('thermal'), factor('electrical'), factor('oil', { value: 110 })];
  const result = calculate(inputs);
  assert.equal(result.score, 88.75); assert.equal(result.band, 'Lower indication');
  assert.deepEqual(result.breaches.map(f => f.id), ['oil']);
  assert.deepEqual(calculate(inputs), result);
});
test('device staleness is disclosed, replay retains its source, future timestamps suppress numeric scores', () => {
  const factors = [factor('loading'), factor('thermal')];
  assert.equal(calculate(factors, { now: now + 120000 }).stale, false);
  const stale = calculate(factors, { now: now + 120001 });
  assert.equal(stale.stale, true); assert.equal(stale.score, 100); assert.equal(stale.state, 'Stale evidence');
  const replayIdentity = { ...identity, source: 'file_replay', runId: 'run' };
  assert.equal(calculate(factors.map(f => ({ ...f, identity: replayIdentity })), { identity: replayIdentity, now: now + 500000 }).state, 'Stored simulation / replay');
  const future = calculate(factors, { now: now - 30001 });
  assert.equal(future.score, null); assert.equal(future.band, null); assert.equal(future.state, 'Invalid evidence time');
});
test('sample evidence cannot produce a live rating, and measured thermal input is never substituted by an estimate', () => {
  const sample = sampleSnapshot('SAMPLE-TX-01');
  assert.equal(conditionRating(sample, 'sample', now).score, 100);
  assert.equal(conditionRating(sample, 'live', now).score, null);
  const overload = conditionRating(sampleSnapshot('SAMPLE-TX-01', 'overload'), 'sample', now);
  assert.equal(overload.breaches.length, 2); assert.equal(overload.score, 25);
  const missing = sampleSnapshot('SAMPLE-TX-01', 'missing');
  assert.equal(conditionRating(missing, 'sample', now).score, null);
  sample.details.current_configuration.version = 2;
  assert.equal(conditionRating(sample, 'sample', now).score, null);
});
test('historical selection binds values and rating to the retrieved reading and excludes another stream/page', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01', 'overload');
  const selected = inspectHistoryRecord(snapshot, snapshot.history[0].readingId, 'sample');
  assert.equal(selected.historical, true);
  assert.equal(conditionRating(selected.snapshot, 'sample', now).breaches.length, 0);
  assert.notEqual(selected.snapshot.latest.measurementTime, snapshot.latest.measurementTime);
  assert.equal(inspectHistoryRecord(snapshot, 'not-retrieved', 'sample').historical, false);
  snapshot.history[0].runId = 'other';
  assert.equal(inspectHistoryRecord(snapshot, snapshot.history[0].readingId, 'sample').historical, false);
  assert.equal(metricTrend('oil_level_pct'), 'oil_level'); assert.equal(metricTrend('current_r_a'), 'current');
});
const spec = { openapi: '3.1.0', paths: { '/api/v1/telemetry/{reading_id}/analytics': { get: {} }, '/api/v1/assets/{asset_id}/analytics/latest': { get: {} } } };
test('runtime capability gating requires complete implemented method families, not route names or a version guess', () => {
  assert.equal(inspectRuntimeContract(spec).analytics, true); assert.equal(inspectRuntimeContract(spec).sampleMaintenance, false);
  const partial = structuredClone(spec); delete partial.paths['/api/v1/telemetry/{reading_id}/analytics'].get;
  assert.equal(inspectRuntimeContract(partial).analytics, false);
  assert.equal(inspectRuntimeContract({ openapi: '3.0.2', paths: {} }).analytics, false);
  assert.throws(() => inspectRuntimeContract({ openapi: '2', paths: {} }), /unsupported/);
});
test('contract discovery is bounded, cancellable and reports HTTP failures', async () => {
  const controller = new AbortController(); let captured;
  const result = await discoverRuntimeContract('http://example.test/', controller.signal, async (url, options) => { captured = { url, signal: options.signal }; return { ok: true, json: async () => spec }; });
  assert.equal(captured.url, 'http://example.test/openapi.json'); assert.ok(captured.signal instanceof AbortSignal); assert.equal(result.analytics, true);
  await assert.rejects(discoverRuntimeContract('http://example.test', controller.signal, async () => ({ ok: false, status: 404 })), /404/);
});

test('a thermal breach remains reported even when coverage prevents a numeric rating', () => {
  const result = calculate([factor('thermal', { value: 110 })]);
  assert.equal(result.score, null); assert.equal(result.breaches.length, 1); assert.equal(result.coverage, 35);
});

test('missing reading identity, unsupported sources, source/run conflicts and unknown modes never assess', () => {
  for (const overrides of [{ readingId: null }, { readingId: 0 }, { source: 'unknown' }, { runId: 'device-must-be-null' }]) {
    const id = { ...identity, ...overrides };
    assert.equal(calculate([factor('loading', { identity: id }), factor('thermal', { identity: id })], { identity: id }).score, null);
  }
  assert.equal(calculate([factor('loading'), factor('thermal')], { mode: 'unknown' }).score, null);
});
