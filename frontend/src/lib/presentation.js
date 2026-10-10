export function displayId(value, fallback = 'Unavailable') {
  if (value == null || value === '') return fallback;
  const label = String(value);
  if (/^sample-\d+$/.test(label)) return `R-${label.slice(7)}`;
  return label.replace(/^SAMPLE-/, '');
}
export const displayLocation = value => value ? String(value).replace(/^Sample substation/, 'Substation') : 'Location unavailable';
export const displayStatus = value => !value || value === 'sample' ? '—' : value;
export const displaySource = value => ({ device: 'Device', simulator: 'Stored run', file_replay: 'File replay' }[value] ?? 'Unavailable');
export function displayMetricReason(metric) {
  if (metric?.value == null && metric?.reason?.startsWith('Illustrative')) return 'Channel unavailable.';
  return metric?.state === 'Sample' ? 'Sample UI illustration.' : metric?.reason?.replace(/^Sample[^.]*\.\s*/, '') || 'Channel unavailable.';
}
export function displayRatingState(rating) {
  if (rating?.factors?.some(factor => factor.breached)) return 'Limit breach';
  if (rating?.score == null) return 'Insufficient evidence';
  return 'Condition overview';
}
