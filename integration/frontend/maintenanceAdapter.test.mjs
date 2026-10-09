import test from 'node:test';
import assert from 'node:assert/strict';
import { toCreateRequest, toFrontendTask, toFrontendPage, toUpdateRequest } from './maintenanceAdapter.mjs';

test('C create fields map to an explicitly sample request', () => {
  const ui = { title: 'Inspect cooling', owner: 'Demo', assetId: 'T001', alertId: 'fixture-1', evidence: 'Sample evidence' };
  assert.deepEqual(toCreateRequest(ui, { sampleMode: true }), {
    alert: { source: 'sample', alert_id: 'sample-fixture-1', asset_id: 'T001', summary: 'Sample evidence' },
    action: 'Inspect cooling', owner: 'Demo',
  });
  assert.throws(() => toCreateRequest(ui), /Genuine alerts/);
  assert.throws(() => toCreateRequest({ ...ui, alertId: null }, { sampleMode: true }), /linked sample alert/);
});

test('API response maps status, notes, assignment, timestamps and version', () => {
  const api = { id: 'task-id', action: 'Inspect', owner: 'Demo', asset_id: 'T001',
    alert: { alert_id: 'sample-1', summary: 'Evidence', source: 'sample' }, status: 'in_progress',
    notes: 'Started', created_at: 'first', updated_at: 'second', version: 3 };
  const ui = toFrontendTask(api);
  assert.equal(ui.status, 'In progress');
  assert.equal(ui.owner, 'Demo');
  assert.equal(ui.notes, 'Started');
  assert.equal(ui.version, 3);
  assert.equal(ui.assetId, 'T001');
  assert.equal(ui.alertSource, 'sample');
  assert.deepEqual(toFrontendPage({ items: [api], limit: 20, offset: 40 }), { items: [ui], limit: 20, offset: 40 });
});

test('C updates carry the retrieved version and canonical statuses', () => {
  assert.deepEqual(toUpdateRequest({ status: 'Completed', notes: 'Finished' }, 4),
    { expected_version: 4, status: 'completed', notes: 'Finished' });
  assert.deepEqual(toUpdateRequest({ status: 'Cancelled', notes: 'Reason' }, 2),
    { expected_version: 2, status: 'cancelled', notes: 'Reason' });
  assert.throws(() => toUpdateRequest({ status: 'Recovered' }, 1), /Unsupported status/);
  assert.throws(() => toUpdateRequest({ actor: 'Spoof' }, 1), /Unsupported task update/);
});
