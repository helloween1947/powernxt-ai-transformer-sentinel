export function adaptWhatIf(body) {
  if (
    body?.schema_version !== 'what-if-response-1.0.0' ||
    body.units?.temperature !== 'C' ||
    body.units?.elapsed_time !== 's' ||
    body.units?.thermal_load !== 'pu'
  ) {
    throw new Error('Unsupported what-if contract or units');
  }

  const start = Date.parse(body.state.measurement_time);
  const baseline = body.baseline.points;
  const reduced = body.reduced_load.points;

  if (
    !Number.isFinite(start) ||
    baseline.length !== reduced.length ||
    baseline.length < 2 ||
    baseline.length > 97
  ) {
    throw new Error('Invalid what-if state or scenario sampling');
  }

  const points = baseline.map((point, index) => {
    const other = reduced[index];
    if (
      point.elapsed_s !== other.elapsed_s ||
      !Number.isFinite(point.elapsed_s) ||
      !Number.isFinite(point.estimated_top_oil_temperature_c) ||
      !Number.isFinite(other.estimated_top_oil_temperature_c)
    ) {
      throw new Error('Invalid aligned scenario point');
    }
    return {
      timestamp: new Date(start + point.elapsed_s * 1000).toISOString(),
      elapsed_s: point.elapsed_s,
      baseline: point.estimated_top_oil_temperature_c,
      alternative: other.estimated_top_oil_temperature_c,
    };
  });

  if (points[0].elapsed_s !== 0 || points[0].baseline !== points[0].alternative) {
    throw new Error('Scenario initial conditions differ');
  }

  return {
    stateRef: body.state.state_ref,
    origin: body.state.measurement_time,
    configuration: body.configuration,
    model: body.model,
    points,
    baselineCrossing: body.baseline.limit_crossing,
    reducedLoadCrossing: body.reduced_load.limit_crossing,
    baselineFinal: body.baseline.final_top_oil_temperature_c,
    baselinePeak: body.baseline.peak_top_oil_temperature_c,
    reducedFinal: body.reduced_load.final_top_oil_temperature_c,
    reducedPeak: body.reduced_load.peak_top_oil_temperature_c,
    finalDifferenceC: body.final_temperature_difference_c,
    assumptions: Array.isArray(body.assumptions) ? body.assumptions.join(' ') : (body.assumptions ?? ''),
    configuredLimit: body.configured_top_oil_limit_c ?? null,
  };
}

export function validateWhatIfRequest({
  source = 'device',
  runId = null,
  stateRef = null,
  durationS = 7200,
  ambientC = 25,
  baselineLoadPu = 1.0,
  reducedLoadPu = 0.8,
}) {
  const duration = Number(durationS);
  const ambient = Number(ambientC);
  const baseLoad = Number(baselineLoadPu);
  const redLoad = Number(reducedLoadPu);

  if (!Number.isFinite(duration) || duration <= 0 || duration > 86400) {
    throw new Error('Duration must be between 1 and 86400 seconds.');
  }
  if (!Number.isFinite(ambient) || ambient < -50 || ambient > 80) {
    throw new Error('Ambient temperature must be between -50°C and 80°C.');
  }
  if (!Number.isFinite(baseLoad) || baseLoad < 0 || baseLoad > 10) {
    throw new Error('Baseline thermal load must be between 0 and 10 p.u.');
  }
  if (!Number.isFinite(redLoad) || redLoad < 0 || redLoad > 10) {
    throw new Error('Reduced thermal load must be between 0 and 10 p.u.');
  }
  if (redLoad > baseLoad) {
    throw new Error('Reduced load cannot exceed baseline load.');
  }

  const payload = {
    schema_version: 'what-if-request-1.0.0',
    source,
    baseline: {
      duration_s: duration,
      thermal_load_pu: baseLoad,
      ambient_temperature_c: ambient,
    },
    reduced_load: {
      duration_s: duration,
      thermal_load_pu: redLoad,
      ambient_temperature_c: ambient,
    },
  };

  if (source !== 'device') {
    if (!runId || !String(runId).trim()) {
      throw new Error('Simulator and replay sources require a valid Run ID.');
    }
    payload.run_id = String(runId).trim();
  }

  if (stateRef) {
    payload.state_ref = String(stateRef).trim();
  }

  return payload;
}
