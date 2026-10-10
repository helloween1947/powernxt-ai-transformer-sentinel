import { usableMeasurement } from '../services/telemetryAdapter.js';

// Demonstration UX policy. These weights, warning zones and sub-scores are NOT
// protection settings, calibrated safety classes or a transformer health model.
export const CONDITION_POLICY = Object.freeze({
  version: 'condition-rating-prototype-v1',
  weights: Object.freeze({ loading: 35, thermal: 35, electrical: 15, oil: 15 }),
  units: Object.freeze({ loading: '%', thermal: '°C', electrical: '%', oil: '%' }),
  warningRatio: 0.9, minimumFactors: 2, minimumCoverage: 50, staleAfterMs: 120000,
  scores: Object.freeze({ normal: 100, warning: 70, critical: 25 }),
});
const sources = new Set(['nameplate', 'measured', 'assumed', 'simulated']);
const sameIdentity = (a, b) => a && b && a.assetId === b.assetId && a.source === b.source && (a.runId ?? null) === (b.runId ?? null) && a.configurationVersion === b.configurationVersion && a.readingId === b.readingId && Date.parse(a.measurementTime) === Date.parse(b.measurementTime);
export function classifyFactor(value, limit, relation = 'maximum') {
  if (!Number.isFinite(value) || !Number.isFinite(limit) || limit <= 0 || !['maximum', 'minimum'].includes(relation)) return null;
  const breached = relation === 'maximum' ? value > limit : value < limit;
  const warning = relation === 'maximum' ? value >= limit * CONDITION_POLICY.warningRatio : value <= limit / CONDITION_POLICY.warningRatio;
  return breached ? 'critical' : warning ? 'warning' : 'normal';
}
export function computeConditionRating({ factors = [], identity, mode = 'live', now = Date.now() }) {
  const seen = new Set();
  const evaluated = Object.entries(CONDITION_POLICY.weights).map(([id, weight]) => {
    const matches = factors.filter(factor => factor.id === id);
    const factor = matches[0] ?? { id, label: id, reason: 'No supported measurement and configured rule.' };
    let reason = factor.reason;
    if (matches.length > 1 || seen.has(id)) reason = 'Duplicate factor evidence.';
    seen.add(id);
    if (factor.value == null || !Number.isFinite(factor.value)) reason = reason || 'Measurement missing or unusable.';
    else if (factor.unit !== CONDITION_POLICY.units[id]) reason = 'Unsupported factor unit.';
    else if (!sameIdentity(factor.identity, identity)) reason = 'Conflicting reading/configuration/stream provenance.';
    else if (factor.quality !== 'good') reason = `Channel quality is ${factor.quality ?? 'unknown'}; excluded from scoring.`;
    else if (!factor.ruleVerified || !sources.has(factor.limitProvenance)) reason = 'A returned configured/approved rule with provenance is required.';
    else if (classifyFactor(factor.value, factor.limit, factor.relation) == null) reason = 'Configured limit or comparison is unsupported.';
    if (!['live', 'sample'].includes(mode) || !identity || !Number.isFinite(Date.parse(identity.measurementTime)) || !identity.assetId || !['device', 'simulator', 'file_replay'].includes(identity.source) || (identity.source === 'device' ? identity.runId != null : !identity.runId) || !(Number.isInteger(identity.readingId) && identity.readingId > 0 || mode === 'sample' && typeof identity.readingId === 'string' && identity.readingId.length > 0) || !Number.isInteger(identity.configurationVersion) || identity.configurationVersion < 1) reason = 'Reading identity or measurement time is missing.';
    const eligible = !reason;
    const classification = eligible ? classifyFactor(factor.value, factor.limit, factor.relation) : null;
    return { ...factor, id, weight, eligible, reason: reason || null, classification, subScore: classification ? CONDITION_POLICY.scores[classification] : null, breached: classification === 'critical' };
  });
  const eligible = evaluated.filter(factor => factor.eligible);
  const baseWeight = Object.values(CONDITION_POLICY.weights).reduce((a, b) => a + b, 0);
  const availableWeight = eligible.reduce((a, b) => a + b.weight, 0);
  const coverage = availableWeight / baseWeight * 100;
  const sufficient = eligible.length >= CONDITION_POLICY.minimumFactors && coverage >= CONDITION_POLICY.minimumCoverage;
  const score = sufficient ? eligible.reduce((sum, factor) => sum + factor.subScore * factor.weight, 0) / availableWeight : null;
  const ageMs = Number.isFinite(Date.parse(identity?.measurementTime)) ? now - Date.parse(identity.measurementTime) : null;
  const stale = mode === 'live' && identity?.source === 'device' && ageMs > CONDITION_POLICY.staleAfterMs;
  const future = ageMs != null && ageMs < -30000;
  return { policyVersion: CONDITION_POLICY.version, score: future ? null : score, coverage, eligibleCount: eligible.length, factors: evaluated,
    breaches: eligible.filter(factor => factor.breached), mode, identity, evidenceTime: identity?.measurementTime ?? null,
    stale, evaluatedAt: identity && Number.isFinite(now) ? new Date(now).toISOString() : null, state: future ? 'Invalid evidence time' : !sufficient ? 'Insufficient evidence' : stale ? 'Stale evidence' : mode === 'sample' ? 'Sample prototype' : identity?.source !== 'device' ? 'Stored simulation / replay' : 'Prototype assessment',
    band: future || score == null ? null : score >= 85 ? 'Lower indication' : score >= 50 ? 'Review evidence' : 'Elevated indication' };
}

export function conditionRating(snapshot, mode, now = Date.now()) {
  const reading = snapshot?.latest;
  const config = snapshot?.details?.current_configuration;
  const identity = reading && { assetId: reading.assetId, source: reading.source, runId: reading.runId, readingId: reading.readingId, configurationVersion: reading.configurationVersion, measurementTime: reading.measurementTime };
  const configBound = config?.asset_id === reading?.assetId && config?.version === reading?.configurationVersion;
  const sample = mode === 'sample' && reading?.assetId?.startsWith('SAMPLE-') && snapshot?.analytics?.status === 'sample';
  const analytics = snapshot?.analytics;
  const result = analytics?.result;
  const loading = analytics?.metrics?.find(metric => metric.path === 'electrical_metrics.capacity_loading_pct');
  const analyticsBound = sample || (analytics?.status === 'completed' && result && analytics.reading_id === reading?.readingId && analytics.asset_id === reading?.assetId && analytics.source === reading?.source && (analytics.run_id ?? null) === (reading?.runId ?? null) && analytics.configuration_version === reading?.configurationVersion && Date.parse(analytics.measurement_time) === Date.parse(reading?.measurementTime));
  const base = { identity, ruleVerified: configBound, quality: 'good', relation: 'maximum' };
  const provenance = name => sample ? 'assumed' : config?.parameter_provenance?.[`operational_limits.${name}`];
  const allCurrentGood = ['current_r_a', 'current_y_a', 'current_b_a', 'voltage_r_v', 'voltage_y_v', 'voltage_b_v'].every(name => reading?.measurementQuality?.[name] === 'good' && usableMeasurement(reading, name) != null);
  const factors = [
    { ...base, id: 'loading', label: 'Capacity loading', valueSource: sample ? 'SAMPLE / SIMULATED' : 'Completed stored analytics', value: analyticsBound && loading?.unit === '%' ? loading.value : null, unit: loading?.unit, limit: config?.operational_limits?.max_load_pct, limitProvenance: provenance('max_load_pct'), quality: allCurrentGood ? 'good' : 'unusable', reason: !analyticsBound ? 'No compatible completed capacity-loading result for this reading.' : undefined },
    { ...base, id: 'thermal', label: 'Measured oil temperature', valueSource: sample ? 'SAMPLE / SIMULATED' : 'Normalized measured channel', value: usableMeasurement(reading, 'oil_temperature_c'), unit: '°C', quality: reading?.measurementQuality?.oil_temperature_c, limit: config?.operational_limits?.max_top_oil_temp_c, limitProvenance: provenance('max_top_oil_temp_c') },
    { id: 'electrical', label: 'Electrical imbalance', unit: '%', reason: 'No approved imbalance threshold is supplied by this configuration contract.' },
    { id: 'oil', label: 'Oil level', unit: '%', reason: 'No configured minimum oil-level rule is supplied by this configuration contract.' },
  ];
  if (mode === 'live' && (reading?.assetId?.startsWith('SAMPLE-') || analytics?.status === 'sample')) factors.forEach(factor => { factor.reason = 'Sample evidence is excluded from backend rating.'; });
  return computeConditionRating({ factors, identity, mode, now });
}

export function ratingFactorForMetric(result, metricId) {
  const group = { capacity_loading: 'loading', oil_temperature_c: 'thermal', oil_level_pct: 'oil', current_imbalance: 'electrical', voltage_imbalance: 'electrical' }[metricId];
  return result?.factors.find(factor => factor.id === group) ?? null;
}
