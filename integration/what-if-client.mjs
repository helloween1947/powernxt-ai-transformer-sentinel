// Reference client for C. It does not wire the prototype UI or invent capabilities.
export function adaptWhatIf(body) {
  if (body?.schema_version !== 'what-if-response-1.0.0'
      || body.units?.temperature !== 'C' || body.units?.elapsed_time !== 's'
      || body.units?.thermal_load !== 'pu') throw new Error('Unsupported what-if contract or units');
  const start = Date.parse(body.state.measurement_time);
  const baseline = body.baseline.points;
  const reduced = body.reduced_load.points;
  if (!Number.isFinite(start) || baseline.length !== reduced.length
      || baseline.length < 2 || baseline.length > 97) throw new Error('Invalid what-if state/sampling');
  const points = baseline.map((point, index) => {
    const other = reduced[index];
    if (point.elapsed_s !== other.elapsed_s || !Number.isFinite(point.elapsed_s)
        || !Number.isFinite(point.estimated_top_oil_temperature_c)
        || !Number.isFinite(other.estimated_top_oil_temperature_c)) throw new Error('Invalid aligned scenario point');
    return { timestamp: new Date(start + point.elapsed_s * 1000).toISOString(),
      elapsed_s: point.elapsed_s, baseline: point.estimated_top_oil_temperature_c,
      alternative: other.estimated_top_oil_temperature_c };
  });
  if (points[0].elapsed_s !== 0 || points[0].baseline !== points[0].alternative)
    throw new Error('Scenario initial conditions differ');
  // Crossing status and null times are retained verbatim; null never means zero.
  return { stateRef: body.state.state_ref, origin: body.state.measurement_time,
    configuration: body.configuration, model: body.model, points,
    baselineCrossing: body.baseline.limit_crossing,
    reducedLoadCrossing: body.reduced_load.limit_crossing,
    finalDifferenceC: body.final_temperature_difference_c,
    assumptions: body.assumptions.join(' ') };
}

export async function postWhatIf(baseUrl, assetId, request, signal) {
  const response = await fetch(`${baseUrl.replace(/\/$/, '')}/api/v1/assets/${encodeURIComponent(assetId)}/what-if`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request), signal,
  });
  const body = await response.json();
  if (!response.ok) {
    const error = new Error(body.detail?.message || `What-if request failed (${response.status})`);
    error.status = response.status;
    error.code = body.detail?.code;
    throw error;
  }
  return { response: body, chart: adaptWhatIf(body) };
}
