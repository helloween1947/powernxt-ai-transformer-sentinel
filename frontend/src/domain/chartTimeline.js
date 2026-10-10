// Snap to a retrieved record by measurement time, never by array spacing or
// interpolated values. Missing sensor values still belong to a real record.
export function nearestChartReading(points, fraction) {
  if (!Number.isFinite(fraction)) return null;
  const records = points.filter(point => point.readingId != null && Number.isFinite(Date.parse(point.timestamp)))
    .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  if (!records.length) return null;
  const start = Date.parse(records[0].timestamp);
  const end = Date.parse(records.at(-1).timestamp);
  const target = start + Math.max(0, Math.min(1, fraction)) * (end - start);
  return records.reduce((nearest, point) => Math.abs(Date.parse(point.timestamp) - target) < Math.abs(Date.parse(nearest.timestamp) - target) ? point : nearest);
}
