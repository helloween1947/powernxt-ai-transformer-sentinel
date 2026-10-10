import { capabilities } from './capabilities.js';

// Dedicated UI illustrations, independent of the bench workbook and backend.
// Fixed dates preserve the distinction between sample history and device freshness.
export const sampleAssets = [
  { asset_id: 'SAMPLE-TX-01', name: 'Central distribution transformer', location: 'Sample substation · Feeder 04', timezone: 'Asia/Kolkata', current_configuration: { asset_id: 'SAMPLE-TX-01', version: 1, rated_kva: 1000, rated_voltage_v: 11000, rated_current_a: 52.49, voltage_convention: 'line_to_line', measurement_side: 'primary', cooling_type: 'ONAN', created_at: '2026-10-08T06:00:00Z', parameter_provenance: { 'operational_limits.max_top_oil_temp_c': 'assumed', 'operational_limits.max_load_pct': 'assumed', rated_kva: 'assumed', rated_voltage_v: 'assumed', rated_current_a: 'assumed' }, operational_limits: { max_top_oil_temp_c: 105, max_load_pct: 120 } } },
  { asset_id: 'SAMPLE-TX-02', name: 'East distribution transformer', location: 'Sample substation · Feeder 02', timezone: 'Asia/Kolkata', current_configuration: { asset_id: 'SAMPLE-TX-02', version: 1, rated_kva: 500, rated_voltage_v: 11000, rated_current_a: 26.24, voltage_convention: 'line_to_line', measurement_side: 'primary', cooling_type: 'ONAN', created_at: '2026-10-08T06:00:00Z', parameter_provenance: { 'operational_limits.max_top_oil_temp_c': 'assumed', 'operational_limits.max_load_pct': 'assumed', rated_kva: 'assumed' }, operational_limits: { max_top_oil_temp_c: 105, max_load_pct: 120 } } },
];

export function sampleSnapshot(assetId, condition = 'steady', range = '24h') {
  const details = structuredClone(sampleAssets.find(asset => asset.asset_id === assetId) ?? sampleAssets[0]);
  const count = range === '1h' ? 7 : range === '6h' ? 13 : 25;
  const minutes = range === '1h' ? 10 : range === '6h' ? 30 : 60;
  const history = Array.from({ length: count }, (_, index) => {
    const fraction = index / Math.max(count - 1, 1);
    const oil = 49 + 8 * fraction + Math.sin(fraction * 11) * 1.4;
    const lost = condition === 'missing' && index >= count - 3;
    const load = condition === 'overload' ? 102 + 24 * fraction : 58 + 10 * fraction + Math.sin(fraction * 10) * 3;
    const current = details.current_configuration.rated_current_a * load / 100;
    const measurements = {
      voltage_r_v: 10954.1, voltage_y_v: 11058.9, voltage_b_v: 11143.5,
      current_r_a: current * 0.99, current_y_a: current, current_b_a: current * 1.01,
      oil_temperature_c: lost ? null : condition === 'overload' ? oil + fraction * 53 : oil,
      ambient_temperature_c: 27.8 + Math.sin(fraction * 4) * 2,
      oil_level_pct: 81.5 - fraction * 0.3,
    };
    return { readingId: `sample-${index + 1}`, assetId: details.asset_id, source: 'simulator', runId: 'ui-illustration', configurationVersion: 1,
      measurementTime: new Date(Date.parse('2026-10-09T12:30:00Z') - (count - index - 1) * minutes * 60000).toISOString(),
      arrivalTime: null, measurements, measurementQuality: Object.fromEntries(Object.entries(measurements).map(([key, value]) => [key, value == null ? 'missing' : 'good'])),
      qualityFlags: lost ? { oil_temperature_c: ['missing'] } : {}, outOfOrder: false, analyticsStatus: 'sample', processingJobStatus: 'sample',
      sampleValues: { capacity_loading: load, phase_loading: load * 1.01, apparent_power: load * details.current_configuration.rated_kva / 100, current_imbalance: 1, voltage_imbalance: 0.89, estimated_oil: oil - 0.8, thermal_residual: lost ? null : measurements.oil_temperature_c - (oil - 0.8), thermal_load: load / 100 },
    };
  });
  const latest = history.at(-1);
  const analytics = { status: 'sample', metrics: capabilities.filter(metric => metric.path).map(metric => ({ path: metric.path, label: metric.label, unit: metric.unit, value: latest.sampleValues[metric.id] ?? null, status: 'available', reasons: [] })), result: null };
  return { details, latest, history, analytics, completedAnalytics: null, latestEnvelope: null, page: { items: history, offset: 0, limit: count }, errors: [], pending: false,
    points: history.map(reading => ({ readingId: reading.readingId, timestamp: reading.measurementTime, measured: reading.measurements.oil_temperature_c, predicted: reading.sampleValues.estimated_oil, residual: reading.sampleValues.thermal_residual, capacityLoading: reading.sampleValues.capacity_loading, phaseLoading: reading.sampleValues.phase_loading, apparentPower: reading.sampleValues.apparent_power, configurationVersion: 1, status: 'sample', reasons: Object.values(reading.qualityFlags).flat() })),
  };
}
