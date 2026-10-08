import { adaptTelemetryReading } from './telemetryAdapter.js';

async function request(path, parameters = {}) {
  const base = import.meta.env.VITE_API_BASE_URL?.trim();

  if (!base) {
    throw new Error('The backend address has not been configured.');
  }

  const url = new URL(`${base.replace(/\/+$/, '')}${path}`);

  for (const [key, value] of Object.entries(parameters)) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  }

  const response = await fetch(url, {
    signal: AbortSignal.timeout(10000),
  });

  if (!response.ok) {
    const error = new Error(
      `Backend request failed with status ${response.status}.`,
    );
    error.status = response.status;
    throw error;
  }

  return response.json();
}

function streamParameters(source = 'device', runId = null) {
  if (!['device', 'simulator', 'file_replay'].includes(source)) {
    throw new Error('Select a supported telemetry source.');
  }

  if (source !== 'device' && !runId?.trim()) {
    throw new Error('Simulator and replay sources need a run ID.');
  }

  if (source === 'device' && runId) {
    throw new Error('Device readings do not use a run ID.');
  }

  return {
    source,
    run_id: source === 'device' ? undefined : runId.trim(),
  };
}

export async function getAssetPage(limit = 20, offset = 0) {
  return request('/api/v1/assets', { limit, offset });
}

export async function getAssetDetails(assetId) {
  return request(`/api/v1/assets/${encodeURIComponent(assetId)}`);
}

export async function getLatestTelemetry(
  assetId,
  source = 'device',
  runId = null,
) {
  const reading = await request(
    `/api/v1/assets/${encodeURIComponent(assetId)}/telemetry/latest`,
    streamParameters(source, runId),
  );

  return adaptTelemetryReading(reading);
}

export async function getTelemetryHistory(
  assetId,
  {
    source = 'device',
    runId = null,
    limit = 20,
    offset = 0,
    start,
    end,
  } = {},
) {
  const page = await request(
    `/api/v1/assets/${encodeURIComponent(assetId)}/telemetry`,
    {
      ...streamParameters(source, runId),
      limit,
      offset,
      start,
      end,
    },
  );

  return {
    items: page.items.map(adaptTelemetryReading),
    limit: page.limit,
    offset: page.offset,
  };
}