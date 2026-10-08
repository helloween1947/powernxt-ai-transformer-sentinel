export function adaptTelemetryReading(reading) {
  if (!reading) {
    return null;
  }

  const telemetry = reading.normalized_telemetry ?? {};
  const measurements = telemetry.measurements ?? {};

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