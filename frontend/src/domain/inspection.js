import { capabilities } from '../data/capabilities.js';
export function inspectHistoryRecord(snapshot, readingId, mode) {
  const reading = snapshot?.history?.find(item => item.readingId === readingId);
  if (!reading) return { snapshot, historical: false };
  // History is already stream-validated by the canonical loader. Never look up
  // another page/stream or silently pair its latest result with this record.
  if (reading.assetId !== snapshot.details?.asset_id || reading.source !== snapshot.latest?.source || (reading.runId ?? null) !== (snapshot.latest?.runId ?? null)) return { snapshot, historical: false };
  const analytics = mode === 'sample' && reading.sampleValues ? { status: 'sample', result: null, metrics: capabilities.filter(metric => metric.path).map(metric => ({ path: metric.path, unit: metric.unit, value: reading.sampleValues[metric.id] ?? null, status: 'available', reasons: [] })) } : snapshot.historyAnalytics?.find(item => item.reading_id === readingId) ?? null;
  return { historical: true, snapshot: { ...snapshot, latest: reading, analytics } };
}
export function metricTrend(id) {
  if (id.startsWith('voltage_')) return 'voltage';
  if (id.startsWith('current_')) return 'current';
  if (['capacity_loading', 'phase_loading', 'thermal_load'].includes(id)) return 'loading';
  if (id === 'apparent_power') return 'power';
  if (id === 'oil_level_pct') return 'oil_level';
  if (id === 'thermal_residual') return 'residual';
  return 'temperature';
}
