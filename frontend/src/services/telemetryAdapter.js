export function usableMeasurement(reading, name) {
  const value = reading?.measurements?.[name];
  const flags = reading?.qualityFlags?.[name] ?? [];
  if (!Number.isFinite(value) || reading?.measurementQuality?.[name] === 'bad' || flags.some(flag => ['outside_sanity_range', 'negative_magnitude', 'above_10x_rating', 'bad'].includes(flag))) return null;
  return value;
}

export function adaptTelemetryReading(reading) {
  if (!reading) {
    return null;
  }

  const telemetry = reading.normalized_telemetry ?? {};
  const measurements = telemetry.measurements ?? {};
  if (!['device', 'simulator', 'file_replay'].includes(reading.source) || (reading.source === 'device' && reading.run_id != null) || (reading.source !== 'device' && !reading.run_id)) throw new Error('Stored telemetry has invalid source/run binding.');
  if (telemetry.schema_version !== '1.0.0') throw new Error('Unsupported telemetry schema version.');
  if (telemetry.asset_id !== reading.asset_id || telemetry.source !== reading.source || (telemetry.run_id ?? null) !== (reading.run_id ?? null) || telemetry.configuration_version !== reading.configuration_version || telemetry.message_id !== reading.message_id || Date.parse(telemetry.timestamp) !== Date.parse(reading.measurement_time)) {
    throw new Error('Normalized telemetry identity differs from its stored envelope.');
  }
  if (!Number.isFinite(Date.parse(reading.measurement_time)) || !Number.isFinite(Date.parse(reading.arrival_time))) throw new Error('Telemetry timestamps are invalid.');

  return {
    readingId: reading.id,
    assetId: reading.asset_id,
    source: reading.source,
    runId: reading.run_id ?? null,
    configurationVersion: reading.configuration_version,
    measurementTime: reading.measurement_time,
    arrivalTime: reading.arrival_time,

    measurements: {
      voltage_r_v: measurements.voltage_r_v ?? null,
      voltage_y_v: measurements.voltage_y_v ?? null,
      voltage_b_v: measurements.voltage_b_v ?? null,

      current_r_a: measurements.current_r_a ?? null,
      current_y_a: measurements.current_y_a ?? null,
      current_b_a: measurements.current_b_a ?? null,

      oil_temperature_c:
        measurements.oil_temperature_c ?? null,
      ambient_temperature_c:
        measurements.ambient_temperature_c ?? null,
      oil_level_pct: measurements.oil_level_pct ?? null,
    },

    measurementQuality: telemetry.measurement_quality ?? {},
    qualityFlags: reading.quality_flags ?? {},
    outOfOrder: reading.out_of_order ?? null,

    analyticsStatus: reading.analytics_status ?? 'unavailable',
    processingJobStatus:
      reading.processing_job?.status ?? 'unavailable',
  };
}
