import test from 'node:test';
import assert from 'node:assert/strict';
import { occurredBeforeOpen } from '../src/domain/dialogInteraction.js';

test('a queued outside event from before a reopen cannot dismiss the new inspection', () => {
  assert.equal(occurredBeforeOpen(120, 140), true);
  assert.equal(occurredBeforeOpen(150, 140), false);
  assert.equal(occurredBeforeOpen(140, 140), false);
  // That same event becomes stale after another close/reopen.
  assert.equal(occurredBeforeOpen(150, 160), true);
});
test('absent or invalid clocks do not block ordinary outside dismissal', () => {
  for (const value of [null, undefined, NaN, Infinity, '120']) {
    assert.equal(occurredBeforeOpen(value, 140), false);
    assert.equal(occurredBeforeOpen(140, value), false);
  }
});
