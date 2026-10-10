import { adaptIncident, adaptEvent, adaptEvidence, validateAcknowledgement } from './incidentAdapter.js';

export class IncidentApiError extends Error {
  constructor(status, message, code = 'incident_error', currentVersion = null) {
    super(message);
    this.name = 'IncidentApiError';
    this.status = status;
    this.code = code;
    this.currentVersion = currentVersion;
  }
}

export function createIncidentClient({ baseUrl, fetchImpl = globalThis.fetch }) {
  const base = (baseUrl ?? '').trim().replace(/\/+$/, '');

  async function request(path, { method = 'GET', body, token, query = {} } = {}) {
    if (!base) {
      throw new Error('Set VITE_API_BASE_URL to a reachable backend and restart Vite.');
    }
    const url = new URL(`${base}${path}`);
    for (const [key, value] of Object.entries(query)) {
      if (value !== '' && value != null) {
        url.searchParams.set(key, String(value));
      }
    }

    const headers = {};
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token.trim()}`;
    }

    let response;
    try {
      response = await fetchImpl(url, {
        method,
        headers,
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        signal: AbortSignal.timeout(10000),
      });
    } catch {
      throw new IncidentApiError(0, 'Cannot reach the incident backend. Check network connection or server status.', 'network_error');
    }

    let result;
    try {
      result = await response.json();
    } catch {
      throw new IncidentApiError(response.status, 'Backend returned an unreadable response.', 'invalid_json');
    }

    if (!response.ok) {
      if (response.status === 401 && token) globalThis.dispatchEvent?.(new Event('powernxt-credential-invalid'));
      const code = result.code || 'error';
      const message = result.message || result.detail || `Incident request failed (${response.status}).`;
      const currentVersion = result.current_version ?? null;
      throw new IncidentApiError(response.status, message, code, currentVersion);
    }

    return result;
  }

  return {
    listIncidents: async ({ assetId, source = 'device', runId = null, conditionStatus = null, limit = 20, cursor = null, token } = {}) => {
      const query = {
        asset_id: assetId,
        source,
        limit,
      };
      if (source !== 'device' && runId) {
        query.run_id = runId;
      }
      if (conditionStatus) {
        query.condition_status = conditionStatus;
      }
      if (cursor) {
        query.cursor = cursor;
      }

      const page = await request('/api/v1/incidents', {
        method: 'GET',
        token,
        query,
      });

      return {
        schemaVersion: page.schema_version,
        items: (page.items ?? []).map(adaptIncident),
        nextCursor: page.next_cursor ?? null,
      };
    },

    getIncident: async (incidentId, token) => {
      const data = await request(`/api/v1/incidents/${encodeURIComponent(incidentId)}`, {
        method: 'GET',
        token,
      });
      return adaptIncident(data);
    },

    getEvidence: async (incidentId, { cursor = 0, limit = 20, token } = {}) => {
      const page = await request(`/api/v1/incidents/${encodeURIComponent(incidentId)}/evidence`, {
        method: 'GET',
        token,
        query: { cursor, limit },
      });
      return {
        schemaVersion: page.schema_version,
        items: (page.items ?? []).map(adaptEvidence),
        nextCursor: page.next_cursor ?? null,
      };
    },

    getEvents: async (incidentId, { cursor = 0, limit = 20, token } = {}) => {
      const page = await request(`/api/v1/incidents/${encodeURIComponent(incidentId)}/events`, {
        method: 'GET',
        token,
        query: { cursor, limit },
      });
      return {
        schemaVersion: page.schema_version,
        items: (page.items ?? []).map(adaptEvent),
        nextCursor: page.next_cursor ?? null,
      };
    },

    acknowledge: async (incidentId, { expectedVersion, idempotencyKey, token } = {}) => {
      const payload = validateAcknowledgement({ expectedVersion, idempotencyKey });
      const data = await request(`/api/v1/incidents/${encodeURIComponent(incidentId)}/acknowledgements`, {
        method: 'POST',
        body: payload,
        token,
      });
      return adaptIncident(data);
    },
  };
}
