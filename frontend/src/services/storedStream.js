import { usableMeasurement } from './telemetryAdapter.js';

const activeStatuses = new Set(['pending', 'processing', 'retry']);

function assertStream(record, selection, adapted = false) {
  const asset = adapted ? record.assetId : record.asset_id;
  const run = adapted ? record.runId : record.run_id;
  if (asset !== selection.assetId || record.source !== selection.source || (run ?? null) !== selection.runId) {
    throw new Error('Backend returned data from a different selected stream.');
  }
}

export async function boundedMap(items, action, signal, concurrency = 4) {
  const output = new Array(items.length);
  let next = 0;
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (next < items.length) {
      signal?.throwIfAborted();
      const index = next++;
      try { output[index] = { value: await action(items[index]), ok: true }; }
      catch (error) { output[index] = { error, ok: false }; }
    }
  }));
  return output;
}

export function thermalPoints(readings, analytics) {
  const byId = new Map(analytics.map(item => [item.reading_id, item]));
  return [...readings].sort((a, b) => Date.parse(a.measurementTime) - Date.parse(b.measurementTime) || a.readingId - b.readingId).map(reading => {
    const result = byId.get(reading.readingId);
    const payload = result?.result?.payload;
    const metric = path => result?.metrics.find(m => m.path === path);
    const predicted = metric('thermal_assessment.predicted_top_oil_temperature_c');
    const residual = metric('thermal_assessment.thermal_residual_c');
    const rawMeasured = payload ? (payload.metadata?.units?.oil_temperature === 'C' ? payload.thermal_assessment?.measured_top_oil_temperature_c : null) : reading.measurements.oil_temperature_c;
    const measured = usableMeasurement(reading, 'oil_temperature_c') == null ? null : rawMeasured;
    return {
      readingId: reading.readingId, timestamp: reading.measurementTime,
      processedAt: result?.result?.created_at ?? null,
      configurationVersion: reading.configurationVersion,
      measured: Number.isFinite(measured) ? measured : null,
      predicted: predicted?.value ?? null, residual: residual?.value ?? null,
      capacityLoading: metric('electrical_metrics.capacity_loading_pct')?.value ?? null,
      phaseLoading: metric('electrical_metrics.max_phase_loading_pct')?.value ?? null,
      apparentPower: metric('electrical_metrics.apparent_power_kva')?.value ?? null,
      elapsed: payload?.thermal_assessment?.elapsed_s ?? null,
      status: result?.status ?? 'not_retrieved',
      modelId: result?.result?.model_id ?? null,
      modelVersion: result?.result?.model_version ?? null,
      parameterVersion: result?.result?.parameter_version ?? null,
      reasons: [...new Set([...(predicted?.reasons ?? []), ...(residual?.reasons ?? [])])],
    };
  });
}

export async function loadStreamSnapshot(client, selection, signal) {
  const { assetId, source, runId, offset = 0, start, end } = selection;
  const details = await client.getAssetDetails(assetId, signal);
  if (details.asset_id !== assetId) throw new Error('Asset response identity differs from the selected asset.');
  const results = await Promise.allSettled([
    client.getLatestTelemetry(assetId, source, runId, signal),
    client.getTelemetryHistory(assetId, { source, runId, limit: 20, offset, start, end, signal }),
    client.supportsAnalytics === false ? Promise.resolve(null) : client.getLatestAnalytics(assetId, source, runId, signal),
  ]);
  signal.throwIfAborted();
  const errors = [];
  const labels = ['Latest telemetry', 'History', 'Latest completed analytics'];
  const values = results.map((result, index) => {
    if (result.status === 'fulfilled') return result.value;
    if (index === 0 && result.reason.status === 404) return null;
    errors.push(`${labels[index]}: ${result.reason.message}`);
    return null;
  });
  const [latest, page] = values;
  let latestEnvelope = values[2];
  if (latest) assertStream(latest, selection, true);
  if (latestEnvelope) {
    try { assertStream(latestEnvelope, selection); }
    catch (error) { errors.push(`Latest analytics integrity: ${error.message}`); latestEnvelope = null; }
  }
  const history = page?.items ?? [];
  history.forEach(reading => assertStream(reading, selection, true));
  const ids = [...new Set([...history.map(r => r.readingId), latest?.readingId, latestEnvelope?.latest_completed_reading_id].filter(id => id != null))];
  // An absent analytics route must not trigger a request for every history row.
  const absentRoute = results[2].status === 'rejected' && results[2].reason.status === 404;
  const fetched = absentRoute || client.supportsAnalytics === false ? [] : await boundedMap(ids, id => client.getReadingAnalytics(id, signal), signal);
  signal.throwIfAborted();
  const analytics = [];
  const references = new Map([...history, ...(latest ? [latest] : [])].map(reading => [reading.readingId, reading]));
  fetched.forEach((item, index) => {
    if (!item.ok) errors.push(`Reading ${ids[index]} analytics: ${item.error.message}`);
    else {
      try {
      assertStream(item.value, selection);
      if (item.value.reading_id !== ids[index]) throw new Error('Analytics reading identity mismatch.');
      const reference = references.get(item.value.reading_id);
      if (reference && (reference.configurationVersion !== item.value.configuration_version || Date.parse(reference.measurementTime) !== Date.parse(item.value.measurement_time))) {
        throw new Error('Analytics configuration or measurement time differs from telemetry.');
      }
      analytics.push(item.value);
      } catch (error) { errors.push(`Reading ${ids[index]} analytics integrity: ${error.message}`); }
    }
  });
  return { details, latest, history, page, latestEnvelope, errors, analyticsAvailable: client.supportsAnalytics !== false, retrievedAt: new Date().toISOString(),
    analytics: analytics.find(a => a.reading_id === latest?.readingId) ?? null,
    completedAnalytics: analytics.find(a => a.reading_id === latestEnvelope?.latest_completed_reading_id) ?? null,
    historyAnalytics: analytics,
    points: thermalPoints(history, analytics),
    pending: activeStatuses.has(latestEnvelope?.latest_telemetry_status) || analytics.some(a => activeStatuses.has(a.status)),
  };
}

// Cancellation invalidates even clients that ignore AbortSignal.
export function createStreamLoader(client, publish, { delay = 5000, maxPolls = 6, schedule = setTimeout, unschedule = clearTimeout } = {}) {
  let generation = 0;
  let controller;
  let timer;
  function cancel() {
    generation++;
    controller?.abort();
    if (timer !== undefined) unschedule(timer);
    timer = undefined;
  }
  async function start(selection) {
    cancel();
    const current = generation;
    controller = new AbortController();
    const signal = controller.signal;
    let retained;
    async function execute(poll = 0) {
      if (current !== generation) return;
      publish({ phase: 'loading', poll, snapshot: retained });
      try {
        const snapshot = await loadStreamSnapshot(client, selection, signal);
        if (current !== generation) return;
        retained = snapshot;
        const polling = snapshot.pending && !snapshot.errors.length && poll < maxPolls;
        publish({ phase: 'ready', snapshot, polling, poll, exhausted: snapshot.pending && poll >= maxPolls });
        if (polling) timer = schedule(() => execute(poll + 1), delay);
      } catch (error) {
        if (current !== generation || signal.aborted) return;
        if (retained) retained = {
          ...retained, analytics: null, completedAnalytics: null, latestEnvelope: null,
          historyAnalytics: [],
          points: thermalPoints(retained.history, []).map(point => ({ ...point, reasons: ['refresh_failed'] })),
          pending: false, errors: [],
        };
        publish({ phase: 'error', message: error.message, snapshot: retained });
      }
    }
    return execute();
  }
  return { start, cancel };
}
