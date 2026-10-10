import { useEffect, useMemo, useState } from 'react';
import { createTelemetryClient } from '../services/telemetryClient.js';
import { createStreamLoader } from '../services/storedStream.js';
import { sampleAssets, sampleSnapshot } from '../data/workstationSample.js';

export function useAssets(mode, baseUrl, offset, refresh) {
  const [state, setState] = useState({ phase: 'loading', items: [] });
  const key = `${baseUrl}:${offset}:${refresh}`;
  useEffect(() => {
    if (mode !== 'live') return;
    const controller = new AbortController();
    const client = createTelemetryClient(baseUrl);
    async function load() {
      try {
        const page = await client.getAssetPage(20, offset, controller.signal);
        if (!controller.signal.aborted) setState({ ...page, phase: 'ready', key });
      } catch (error) {
        if (!controller.signal.aborted) setState({ phase: 'error', items: [], message: error.message, key });
      }
    }
    load();
    return () => controller.abort();
  }, [mode, baseUrl, offset, key]);
  return mode === 'sample' ? { phase: 'ready', items: sampleAssets, offset: 0 } : state.key === key ? state : { phase: 'loading', items: [] };
}

export function useWorkstation({ mode, baseUrl, assetId, source, runId, range, offset, condition, refresh, analyticsEnabled = false }) {
  const [state, setState] = useState({ phase: 'idle' });
  const key = JSON.stringify({ mode, baseUrl, assetId, source, runId, range, offset, refresh, analyticsEnabled });
  const cacheScope = JSON.stringify({ baseUrl, assetId, source, runId });
  const client = useMemo(() => {
    const canonical = createTelemetryClient(baseUrl);
    const cache = new Map();
    return { ...canonical, supportsAnalytics: analyticsEnabled, async getReadingAnalytics(id, signal) {
      const cacheKey = `${cacheScope}:${id}`;
      if (cache.has(cacheKey)) return cache.get(cacheKey);
      const result = await canonical.getReadingAnalytics(id, signal);
      if (['completed', 'unavailable'].includes(result.status)) {
        if (cache.size >= 200) cache.delete(cache.keys().next().value);
        cache.set(cacheKey, result);
      }
      return result;
    } };
  }, [baseUrl, cacheScope, analyticsEnabled]);
  useEffect(() => {
    if (mode !== 'live' || !assetId || (source !== 'device' && !runId.trim())) return;
    const hours = { '1h': 1, '6h': 6, '24h': 24 }[range];
    let timer;
    let stopped = false;
    const loader = createStreamLoader(client, next => {
      if (stopped) return;
      setState({ ...next, key });
      if (next.phase === 'ready' && !next.polling && !next.exhausted && !next.snapshot.errors.length) {
        clearTimeout(timer);
        timer = setTimeout(reload, 30000);
      }
    });
    function reload() {
      const end = new Date().toISOString();
      const start = hours ? new Date(Date.parse(end) - hours * 3600000).toISOString() : undefined;
      loader.start({ assetId, source, runId: source === 'device' ? null : runId.trim(), offset, start, end });
    }
    reload();
    return () => { stopped = true; clearTimeout(timer); loader.cancel(); };
  }, [mode, assetId, source, runId, offset, range, client, key]);
  const sample = useMemo(() => mode === 'sample' ? sampleSnapshot(assetId, condition, range) : null, [mode, assetId, condition, range]);
  if (sample) return { phase: 'ready', snapshot: sample };
  if (!assetId) return { phase: 'idle' };
  if (source !== 'device' && !runId.trim()) return { phase: 'idle', message: 'Enter the run ID for this simulator or replay stream.' };
  return state.key === key ? state : { phase: 'loading' };
}
