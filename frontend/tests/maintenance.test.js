import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequest, adaptTask, updateRequest, validateActor, pageParameters } from '../src/services/maintenanceAdapter.js';
import { createMaintenanceClient } from '../src/services/maintenanceApi.js';

const wire = {
  id: 'a2cd3f1b-7605-42e9-a74e-252203f2d925', asset_id: 'registered-fixture',
  alert: { source: 'sample', alert_id: 'sample-cooling-001', asset_id: 'registered-fixture', summary: 'Explicit sample cooling alert.' },
  action: 'Arrange a sample cooling inspection.', owner: null, status: 'open', notes: '', version: 1,
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
};
const task = adaptTask(wire);
const createDraft = { assetId: wire.asset_id, alertId: wire.alert.alert_id, summary: wire.alert.summary, title: wire.action, owner: '', sampleMode: true };

test('sample creation maps title and owner; real alert provenance is rejected', () => {
  assert.deepEqual(createRequest(createDraft), { alert: wire.alert, action: wire.action, owner: null });
  assert.equal(createRequest({ ...createDraft, owner: ' Demo maintainer ' }).owner, 'Demo maintainer');
  assert.throws(() => createRequest({ ...createDraft, sampleMode: false }), /sample/);
  assert.throws(() => createRequest({ ...createDraft, alertId: 'real-detector-id' }), /sample-/);
  assert.throws(() => createRequest({ ...createDraft, title: ' ' }), /required/);
  assert.throws(() => createRequest({ ...createDraft, assetId: '' }), /required/);
  assert.throws(() => createRequest({ ...createDraft, summary: 'x'.repeat(501) }), /500/);
});

test('response preserves task identity, saved version, exact API status and timestamps', () => {
  assert.equal(task.title, wire.action); assert.equal(task.owner, ''); assert.equal(task.version, 1);
  assert.equal(task.assetId, wire.asset_id); assert.equal(task.status, 'open'); assert.deepEqual(task.alert, wire.alert);
  assert.equal(task.createdAt, wire.created_at); assert.equal(task.updatedAt, wire.updated_at);
  assert.throws(() => adaptTask({ ...wire, version: 0 }), /version/);
  assert.throws(() => adaptTask({ ...wire, status: 'reopened' }), /status/);
});

test('assignment, start and completion use each returned version; completion needs notes', () => {
  assert.throws(() => updateRequest(task, { owner: '', status: 'in_progress', notes: '' }), /owner/);
  const assigned = { ...task, owner: 'Maintainer', version: 2 };
  assert.equal(updateRequest(task, { owner: 'Maintainer', status: 'open', notes: '' }).owner, 'Maintainer');
  assert.equal(updateRequest(assigned, { owner: 'Maintainer', status: 'in_progress', notes: '' }).expected_version, 2);
  const started = { ...assigned, status: 'in_progress', version: 3 };
  assert.throws(() => updateRequest(started, { owner: '', status: 'in_progress', notes: 'Working' }), /unassigned/);
  assert.throws(() => updateRequest(started, { owner: 'Maintainer', status: 'completed', notes: '  ' }), /nonblank notes/);
  assert.deepEqual(updateRequest(started, { owner: 'Maintainer', status: 'completed', notes: 'Inspection complete.' }), {
    expected_version: 3, owner: 'Maintainer', status: 'completed', notes: 'Inspection complete.',
  });
});

test('cancellation requires a reason; illegal transitions and terminal edits are blocked', () => {
  for (const status of ['open', 'in_progress']) {
    const active = { ...task, status, owner: status === 'in_progress' ? 'Maintainer' : '' };
    assert.throws(() => updateRequest(active, { owner: active.owner, status: 'cancelled', notes: '' }), /notes/);
    assert.equal(updateRequest(active, { owner: active.owner, status: 'cancelled', notes: 'Sample inspection no longer required.' }).status, 'cancelled');
  }
  assert.throws(() => updateRequest(task, { owner: 'Maintainer', status: 'completed', notes: 'Done' }), /transition/);
  assert.throws(() => updateRequest({ ...task, status: 'in_progress', owner: 'Maintainer' }, { owner: 'Maintainer', status: 'open', notes: 'Reopen' }), /transition/);
  for (const status of ['completed', 'cancelled']) assert.throws(() => updateRequest({ ...task, status }, { owner: 'Maintainer', status: 'open', notes: 'Reopen' }), /read-only/);
  assert.throws(() => updateRequest(task, { owner: '', status: 'open', notes: '' }), /Change/);
});

test('actor identity and pagination reject invalid requests before HTTP', () => {
  assert.equal(validateActor(' Person C demo operator '), 'Person C demo operator');
  for (const actor of ['', ' ', 'x'.repeat(101), 'Bad\nactor', 'Bad\u007factor']) assert.throws(() => validateActor(actor));
  assert.deepEqual(pageParameters(100, 20), { limit: 100, offset: 20 });
  for (const args of [[0, 0], [101, 0], [20, -1], [20, 0.5]]) assert.throws(() => pageParameters(...args));
});

test('client uses the shared API origin, encodes filters, maps pages and sends PATCH headers only on PATCH', async () => {
  const calls = [];
  const client = createMaintenanceClient({ baseUrl: ' http://127.0.0.1:8000/ ', fetchImpl: async (url, options) => {
    calls.push({ url: String(url), ...options });
    const result = String(url).includes('/history') ? { items: [{ id: 1, version: 1 }], limit: 20, offset: 20 }
      : options.method === 'PATCH' ? { ...wire, owner: 'Maintainer', version: 2 }
      : options.method === 'POST' || new URL(url).pathname.endsWith(wire.id) ? wire
      : { items: [wire], limit: 20, offset: 20 };
    return new Response(JSON.stringify(result), { status: options.method === 'POST' ? 201 : 200 });
  } });
  const page = await client.tasks('registered-fixture', 20);
  assert.equal(page.offset, 20); assert.equal(page.items[0].title, wire.action);
  const url = new URL(calls[0].url); assert.equal(url.pathname, '/api/v1/maintenance/tasks'); assert.equal(url.searchParams.get('asset_id'), wire.asset_id);
  assert.equal(url.searchParams.get('offset'), '20'); assert.deepEqual(calls[0].headers, {});
  await client.create(createDraft); assert.equal(calls[1].headers['X-Demo-Actor'], undefined);
  const updated = await client.update(task, { owner: 'Maintainer', status: 'open', notes: '' }, ' Person C demo operator ');
  assert.equal(updated.version, 2); assert.equal(calls[2].headers['X-Demo-Actor'], 'Person C demo operator');
  assert.equal(calls[2].headers['Content-Type'], 'application/json'); assert.equal(JSON.parse(calls[2].body).expected_version, 1);
  await client.task(task.id); const history = await client.history(task.id, 20); assert.equal(history.items[0].version, 1);
  assert.equal(new URL(calls[4].url).searchParams.get('offset'), '20');
});

test('409 is surfaced without retrying or altering the operator draft', async () => {
  let count = 0;
  const client = createMaintenanceClient({ baseUrl: 'http://backend.example', fetchImpl: async () => {
    count++; return new Response(JSON.stringify({ detail: 'Task changed; retrieve its latest version before updating' }), { status: 409 });
  } });
  const draft = { owner: 'Maintainer', status: 'open', notes: 'Keep my draft' };
  await assert.rejects(client.update(task, draft, 'Person C demo operator'), error => error.status === 409 && /Task changed/.test(error.message));
  assert.equal(count, 1); assert.equal(draft.notes, 'Keep my draft'); assert.equal(task.version, 1);
});

test('network, missing origin, API validation and missing endpoints remain visible failures', async () => {
  await assert.rejects(createMaintenanceClient({}).tasks(), /VITE_API_BASE_URL/);
  await assert.rejects(createMaintenanceClient({ baseUrl: 'http://backend.example', fetchImpl: async () => { throw new TypeError('fetch failed'); } }).tasks(), /Cannot reach/);
  const client = createMaintenanceClient({ baseUrl: 'http://backend.example', fetchImpl: async () => new Response(JSON.stringify({ detail: [{ loc: ['body', 'owner'], msg: 'Invalid owner' }] }), { status: 422 }) });
  await assert.rejects(client.tasks(), error => error.status === 422 && /body.owner: Invalid owner/.test(error.message));
  const missing = createMaintenanceClient({ baseUrl: 'http://backend.example', fetchImpl: async () => new Response(JSON.stringify({ detail: 'Not Found' }), { status: 404 }) });
  await assert.rejects(missing.tasks(), error => error.status === 404);
});
