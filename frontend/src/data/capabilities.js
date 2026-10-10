import { usableMeasurement } from '../services/telemetryAdapter.js';

export const anchors = {
  terminals: { label: 'Electrical terminals', position: [-1.12, 2.45, 0.2], description: 'Phase measurements are associated with the asset. Physical sensor placement is not supplied.' },
  tank: { label: 'Oil tank & cooling', position: [-1.1, 0.6, 0.9], description: 'Oil temperature and top-oil estimates describe the oil system. Sensor mounting location is unknown.' },
  conservator: { label: 'Oil system', position: [1.05, 2.65, -0.2], description: 'Oil level is a measured channel. A low level does not establish a leak.' },
  environment: { label: 'Environment', position: [1.7, 0.9, 0.6], description: 'Ambient temperature is an asset-level measurement. Sensor location is not recorded.' },
  base: { label: 'Asset capacity', position: [1.2, -0.45, 0.6], description: 'Rated kVA is the total three-phase apparent-power rating. Loading is supplied by stored analytics.' },
};

const measured = (id, label, unit, category, anchor, digits = 1) => ({ id, label, unit, category, anchor, digits, type: 'measured' });
const derived = (id, label, unit, category, anchor, path, type = 'derived', digits = 1) => ({ id, label, unit, category, anchor, path, type, digits });
const future = (id, label, unit, category, reason, readiness = 'Planned') => ({ id, label, unit, category, type: 'future', reason, readiness });

const descriptors = [
  ...['r', 'y', 'b'].map(phase => measured(`voltage_${phase}_v`, `${phase.toUpperCase()}-phase voltage`, 'V', 'Electrical', 'terminals')),
  ...['r', 'y', 'b'].map(phase => measured(`current_${phase}_a`, `${phase.toUpperCase()}-phase current`, 'A', 'Electrical', 'terminals')),
  derived('capacity_loading', 'Capacity loading', '%', 'Electrical', 'base', 'electrical_metrics.capacity_loading_pct'),
  derived('phase_loading', 'Worst-phase loading', '%', 'Electrical', 'terminals', 'electrical_metrics.max_phase_loading_pct'),
  derived('apparent_power', 'Apparent power', 'kVA', 'Electrical', 'base', 'electrical_metrics.apparent_power_kva'),
  derived('current_imbalance', 'Current magnitude imbalance', '%', 'Electrical', 'terminals', 'electrical_metrics.current_magnitude_imbalance_pct', 'derived', 2),
  derived('voltage_imbalance', 'Voltage magnitude imbalance', '%', 'Electrical', 'terminals', 'electrical_metrics.voltage_magnitude_imbalance_pct', 'derived', 2),
  measured('oil_temperature_c', 'Oil temperature', '°C', 'Thermal', 'tank'),
  measured('ambient_temperature_c', 'Ambient temperature', '°C', 'Thermal', 'environment'),
  derived('estimated_oil', 'Estimated top-oil', '°C', 'Thermal', 'tank', 'thermal_assessment.predicted_top_oil_temperature_c', 'estimated'),
  derived('thermal_residual', 'Thermal residual', '°C', 'Thermal', 'tank', 'thermal_assessment.thermal_residual_c', 'derived', 2),
  derived('thermal_load', 'Thermal load', 'pu', 'Thermal', 'base', 'electrical_metrics.thermal_load_pu', 'derived', 3),
  measured('oil_level_pct', 'Oil level', '%', 'Condition', 'conservator'),
  { id: 'rated_capacity', label: 'Rated capacity', unit: 'kVA', category: 'Electrical', anchor: 'base', type: 'configuration', digits: 0 },
  future('active_power', 'Active power', 'kW', 'Electrical', 'Requires a power channel or phase-angle inputs.'),
  future('reactive_power', 'Reactive power', 'kvar', 'Electrical', 'Requires a genuine power meter or synchronized phase-angle measurements.'),
  future('power_factor', 'Power factor', '', 'Electrical', 'Magnitude-only telemetry cannot establish power factor.', 'Unsupported'),
  future('frequency', 'Frequency', 'Hz', 'Electrical', 'Requires a frequency measurement and quality contract.'),
  future('thd', 'Harmonic distortion', '%', 'Electrical', 'Requires harmonic measurements and an agreed THD definition.'),
  future('impedance', 'Transformer impedance', '%', 'Electrical', 'Requires verified nameplate impedance and base quantities.'),
  future('short_circuit', 'Short-circuit capacity', 'MVA', 'Electrical', 'Requires an approved system boundary and network impedance model.'),
  future('hotspot', 'Winding hot-spot', '°C', 'Thermal', 'The adopted top-oil model does not assess winding hot-spot.', 'Unsupported'),
  future('winding', 'Measured winding temperature', '°C', 'Thermal', 'Requires a winding sensor channel.'),
  future('bushing', 'Bushing temperature', '°C', 'Thermal', 'Requires a bushing sensor channel.'),
  future('overload_duration', 'Permissible overload duration', 'min', 'Thermal', 'Requires a validated duration-dependent thermal and cooling model.', 'Unsupported'),
  future('thermal_capacity', 'Thermal capacity', '', 'Thermal', 'Not assessed by the current simplified top-oil model.', 'Unsupported'),
  future('oil_leak', 'Oil leak detection', '', 'Condition', 'Dedicated sensor or verified inspection evidence is required.'),
  future('pressure', 'Tank pressure', 'kPa', 'Condition', 'No pressure channel or confirmed mounting location is available.'),
  future('response_time', 'Sensor response time', 'ms', 'Condition', 'Requires documented sensor metadata. Telemetry age is a separate concept.'),
  future('vibration', 'Vibration', '', 'Condition', 'Requires a mechanical sensor and an agreed measurement unit.'),
  future('correlation', 'Electrical / mechanical analysis', '', 'Condition', 'Requires synchronized measurements and a defined validated method.'),
  future('health', 'Health index', '', 'Condition', 'Not assessed by current model. No validated health methodology.', 'Unsupported'),
  future('fault', 'Fault prediction', '', 'Condition', 'No validated fault model or probability is provided.', 'Unsupported'),
  future('rul', 'Remaining useful life', '', 'Condition', 'Requires validated ageing history, method and uncertainty.', 'Unsupported'),

  { id: 'condition_rating', label: 'Condition rating', unit: '/100', category: 'Condition', anchor: 'base', type: 'prototype', readiness: 'Prototype', reason: 'Unvalidated frontend policy; opens its factor explanation. Never an authoritative Health Index.' },
  future('ageing', 'Insulation ageing', '', 'Condition', 'Requires validated cumulative thermal history and an ageing methodology.', 'Unsupported'),
  future('lifespan', 'Lifespan assessment', '', 'Condition', 'No validated service-life model is supplied.', 'Unsupported'),
  future('maintenance_recommendation', 'Predictive maintenance evidence', '', 'Condition', 'Requires approved evidence-linked recommendation rules and incident provenance.'),
  future('incident_lifecycle', 'Incident lifecycle', '', 'Condition', 'No persisted incident registry or authenticated action contract exists in this workspace.'),
  future('whatif_result', 'What-if result', '', 'Thermal', 'No scenario execution/persistence contract exists in this workspace.'),
  future('processing_duration', 'Analytics processing duration', 'ms', 'Condition', 'A storage timestamp is not a duration. Worker start/end instrumentation is required.'),
  derived('telemetry_latency', 'Telemetry arrival delay', 's', 'Condition', 'environment', null, 'transport', 2),
];

const futureAnchors = { oil_leak: 'conservator', pressure: 'tank', response_time: 'tank', vibration: 'base', correlation: 'base', hotspot: 'tank', winding: 'tank', bushing: 'terminals' };
export const capabilities = descriptors.map(metric => ({ ...metric,
  anchor: metric.anchor ?? futureAnchors[metric.id] ?? (metric.category === 'Electrical' ? 'terminals' : metric.category === 'Thermal' ? 'tank' : 'base'),
  readiness: metric.readiness ?? 'Supported',
  expectedSource: metric.type === 'measured' ? 'Normalized telemetry channel with quality' : metric.type === 'derived' || metric.type === 'estimated' ? 'Compatible completed stored analytics' : metric.type === 'configuration' ? 'Versioned asset configuration' : metric.type === 'transport' ? 'Measurement and arrival timestamps' : 'Proposed sensor or validated model contract',
  placementVerified: false,
}));

export function resolveMetrics(snapshot, mode = 'live', assessment = null) {
  const reading = snapshot?.latest;
  const analytics = snapshot?.analytics;
  const config = snapshot?.details?.current_configuration;
  return capabilities.map(metric => {
    let value = null;
    let reason = metric.reason;
    let quality = null;
    let timestamp = reading?.measurementTime;
    if (metric.type === 'measured') {
      const raw = reading?.measurements[metric.id];
      quality = reading?.measurementQuality?.[metric.id] ?? (raw == null ? 'missing' : 'unknown');
      const flags = reading?.qualityFlags?.[metric.id] ?? [];
      value = usableMeasurement(reading, metric.id);
      reason = !reading ? 'No reading retrieved for this stream.' : value == null ? `Missing or unusable channel${flags.length ? `: ${flags.join(', ')}` : ''}.` : quality === 'suspect' ? 'Sensor marks this reading as suspect.' : flags.length ? flags.join(', ') : 'Normalized measurement. Physical sensor location is unknown.';
    } else if (metric.path) {
      const stored = analytics?.metrics?.find(item => item.path === metric.path);
      if (stored?.unit === metric.unit && Number.isFinite(stored.value)) value = stored.value;
      reason = value == null ? stored?.reasons?.join(', ') || 'Stored analytics is unavailable for this reading.' : metric.type === 'estimated' ? 'Simplified top-oil estimate. Model assumptions are shown in provenance.' : 'Derived from the stored reading and its configuration.';
    } else if (metric.type === 'prototype') {
      const bound = assessment?.mode === mode && assessment?.identity?.assetId === reading?.assetId && assessment?.identity?.readingId === reading?.readingId && assessment?.identity?.configurationVersion === reading?.configurationVersion;
      value = bound && Number.isFinite(assessment?.score) ? assessment.score : null;
      reason = `Prototype · rules-based · not field-validated. ${assessment?.state ?? 'Not assessed'}. ${assessment?.coverage ?? 0}% eligible evidence coverage; not a Health Index.`;
    } else if (metric.type === 'transport') {
      const arrival = Date.parse(reading?.arrivalTime);
      const measured = Date.parse(reading?.measurementTime);
      value = Number.isFinite(arrival) && Number.isFinite(measured) && arrival >= measured ? (arrival - measured) / 1000 : null;
      reason = value == null ? 'No valid measurement/arrival pair. Sensor response and worker duration are separate.' : 'Arrival minus measurement time; clock synchronization affects this transport estimate.';
    } else if (metric.type === 'configuration') {
      value = Number.isFinite(config?.rated_kva) ? config.rated_kva : null;
      timestamp = config?.created_at;
      reason = value == null ? 'Asset rating has not been configured.' : `Configuration v${config.version}; ${config.parameter_provenance?.rated_kva ?? 'provenance unavailable'}. Total three-phase apparent-power rating.`;
    }
    const state = metric.type === 'future' ? metric.readiness : value == null ? 'Unavailable' : mode === 'sample' ? 'Sample' : metric.type === 'estimated' ? 'Estimated' : metric.type === 'configuration' ? 'Configured' : metric.type === 'prototype' ? 'Prototype' : ['derived', 'transport'].includes(metric.type) ? 'Derived' : 'Measured';
    if (mode === 'sample' && !['future', 'prototype'].includes(metric.type)) reason = `Illustrative ${metric.type === 'configuration' ? 'assumed configuration' : metric.type === 'estimated' ? 'estimate' : 'sample value'}. No sensor or model execution. ${value == null ? 'This channel is missing in the sample.' : ''}`;
    return { ...metric, value, state, reason, quality, timestamp, readingId: reading?.readingId, configurationVersion: reading?.configurationVersion, modelVersion: analytics?.result?.model_version ?? null };
  });
}

export function calloutMetrics(metrics, category = 'All', mobile = false) {
  const ids = category === 'Electrical' ? ['voltage_r_v', 'current_r_a', 'capacity_loading', 'apparent_power'] : category === 'Thermal' ? ['oil_temperature_c', 'estimated_oil', 'ambient_temperature_c', 'thermal_residual'] : category === 'Condition' ? ['oil_level_pct', 'oil_temperature_c'] : ['voltage_r_v', 'oil_temperature_c', 'oil_level_pct', 'capacity_loading'];
  return ids.slice(0, mobile ? 2 : 4).map(id => metrics.find(metric => metric.id === id)).filter(Boolean);
}
