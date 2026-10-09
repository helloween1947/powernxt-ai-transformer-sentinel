import { adaptReadingAnalytics, adaptLatestAnalytics } from './analyticsAdapter.js';
import { adaptTelemetryReading } from './telemetryAdapter.js';

export function streamParameters(source = 'device', runId = null) {
  if (!['device', 'simulator', 'file_replay'].includes(source)) throw new Error('Select a supported telemetry source.');
  if (source !== 'device' && !runId?.trim()) throw new Error('Simulator and replay sources need a run ID.');
  if (source === 'device' && runId) throw new Error('Device readings do not use a run ID.');
  return { source, run_id: source === 'device' ? undefined : runId.trim() };
}

export function createTelemetryClient(base, fetcher = globalThis.fetch) {
  async function request(path, parameters = {}, signal) {
    if (!base?.trim()) throw new Error('The backend address has not been configured.');
    const url = new URL(`${base.trim().replace(/\/+$/, '')}${path}`);
    for (const [key, value] of Object.entries(parameters)) {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value));
    }
    const timeout = AbortSignal.timeout(10000);
    const response = await fetcher(url, { signal: signal ? AbortSignal.any([signal, timeout]) : timeout });
    if (!response.ok) {
      const error = new Error(`Backend request failed with status ${response.status}.`);
      error.status = response.status;
      throw error;
    }
    return response.json();
  }
  return {
    getAssetPage: (limit = 20, offset = 0, signal) => request('/api/v1/assets', { limit, offset }, signal),
    getAssetDetails: (assetId, signal) => request(`/api/v1/assets/${encodeURIComponent(assetId)}`, {}, signal),
    async getLatestTelemetry(assetId, source = 'device', runId = null, signal) {
      return adaptTelemetryReading(await request(`/api/v1/assets/${encodeURIComponent(assetId)}/telemetry/latest`, streamParameters(source, runId), signal));
    },
    async getTelemetryHistory(assetId, { source = 'device', runId = null, limit = 20, offset = 0, start, end, signal } = {}) {
      const page = await request(`/api/v1/assets/${encodeURIComponent(assetId)}/telemetry`, { ...streamParameters(source, runId), limit, offset, start, end }, signal);
      return { items: page.items.map(adaptTelemetryReading), limit: page.limit, offset: page.offset };
    },
    async getReadingAnalytics(readingId, signal) {
      const analytics = adaptReadingAnalytics(await request(`/api/v1/telemetry/${encodeURIComponent(readingId)}/analytics`, {}, signal));
      if (analytics.reading_id !== readingId) throw new Error('Analytics response references a different requested reading.');
      return analytics;
    },
    async getLatestAnalytics(assetId, source = 'device', runId = null, signal) {
      return adaptLatestAnalytics(await request(`/api/v1/assets/${encodeURIComponent(assetId)}/analytics/latest`, streamParameters(source, runId), signal));
    },
  };
}
