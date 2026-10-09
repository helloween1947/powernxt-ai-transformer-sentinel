// Run with Node from the repository root. No npm packages or browser are needed.
// Optional second argument retrieves a previously completed task after restart.
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { toCreateRequest, toFrontendTask, toFrontendPage, toUpdateRequest } from './maintenanceAdapter.mjs';

const [baseUrl = 'http://127.0.0.1:8000', savedId] = process.argv.slice(2);
const root = '/api/v1/maintenance/tasks';
async function request(path, { method = 'GET', body, expected = 200 } = {}) {
  const response = await fetch(`${baseUrl.replace(/\/$/, '')}${path}`, {
    method, headers: { 'Content-Type': 'application/json', 'X-Demo-Actor': 'Person D demo operator' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    signal: AbortSignal.timeout(10000),
  });
  const result = await response.json();
  assert.equal(response.status, expected, JSON.stringify(result));
  return result;
}

let task;
if (savedId) {
  task = toFrontendTask(await request(`${root}/${encodeURIComponent(savedId)}`));
} else {
  const assetId = 'sample-transformer-d';
  const asset = await fetch(`${baseUrl}/api/v1/assets/${assetId}`);
  if (asset.status === 404) await request('/api/v1/assets', { method: 'POST', expected: 201, body: {
    asset_id: assetId, name: 'Person D sample transformer', location: 'Demonstration only', timezone: 'Asia/Kolkata',
  } });
  else assert.equal(asset.status, 200);
  const ui = { title: 'Sample cooling inspection', owner: 'Demo maintainer', assetId,
    alertId: `sample-workflow-${randomUUID()}`, evidence: 'Explicit sample fixture; no genuine detector output.' };
  task = toFrontendTask(await request(root, { method: 'POST', expected: 201,
    body: toCreateRequest(ui, { sampleMode: true }) }));
  assert.equal(task.status, 'Open');
  task = toFrontendTask(await request(`${root}/${task.id}`, { method: 'PATCH',
    body: toUpdateRequest({ status: 'In progress', notes: 'Sample inspection started' }, task.version) }));
  const staleVersion = task.version;
  task = toFrontendTask(await request(`${root}/${task.id}`, { method: 'PATCH',
    body: toUpdateRequest({ status: 'Completed', notes: 'Sample inspection completed' }, task.version) }));
  await request(`${root}/${task.id}`, { method: 'PATCH', expected: 409,
    body: toUpdateRequest({ notes: 'Stale client update' }, staleVersion) });
  const page = toFrontendPage(await request(`${root}?asset_id=${assetId}&limit=100&offset=0`));
  assert(page.items.some(item => item.id === task.id));
  assert.equal(page.limit, 100);
}
const history = await request(`${root}/${task.id}/history`);
assert.equal(task.status, 'Completed');
assert.equal(task.notes, 'Sample inspection completed');
assert.equal(task.version, 3);
assert.deepEqual(history.items.map(item => item.new_status), ['open', 'in_progress', 'completed']);
assert.deepEqual(history.items.map(item => item.version), [1, 2, 3]);
assert(history.items.slice(1).every(item => item.actor === 'Person D demo operator' && item.identity_source === 'demo_header'));
console.log(savedId ? 'PASS: completed task and history survived backend restart.' : 'PASS: C field/status adapter against real maintenance HTTP API, including stale-update rejection.');
console.log(JSON.stringify({ task, history }, null, 2));
console.log(`Restart check: node integration/frontend/verifyMaintenanceApi.mjs ${baseUrl} ${task.id}`);
