import test from 'node:test';
import assert from 'node:assert/strict';
import { inspectRuntimeContract } from '../src/services/runtimeContract.js';

test('incident and forecast workflows require implemented verbs, independently of analytics', () => {
  const spec = { openapi: '3.1.0', paths: {
    '/api/v1/operators/me': { get: {} },
    '/api/v1/incidents': { get: {} },
    '/api/v1/incidents/{incident_id}/acknowledgements': { post: {} },
    '/api/v1/assets/{asset_id}/what-if': { post: {} },
  } };
  assert.equal(inspectRuntimeContract(spec).incidents, true);
  assert.equal(inspectRuntimeContract(spec).whatIf, true);
  assert.equal(inspectRuntimeContract(spec).analytics, false);
  delete spec.paths['/api/v1/operators/me'].get;
  delete spec.paths['/api/v1/assets/{asset_id}/what-if'].post;
  assert.equal(inspectRuntimeContract(spec).incidents, false);
  assert.equal(inspectRuntimeContract(spec).whatIf, false);
});
