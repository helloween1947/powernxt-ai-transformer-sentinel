// Presentation labels only: retain canonical identifiers, mode and provenance
// in adapters, state, requests and exported records.
export function displayId(value, fallback = 'Unavailable') {
  if (value == null) return fallback;
  return String(value).replace(/^SAMPLE-TX-/, 'TX-').replace(/^sample-(\d+)$/, 'R-$1').replace(/^sample-task-/, 'task-').replace(/^sample-c-/, 'alert-');
}
export function displayLocation(value) {
  return value?.replace(/^Sample substation/, 'Substation').replace(/^Sample /, '') ?? 'Location unavailable';
}
export function displayStatus(value) {
  return value === 'sample' ? '—' : value ?? 'Unavailable';
}
export function displaySource(value) {
  return ({ simulator: 'Stored run', file_replay: 'Archive', device: 'Device' })[value] ?? value ?? 'Unavailable';
}
export function displayMetricReason(metric) {
  if ((metric?.state === 'Sample' || metric?.reason?.startsWith('Illustrative ')) && metric.type !== 'prototype') return metric.value == null ? 'Channel unavailable.' : '';
  if (metric?.type === 'prototype') return 'Based on configured limits and available measurements.';
  return metric?.reason ?? '';
}
export function displayRatingState(result) {
  if (['Sample prototype', 'Prototype assessment', 'Stored simulation / replay'].includes(result.state)) return result.breaches.length ? 'Limit breach' : 'Condition overview';
  return result.state;
}
