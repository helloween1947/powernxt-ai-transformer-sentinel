export function csvCell(value) {
  let text = value == null ? '' : String(value);
  // Prevent spreadsheet formula injection from user-controlled IDs and notes.
  if (typeof value === 'string' && /^[\s]*[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}

export function exportRows(snapshot, mode) {
  return (snapshot?.history ?? []).map(reading => {
    const point = snapshot.points?.find(item => item.readingId === reading.readingId);
    return {
      scope: mode === 'sample' ? 'Sample UI illustration' : 'Retrieved history page',
      asset_id: reading.assetId, reading_id: reading.readingId, source: reading.source, run_id: reading.runId,
      configuration_version: reading.configurationVersion, measurement_time_utc: reading.measurementTime, arrival_time_utc: reading.arrivalTime,
      ...reading.measurements, quality_flags: JSON.stringify(reading.qualityFlags), measurement_quality: JSON.stringify(reading.measurementQuality),
      out_of_order: reading.outOfOrder, processing_status: point?.status ?? reading.processingJobStatus,
      estimated_top_oil_c: point?.predicted ?? null, thermal_residual_c: point?.residual ?? null,
      capacity_loading_pct: point?.capacityLoading ?? null, worst_phase_loading_pct: point?.phaseLoading ?? null, apparent_power_kva: point?.apparentPower ?? null,
      analytics_model_id: point?.modelId ?? '', analytics_model_version: point?.modelVersion ?? '',
      analytics_parameter_version: point?.parameterVersion ?? '', analytics_processed_at_utc: point?.processedAt ?? '',
      analytics_unavailable_reasons: point?.reasons?.join('; ') ?? '',
    };
  });
}
export function reportCsv(snapshot, mode) {
  const rows = exportRows(snapshot, mode);
  if (!rows.length) return null;
  const headers = Object.keys(rows[0]);
  return [headers.map(csvCell).join(','), ...rows.map(row => headers.map(key => csvCell(row[key])).join(','))].join('\r\n');
}
export function downloadReport(snapshot, mode) {
  const csv = reportCsv(snapshot, mode);
  if (!csv) return false;
  const url = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `powernxt-${mode}-${snapshot.details.asset_id.replace(/[^a-zA-Z0-9._-]/g, '_')}-page-${snapshot.page.offset}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return true;
}
