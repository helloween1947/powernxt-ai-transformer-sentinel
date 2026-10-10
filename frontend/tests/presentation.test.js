import test from 'node:test';
import assert from 'node:assert/strict';
import { displayId, displayLocation, displayStatus, displaySource, displayMetricReason, displayRatingState } from '../src/lib/presentation.js';
import { sampleSnapshot } from '../src/data/workstationSample.js';
import { resolveMetrics } from '../src/data/capabilities.js';
import { conditionRating } from '../src/domain/conditionRating.js';
import { exportRows } from '../src/services/reportExport.js';

test('clean labels preserve real identifiers and do not alter canonical records or export provenance', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01');
  const before = structuredClone(snapshot);
  assert.equal(displayId(snapshot.latest.readingId), 'R-25');
  assert.equal(displayId(snapshot.details.asset_id), 'TX-01');
  assert.equal(displayId('REAL-TX-123'), 'REAL-TX-123');
  assert.equal(displayId(7), '7');
  assert.equal(displayLocation(snapshot.details.location), 'Substation · Feeder 04');
  assert.equal(displayStatus('sample'), '—');
  assert.equal(displayStatus('failed'), 'failed');
  assert.equal(displaySource('simulator'), 'Stored run');
  assert.deepEqual(snapshot, before);
  assert.equal(exportRows(snapshot, 'sample')[0].scope, 'Sample UI illustration');
});
test('clean measurement descriptions retain unavailable channels and condition breaches', () => {
  const snapshot = sampleSnapshot('SAMPLE-TX-01', 'missing');
  const oil = resolveMetrics(snapshot, 'sample').find(metric => metric.id === 'oil_temperature_c');
  assert.equal(displayMetricReason(oil), 'Channel unavailable.');
  assert.equal(displayMetricReason({ state: 'Unavailable', reason: 'Bad channel quality.' }), 'Bad channel quality.');
  const now = Date.parse('2026-10-10T12:00:00Z');
  assert.equal(displayRatingState(conditionRating(sampleSnapshot('SAMPLE-TX-01'), 'sample', now)), 'Condition overview');
  assert.equal(displayRatingState(conditionRating(sampleSnapshot('SAMPLE-TX-01', 'overload'), 'sample', now)), 'Limit breach');
  assert.equal(displayRatingState(conditionRating(snapshot, 'sample', now)), 'Insufficient evidence');
});
