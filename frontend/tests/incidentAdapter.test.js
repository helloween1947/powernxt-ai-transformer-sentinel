import test from 'node:test';
import assert from 'node:assert/strict';
import { adaptIncident, validateAcknowledgement, adaptEvent, adaptEvidence } from '../src/services/incidentAdapter.js';
import { createIncidentClient } from '../src/services/incidentApi.js';

const sampleIncidentWire = {
  schema_version: 'incident-1.0.0',
  incident_id: 'c1a2b3c4-1111-2222-3333-444455556666',
  incident_version: 1,
  asset_id: 'tx-alpha',
  source: 'analytics',
  measurement_source: 'device',
  run_id: null,
  category: 'thermal_overload',
  severity: 'critical',
  detector_epoch: 'd1e2f3a4-5555-6666-7777-888899990000',
  detector_episode_key: 'top_oil_overload',
  condition_status: 'active',
  monitoring_status: 'monitoring',
  opened_at: '2026-10-10T12:00:00Z',
  recovered_at: null,
  last_evaluated_measurement_time: '2026-10-10T12:05:00Z',
  last_evidence_status: 'available',
  acknowledgement: {
    status: 'unacknowledged',
    acknowledged_at: null,
    actor_ref: null,
  },
};

test('adaptIncident correctly maps wire incident to UI representation', () => {
  const adapted = adaptIncident(sampleIncidentWire);
  assert.equal(adapted.id, sampleIncidentWire.incident_id);
  assert.equal(adapted.version, 1);
  assert.equal(adapted.assetId, 'tx-alpha');
  assert.equal(adapted.severity, 'critical');
  assert.equal(adapted.conditionStatus, 'active');
  assert.equal(adapted.monitoringStatus, 'monitoring');
  assert.equal(adapted.acknowledgement.status, 'unacknowledged');
  assert.equal(adapted.runId, null);
});

test('adaptIncident rejects mismatched schema version', () => {
  assert.throws(() => adaptIncident({ ...sampleIncidentWire, schema_version: 'incident-2.0.0' }), /schema version/);
});

test('validateAcknowledgement enforces version > 0 and UUIDv4 format', () => {
  const validKey = 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d';
  const ack = validateAcknowledgement({ expectedVersion: 1, idempotencyKey: validKey });
  assert.equal(ack.schema_version, 'incident-acknowledgement-1.0.0');
  assert.equal(ack.expected_version, 1);
  assert.equal(ack.idempotency_key, validKey);

  assert.throws(() => validateAcknowledgement({ expectedVersion: 0, idempotencyKey: validKey }), /positive integer/);
  assert.throws(() => validateAcknowledgement({ expectedVersion: -1, idempotencyKey: validKey }), /positive integer/);
  assert.throws(() => validateAcknowledgement({ expectedVersion: 1.5, idempotencyKey: validKey }), /positive integer/);
  assert.throws(() => validateAcknowledgement({ expectedVersion: 1, idempotencyKey: 'not-a-uuid' }), /valid UUIDv4/);
});

test('adaptEvent and adaptEvidence map items cleanly', () => {
  const eventWire = {
    event_id: 'e1e2e3e4-0000-1111-2222-333344445555',
    incident_id: sampleIncidentWire.incident_id,
    incident_version: 1,
    event_type: 'opened',
    evidence_id: 101,
    actor_id: null,
    recorded_at: '2026-10-10T12:00:00Z',
    payload: { temp_c: 110.5 },
  };
  const event = adaptEvent(eventWire);
  assert.equal(event.eventId, eventWire.event_id);
  assert.equal(event.eventType, 'opened');
  assert.equal(event.evidenceId, 101);

  const evidenceWire = {
    evidence_id: 101,
    incident_id: sampleIncidentWire.incident_id,
    incident_version: 1,
    recorded_at: '2026-10-10T12:00:00Z',
    payload: { metric: 'top_oil_c', value: 110.5 },
  };
  const evidence = adaptEvidence(evidenceWire);
  assert.equal(evidence.evidenceId, 101);
  assert.deepEqual(evidence.payload, evidenceWire.payload);
});

test('incidentClient calls endpoints with auth token and handles errors', async () => {
  const calls = [];
  const client = createIncidentClient({
    baseUrl: 'http://test-incident.local',
    fetchImpl: async (url, options) => {
      calls.push({ url: String(url), ...options });
      if (options.method === 'POST') {
        return new Response(JSON.stringify({ ...sampleIncidentWire, acknowledgement: { status: 'acknowledged', acknowledged_at: '2026-10-10T12:10:00Z', actor_ref: 'b1b2b3b4-0000-0000-0000-000000000000' } }), { status: 201 });
      }
      return new Response(JSON.stringify({ schema_version: 'incident-page-1.0.0', items: [sampleIncidentWire], next_cursor: null }), { status: 200 });
    },
  });

  const page = await client.listIncidents({
    assetId: 'tx-alpha',
    source: 'device',
    token: 'secret-token-123',
  });

  assert.equal(page.items.length, 1);
  assert.equal(calls[0].headers['Authorization'], 'Bearer secret-token-123');
  const parsedUrl = new URL(calls[0].url);
  assert.equal(parsedUrl.searchParams.get('asset_id'), 'tx-alpha');
  assert.equal(parsedUrl.searchParams.get('source'), 'device');
  assert.equal(parsedUrl.searchParams.get('run_id'), null);

  // Acknowledge call
  const ackResult = await client.acknowledge(sampleIncidentWire.incident_id, {
    expectedVersion: 1,
    idempotencyKey: 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d',
    token: 'secret-token-123',
  });
  assert.equal(ackResult.acknowledgement.status, 'acknowledged');
  assert.equal(calls[1].headers['Authorization'], 'Bearer secret-token-123');
});
