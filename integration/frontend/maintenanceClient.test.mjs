import test from 'node:test';
import assert from 'node:assert/strict';
import { createMaintenanceClient } from './maintenanceClient.mjs';

test('update sends saved version, demo actor and mapped status, with no automatic retry', async () => {
  const calls = [];
  const client = createMaintenanceClient({ baseUrl: 'http://example.test/', fetchImpl: async (...args) => {
    calls.push(args); return { ok: false, status: 409, json: async () => ({ detail: 'Task changed' }) };
  } });
  await assert.rejects(client.update({ id: 'task-1', version: 4 }, { status: 'Completed', notes: 'Finished' }, 'Demo'),
    error => error.status === 409 && error.message === 'Task changed');
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], 'http://example.test/api/v1/maintenance/tasks/task-1');
  assert.equal(calls[0][1].headers['X-Demo-Actor'], 'Demo');
  assert.deepEqual(JSON.parse(calls[0][1].body), { expected_version: 4, status: 'completed', notes: 'Finished' });
});

test('task pagination preserves page metadata and encodes the registered asset ID', async () => {
  let url;
  const client = createMaintenanceClient({ baseUrl: 'http://example.test', fetchImpl: async value => {
    url = value; return { ok: true, status: 200, json: async () => ({ items: [], limit: 20, offset: 40 }) };
  } });
  assert.deepEqual(await client.tasks('asset.name', 40), { items: [], limit: 20, offset: 40 });
  assert.match(url, /asset_id=asset.name&limit=20&offset=40$/);
});

test('validation, missing configuration, transport and invalid JSON failures remain errors', async () => {
  const missing = createMaintenanceClient({ baseUrl: '' });
  await assert.rejects(missing.assets(), /VITE_API_BASE_URL/);
  const invalid = createMaintenanceClient({ baseUrl: 'http://example.test', fetchImpl: async () => ({ ok: false,
    status: 422, json: async () => ({ detail: [{ loc: ['body', 'notes'], msg: 'Required' }] }) }) });
  await assert.rejects(invalid.history('task'), error => error.status === 422 && /body.notes: Required/.test(error.message));
  const broken = createMaintenanceClient({ baseUrl: 'http://example.test', fetchImpl: async () => { throw new Error('Network unavailable'); } });
  await assert.rejects(broken.assets(), /Network unavailable/);
  const unreadable = createMaintenanceClient({ baseUrl: 'http://example.test', fetchImpl: async () => ({ status: 503, json: async () => { throw new Error('HTML'); } }) });
  await assert.rejects(unreadable.assets(), error => error.status === 503 && /unreadable/.test(error.message));
});
