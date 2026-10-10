import { ratingFactorForMetric } from '../../domain/conditionRating.js';
import { motion } from 'motion/react';
import { motionTiming } from '../../domain/motion.js';
import { Activity, ArrowUpRight, ChevronRight, Droplets, Thermometer, Zap } from 'lucide-react';
import { anchors } from '../../data/capabilities.js';
import { displayId, displaySource, displayMetricReason } from '../../lib/presentation.js';
import { number, time } from '../../lib/utils.js';
import { Button } from '../ui/button.jsx';

export function Availability({ state }) {
  if (['Sample', 'Prototype'].includes(state)) return null;
  return <span className={`availability state-${state.toLowerCase()}`}><span />{state}</span>;
}
export function MetricRow({ metric, onSelect, selected }) {
  const typeLabel = metric.type === 'prototype' || metric.state === 'Sample' ? '' : metric.type === 'future' ? metric.state : metric.type === 'configuration' ? 'Configuration' : metric.type[0].toUpperCase() + metric.type.slice(1);
  return <button className={`metric-row ${selected ? 'active' : ''}`} onClick={() => onSelect(metric.id)} aria-pressed={selected}>
    <span><span>{metric.label}</span>{typeLabel && <small>{typeLabel}</small>}</span>
    <strong>{number(metric.value, metric.digits)}{metric.value != null && <small>{metric.unit}</small>}</strong><ChevronRight size={13} />
  </button>;
}
export function MetricDetails({ metric, snapshot, mode, rating, onTrend }) {
  if (!metric) return null;
  const config = snapshot?.details?.current_configuration;
  const contribution = ratingFactorForMetric(rating, metric.id);
  return <div className="metric-details">
    <div className="detail-value"><strong>{number(metric.value, metric.digits)}</strong><span>{metric.unit}</span><Availability state={metric.state} /></div>
    {displayMetricReason(metric) && <p>{displayMetricReason(metric)}</p>}
    {metric.anchor && <div className="detail-location"><Activity size={14} /><span>{anchors[metric.anchor].label}<small>Semantic association · placement unverified</small></span></div>}
    <dl className="metadata-list"><div><dt>Value type</dt><dd>{metric.type === 'prototype' ? 'Condition rating' : metric.type}</dd></div>
      <div><dt>Measurement time</dt><dd>{time(metric.timestamp, true)}</dd></div>
      <div><dt>Reading</dt><dd>{displayId(metric.readingId)}</dd></div>
      <div><dt>Configuration</dt><dd>{metric.configurationVersion != null ? `Version ${metric.configurationVersion}` : 'Unavailable'}</dd></div>
      {mode !== 'sample' && <div><dt>Source / run</dt><dd>{displaySource(snapshot?.latest?.source)} / {snapshot?.latest?.runId ?? 'none'}</dd></div>}
      {metric.quality && <div><dt>Channel quality</dt><dd>{metric.quality}</dd></div>}
      {metric.modelVersion && <div><dt>Model</dt><dd>{metric.modelVersion}</dd></div>}
      {snapshot?.analytics?.result && <><div><dt>Parameter version</dt><dd>{snapshot.analytics.result.parameter_version ?? 'Unavailable'}</dd></div><div><dt>Result stored (UTC)</dt><dd>{snapshot.analytics.result.created_at ?? 'Unavailable'}</dd></div></>}
    </dl>
    {rating && <p className="rating-contribution">Condition Rating: {contribution?.eligible ? `${contribution.weight}% base weight · sub-score ${contribution.subScore}/100 · ${contribution.classification}. ${rating.score == null ? 'Coverage gate prevents an aggregate score.' : `${number(contribution.weight / rating.coverage * 100, 1)}% of eligible weight.`}` : contribution?.reason ?? 'This metric is not a scoring factor.'}</p>}
    {onTrend && <Button variant="outline" onClick={onTrend}>Open related history<ArrowUpRight size={14} /></Button>}
    {metric.id === 'oil_temperature_c' && config?.version === metric.configurationVersion && Number.isFinite(config?.operational_limits?.max_top_oil_temp_c) && <div className="limit-note"><span>Configured top-oil maximum</span><strong>{config.operational_limits.max_top_oil_temp_c} °C</strong><small>Configuration v{config.version} · {config.parameter_provenance?.['operational_limits.max_top_oil_temp_c'] ?? 'provenance unavailable'}</small></div>}
    {metric.id === 'capacity_loading' && config?.version === metric.configurationVersion && Number.isFinite(config?.operational_limits?.max_load_pct) && <div className="limit-note"><span>Configured loading limit</span><strong>{config.operational_limits.max_load_pct}%</strong><small>Asset-specific setting; permissible duration is not assessed.</small></div>}
  </div>;
}

export default function MetricPanel({ metrics, selected, onSelect, snapshot, onExpand, onTrend, onClear }) {
  const group = selected?.category ?? 'Thermal';
  const Icon = { Electrical: Zap, Thermal: Thermometer, Condition: Droplets }[group] ?? Activity;
  const nearby = metrics.filter(metric => metric.category === group && metric.type !== 'future').slice(0, 4);
  return <motion.section className="component-panel" layout="position" transition={motionTiming.micro}>
    <div className="panel-head"><h2>Component details</h2><Button variant="ghost" size="icon" aria-label="Expand measurement details" onClick={onExpand}><ArrowUpRight size={17} /></Button></div>
    <motion.div key={selected?.id} className="selected-component" initial={{ opacity: 0, y: 3 }} animate={{ opacity: 1, y: 0 }} transition={motionTiming.micro}><span className="component-icon"><Icon size={21} /></span><div><h3>{selected?.anchor ? anchors[selected.anchor].label : 'Asset measurements'}</h3><p>{selected?.label ?? 'Select a component'}</p></div></motion.div>
    <div className="panel-metric"><span>{selected?.label}</span><div><strong>{number(selected?.value, selected?.digits)}</strong><small>{selected?.unit}</small><Availability state={selected?.state ?? 'Unavailable'} /></div></div>
    {displayMetricReason(selected) && <p className="panel-explanation">{displayMetricReason(selected)}</p>}
    <div className="panel-section-label">{group.toUpperCase()} MEASUREMENTS</div>
    <div className="nearby-metrics">{nearby.map(metric => <MetricRow key={metric.id} metric={metric} selected={selected?.id === metric.id} onSelect={onSelect} />)}</div>
    <div className="inspector-evidence"><span>Reading {displayId(snapshot?.latest?.readingId, 'unavailable')} · {time(selected?.timestamp)} IST</span><span>Quality: {selected?.quality ?? 'not a sensor channel'} · config {selected?.configurationVersion ?? '—'}</span><Button variant="outline" size="sm" onClick={onTrend}>Related evidence<ArrowUpRight size={14} /></Button><button className="text-link" onClick={onClear}>Return to oil tank</button></div>
  </motion.section>;
}

export function Parameters({ metrics, category, selected, onSelect, future = true }) {
  const groups = category ? [category] : ['Electrical', 'Thermal', 'Condition'];
  return <div className="parameter-groups">{groups.map(group => <section className="card parameter-group" key={group}>
    <div className="panel-head"><h2>{group} parameters</h2><span className="tiny-tag">{metrics.filter(metric => metric.category === group && metric.type !== 'future').length} supported</span></div>
    {metrics.filter(metric => metric.category === group && metric.type !== 'future').map(metric => <MetricRow key={metric.id} metric={metric} selected={selected?.id === metric.id} onSelect={onSelect} />)}
    {future && <details><summary>Future capabilities</summary>{metrics.filter(metric => metric.category === group && metric.type === 'future').map(metric => <div className="future-metric" key={metric.id}><button onClick={() => onSelect(metric.id)}>{metric.label}<ChevronRight size={13} /></button><Availability state={metric.state} />{displayMetricReason(metric) && <p>{displayMetricReason(metric)}</p>}</div>)}</details>}
  </section>)}</div>;
}
