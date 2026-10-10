import test from 'node:test';
import assert from 'node:assert/strict';
import { createAnalyticsRequest, adaptTask } from '../src/services/maintenanceAdapter.js';
import { createMaintenanceClient } from '../src/services/maintenanceApi.js';

const analyticsWire = {
  id: 'b1cd3f1b-7605-42e9-a74e-252203f2d999',
  asset_id: 'tx-gamma',
  alert: {
    source: 'analytics',
    alert_id: 'c1a2b3c4-1111-2222-3333-444455556666',
    asset_id: 'tx-gamma',
    summary: 'Thermal overload detected on sustained threshold.',
  },
  action: 'Inspect transformer radiator bank.',
  owner: 'Lead Technician',
  status: 'open',
  notes: '',
  version: 1,
  incident_id: 'c1a2b3c4-1111-2222-3333-444455556666',
  created_at: '2026-10-10T12:00:00Z',
  updated_at: '2026-10-10T12:00:00Z',
};

test('createAnalyticsRequest packages incident alert correctly', () => {
  const req = createAnalyticsRequest({
    assetId: 'tx-gamma',
    incidentId: 'c1a2b3c4-1111-2222-3333-444455556666',
    title: 'Inspect transformer radiator bank.',
    owner: 'Lead Technician',
  });

  assert.equal(req.alert.source, 'analytics');
  assert.equal(req.alert.incident_id, 'c1a2b3c4-1111-2222-3333-444455556666');
  assert.equal(req.alert.asset_id, 'tx-gamma');
  assert.equal(req.action, 'Inspect transformer radiator bank.');
  assert.equal(req.owner, 'Lead Technician');
});

test('adaptTask preserves incidentId for genuine tasks', () => {
  const adapted = adaptTask(analyticsWire);
  assert.equal(adapted.id, analyticsWire.id);
  assert.equal(adapted.incidentId, 'c1a2b3c4-1111-2222-3333-444455556666');
  assert.equal(adapted.alert.source, 'analytics');
});

test('maintenance client queries analytics source with Authorization bearer token', async () => {
  const calls = [];
  const client = createMaintenanceClient({
    baseUrl: 'http://test-maintenance.local',
    fetchImpl: async (url, options) => {
      calls.push({ url: String(url), ...options });
      return new Response(JSON.stringify({
        items: [analyticsWire],
        limit: 20,
        offset: 0,
      }), { status: 200 });
    },
  });

  const page = await client.tasks('tx-gamma', 0, 'analytics', 'test-bearer-token');
  assert.equal(page.items.length, 1);
  assert.equal(page.items[0].incidentId, analyticsWire.incident_id);

  const url = new URL(calls[0].url);
  assert.equal(url.searchParams.get('source'), 'analytics');
  assert.equal(url.searchParams.get('asset_id'), 'tx-gamma');
  assert.equal(calls[0].headers['Authorization'], 'Bearer test-bearer-token');
  assert.equal(calls[0].headers['X-Demo-Actor'], undefined);
});

test('maintenance client updates analytics task with Bearer token without X-Demo-Actor', async () => {
  const calls = [];
  const client = createMaintenanceClient({
    baseUrl: 'http://test-maintenance.local',
    fetchImpl: async (url, options) => {
      calls.push({ url: String(url), ...options });
      return new Response(JSON.stringify({
        ...analyticsWire,
        version: 2,
        status: 'in_progress',
      }), { status: 200 });
    },
  });

  const task = adaptTask(analyticsWire);
  const updated = await client.update(
    task,
    { owner: 'Lead Technician', status: 'in_progress', notes: '' },
    null,
    'operator-token-xyz'
  );

  assert.equal(updated.version, 2);
  assert.equal(updated.status, 'in_progress');
  assert.equal(calls[0].headers['Authorization'], 'Bearer operator-token-xyz');
  assert.equal(calls[0].headers['X-Demo-Actor'], undefined);
});
