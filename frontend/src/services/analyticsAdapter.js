const fields = [
  ['electrical_metrics.capacity_loading_pct', 'Capacity loading', '%'],
  ['electrical_metrics.max_phase_loading_pct', 'Worst-phase loading', '%'],
  ['electrical_metrics.apparent_power_kva', 'Apparent power', 'kVA'],
  ['electrical_metrics.thermal_load_pu', 'Thermal load', 'pu'],
  ['electrical_metrics.current_magnitude_imbalance_pct', 'Current magnitude imbalance', '%'],
  ['electrical_metrics.voltage_magnitude_imbalance_pct', 'Voltage magnitude imbalance', '%'],
  ['thermal_assessment.predicted_top_oil_temperature_c', 'Estimated top-oil temperature', '°C'],
  ['thermal_assessment.thermal_residual_c', 'Observed minus predicted oil temperature', '°C'],
];

export function adaptReadingAnalytics(envelope) {
  if (envelope.schema_version !== '1.0.0') throw new Error('Unsupported analytics API version.');
  const result = envelope.result;
  if (result && result.schema_version !== 'stored-reading-result-1.1.0') {
    throw new Error('Unsupported analytics result version.');
  }
  if (result && result.reading_id !== envelope.reading_id) {
    throw new Error('Stored analytics references a different reading.');
  }
  const payload = result?.payload;
  return {
    ...envelope,
    metrics: payload ? fields.map(([path, label, unit]) => {
      const [group, key] = path.split('.');
      const value = payload[group]?.[key];
      const availability = payload.execution_status?.availability?.[path];
      return { path, label, unit,
        value: availability?.status === 'available' && Number.isFinite(value) ? value : null,
        status: availability?.status ?? 'unavailable',
        reasons: availability?.reasons ?? ['availability_not_provided'],
      };
    }) : [],
  };
}
