export const severityColors = {
  info: '#0e7490',
  warning: '#a16207',
  critical: '#b91c1c',
};

export const conditionColors = {
  active: '#b91c1c',
  recovered: '#15803d',
};

export const monitoringColors = {
  monitoring: '#15803d',
  interrupted: '#ca8a04',
};

export function adaptIncident(raw) {
  if (!raw || raw.schema_version !== 'incident-1.0.0') {
    throw new Error('Unsupported incident schema version.');
  }
  return {
    id: raw.incident_id,
    version: raw.incident_version,
    assetId: raw.asset_id,
    source: raw.source,
    measurementSource: raw.measurement_source,
    runId: raw.run_id ?? null,
    category: raw.category,
    severity: raw.severity,
    detectorEpoch: raw.detector_epoch,
    detectorEpisodeKey: raw.detector_episode_key,
    conditionStatus: raw.condition_status,
    monitoringStatus: raw.monitoring_status,
    openedAt: raw.opened_at,
    recoveredAt: raw.recovered_at ?? null,
    lastEvaluatedTime: raw.last_evaluated_measurement_time,
    lastEvidenceStatus: raw.last_evidence_status,
    acknowledgement: {
      status: raw.acknowledgement?.status ?? 'unacknowledged',
      acknowledgedAt: raw.acknowledgement?.acknowledged_at ?? null,
      actorRef: raw.acknowledgement?.actor_ref ?? null,
    },
  };
}

export function validateAcknowledgement({ expectedVersion, idempotencyKey }) {
  if (!Number.isInteger(expectedVersion) || expectedVersion < 1) {
    throw new Error('Expected incident version must be a positive integer.');
  }
  const cleanKey = String(idempotencyKey ?? '').trim();
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(cleanKey)) {
    throw new Error('Idempotency key must be a valid UUIDv4 string.');
  }
  return {
    schema_version: 'incident-acknowledgement-1.0.0',
    expected_version: expectedVersion,
    idempotency_key: cleanKey,
  };
}

export function adaptEvent(raw) {
  return {
    eventId: raw.event_id,
    incidentId: raw.incident_id,
    incidentVersion: raw.incident_version,
    eventType: raw.event_type,
    evidenceId: raw.evidence_id ?? null,
    actorId: raw.actor_id ?? null,
    recordedAt: raw.recorded_at,
    payload: raw.payload ?? {},
  };
}

export function adaptEvidence(raw) {
  return {
    evidenceId: raw.evidence_id,
    incidentId: raw.incident_id,
    incidentVersion: raw.incident_version,
    recordedAt: raw.recorded_at,
    payload: raw.payload ?? {},
  };
}
