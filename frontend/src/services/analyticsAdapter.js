const fields = [
  ['electrical_metrics.capacity_loading_pct', 'Capacity loading', 'capacity_loading_pct', '%'],
  ['electrical_metrics.max_phase_loading_pct', 'Worst-phase loading', 'phase_loading_pct', '%'],
  ['electrical_metrics.apparent_power_kva', 'Apparent power', 'apparent_power_kva', 'kVA'],
  ['electrical_metrics.thermal_load_pu', 'Thermal load', 'thermal_load_pu', 'pu'],
  ['electrical_metrics.current_magnitude_imbalance_pct', 'Current magnitude imbalance', 'magnitude_imbalance', '%'],
  ['electrical_metrics.voltage_magnitude_imbalance_pct', 'Voltage magnitude imbalance', 'magnitude_imbalance', '%'],
  ['thermal_assessment.predicted_top_oil_temperature_c', 'Estimated top-oil temperature', 'oil_temperature', 'C'],
  ['thermal_assessment.thermal_residual_c', 'Observed minus predicted oil temperature', 'thermal_residual', 'C'],
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
  const metadata = payload?.metadata;
  if (metadata && (
    metadata.reading_identity?.reading_id !== envelope.reading_id ||
    metadata.configuration_version !== envelope.configuration_version ||
    metadata.stream?.asset_id !== envelope.asset_id ||
    metadata.stream?.source !== envelope.source ||
    (metadata.stream?.run_id ?? null) !== (envelope.run_id ?? null) ||
    metadata.measurement_time !== envelope.measurement_time ||
    metadata.measurement_source !== envelope.source
  )) throw new Error('Analytics metadata does not match the reading, configuration or stream.');
  return {
    ...envelope,
    assessment: {
      health: null, healthStatus: payload?.condition_contributors?.status ?? 'not_assessed',
      confidence: null, confidenceStatus: payload?.data_confidence?.status ?? 'not_estimated',
      usableChannels: payload?.data_confidence?.usable_required_channel_count ?? null,
      requiredChannels: payload?.data_confidence?.required_channel_count ?? null,
    },
    metrics: payload ? fields.map(([path, label, unitKey, expectedUnit]) => {
      const [group, key] = path.split('.');
      const value = payload[group]?.[key];
      const availability = payload.execution_status?.availability?.[path];
      const rawUnit = metadata?.units?.[unitKey];
      const knownUnit = rawUnit === expectedUnit;
      const unit = rawUnit === 'C' ? '°C' : rawUnit ?? 'Unavailable';
      return { path, label, unit,
        value: knownUnit && availability?.status === 'available' && Number.isFinite(value) ? value : null,
        status: availability?.status ?? 'unavailable',
        reasons: [...(availability?.reasons ?? ['availability_not_provided']), ...(!knownUnit ? [rawUnit == null ? 'units_not_provided' : 'unsupported_metric_unit'] : [])],
      };
    }) : [],
  };
}

export function adaptLatestAnalytics(envelope) {
  if (envelope.schema_version !== '1.0.0') throw new Error('Unsupported analytics API version.');
  if (envelope.result && (envelope.result.schema_version !== 'stored-reading-result-1.1.0' || envelope.result.reading_id !== envelope.latest_completed_reading_id)) {
    throw new Error('Latest completed analytics has unsupported version or reading identity.');
  }
  return { ...envelope,
    lagging: envelope.latest_telemetry_reading_id !== envelope.latest_completed_reading_id,
  };
}
