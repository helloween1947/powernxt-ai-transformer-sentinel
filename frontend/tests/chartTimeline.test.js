import test from 'node:test';
import assert from 'node:assert/strict';
import { nearestChartReading } from '../src/domain/chartTimeline.js';
import { inspectHistoryRecord } from '../src/domain/inspection.js';
import { resolveMetrics } from '../src/data/capabilities.js';
import { sampleSnapshot } from '../src/data/workstationSample.js';
import { conditionRating } from '../src/domain/conditionRating.js';

const record = (readingId, minute, extra = {}) => ({ readingId, timestamp: new Date(Date.parse('2026-10-08T00:00:00Z') + minute * 60000).toISOString(), ...extra });
test('scrubbing snaps by time across irregular intervals, sorts records and clamps either end', () => {
  const points = [record('last', 120), record('middle', 10), record('first', 0)];
  assert.equal(nearestChartReading(points, 0.1).readingId, 'middle');
  assert.equal(nearestChartReading(points, 0.5).readingId, 'middle');
  assert.equal(nearestChartReading(points, 0.9).readingId, 'last');
  assert.equal(nearestChartReading(points, -1).readingId, 'first');
  assert.equal(nearestChartReading(points, 2).readingId, 'last');
  assert.equal(points[0].readingId, 'last');
});
test('time ties select the earlier record; missing channel values remain selectable', () => {
  const points = [record('first', 0), record('missing', 30, { measured: null }), record('last', 60)];
  assert.equal(nearestChartReading(points, 0.25).readingId, 'first');
  assert.equal(nearestChartReading(points, 0.5).readingId, 'missing');
  assert.equal(nearestChartReading([points[1]], 0.8).readingId, 'missing');
});
test('empty, invalid dates, missing identities and invalid coordinates do not select a record', () => {
  assert.equal(nearestChartReading([], 0.5), null);
  assert.equal(nearestChartReading([{ readingId: 'bad', timestamp: 'invalid' }, record(null, 0)], 0.5), null);
  assert.equal(nearestChartReading([record('first', 0)], NaN), null);
});
test('a scrubbed record binds measurements, sample estimates and rating to the same time', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01', 'overload');
  const first = nearestChartReading(snapshot.points, 0);
  const inspected = inspectHistoryRecord(snapshot, first.readingId, 'sample').snapshot;
  const rating = conditionRating(inspected, 'sample', Date.parse('2026-10-10T12:00:00Z'));
  const metrics = resolveMetrics(inspected, 'sample', rating);
  assert.equal(inspected.latest.measurementTime, first.timestamp);
  assert.equal(rating.identity.readingId, first.readingId);
  assert.equal(rating.breaches.length, 0);
  assert.equal(metrics.find(metric => metric.id === 'oil_temperature_c').value, first.measured);
  assert.equal(metrics.find(metric => metric.id === 'apparent_power').value, first.apparentPower);
  assert.equal(conditionRating(snapshot, 'sample', Date.parse('2026-10-10T12:00:00Z')).breaches.length, 2);
});
