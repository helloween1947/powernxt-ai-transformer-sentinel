import test from 'node:test';
import assert from 'node:assert/strict';
import { cameraResetProgress, inspectionEntry } from '../src/domain/motion.js';

test('camera reset stays bounded and moves monotonically to the exact endpoint', () => {
  assert.equal(cameraResetProgress(-1), 0);
  assert.equal(cameraResetProgress(0), 0);
  assert.equal(cameraResetProgress(0.18), 0.5);
  assert.equal(cameraResetProgress(0.36), 1);
  assert.equal(cameraResetProgress(10), 1);
  let previous = 0;
  for (let i = 0; i <= 36; i++) {
    const value = cameraResetProgress(i / 100);
    assert.ok(value >= previous && value <= 1);
    previous = value;
  }
  assert.ok(cameraResetProgress(0.01) < cameraResetProgress(0.19) - cameraResetProgress(0.18));
});
test('reduced-motion inspection appears immediately without perspective or translation', () => {
  assert.deepEqual(inspectionEntry(true), { opacity: 1, y: 0 });
  assert.equal(inspectionEntry(false).opacity, 0);
});
