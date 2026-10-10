import test from 'node:test';
import assert from 'node:assert/strict';
import { chartPointsForContext } from '../src/domain/chartProvenance.js';
test('charts never combine immutable configurations or stored models; gaps remain', () => {
  const rows = [{ readingId: 1, configurationVersion: 1, modelVersion: 'a', predicted: null }, { readingId: 2, configurationVersion: 2, modelVersion: 'a', predicted: 40 }, { readingId: 3, configurationVersion: 1, modelVersion: 'b', predicted: 41 }, { readingId: 4, configurationVersion: 1, modelVersion: 'a', predicted: 42 }];
  assert.deepEqual(chartPointsForContext(rows, 1, 'a').map(p => p.readingId), [1,4]);
  assert.equal(chartPointsForContext(rows, 1, 'a')[0].predicted, null);
  assert.equal(rows.length, 4);
  assert.deepEqual(chartPointsForContext(rows, 1, null), []);
});
