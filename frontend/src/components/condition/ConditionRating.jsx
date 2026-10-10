import { ArrowUpRight, AlertTriangle } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { CONDITION_POLICY } from '../../domain/conditionRating.js';
import { motionTiming } from '../../domain/motion.js';
import { displayId, displayRatingState, displaySource } from '../../lib/presentation.js';
import { number } from '../../lib/utils.js';

export default function ConditionRating({ result, onOpen }) {
  const reduced = useReducedMotion();
  const assessed = result.score != null;
  return <motion.button className={`condition-rating ${result.breaches.length ? 'rating-breach' : ''}`} onClick={onOpen} aria-label="Explain Transformer Condition Rating">
    <span className="rating-instrument"><svg viewBox="0 0 100 100" aria-hidden="true"><circle className="rating-track" cx="50" cy="50" r="41" /><motion.circle className="rating-arc" cx="50" cy="50" r="41" pathLength="100" initial={false} animate={{ strokeDasharray: `${assessed ? result.score * 0.78 : 0} 100` }} transition={reduced || !assessed ? { duration: 0 } : motionTiming.spatial} /></svg><strong>{assessed ? number(result.score, 0) : '—'}<small>{assessed ? '/100' : 'NOT ASSESSED'}</small></strong></span>
    <span className="rating-copy"><span className="eyebrow">TRANSFORMER CONDITION RATING</span><strong>{displayRatingState(result)}</strong></span>
    <span className="rating-action">{result.breaches.length ? <AlertTriangle size={18} /> : <ArrowUpRight size={18} />}<small>{result.breaches.length ? `${result.breaches.length} limit breach${result.breaches.length === 1 ? '' : 'es'}` : 'Show factors'}</small></span>
  </motion.button>;
}
export function RatingExplanation({ result }) {
  return <div className="rating-explanation">
    <dl className="metadata-list"><div><dt>Policy</dt><dd>{result.policyVersion.replace('-prototype-', '-')}</dd></div><div><dt>Evidence time</dt><dd>{result.evidenceTime ?? 'No reading retrieved'} UTC</dd></div><div><dt>Frontend calculation (UTC)</dt><dd>{result.evaluatedAt ?? 'Not calculated'}</dd></div><div><dt>Coverage</dt><dd>{result.coverage}% · {result.eligibleCount}/4 eligible groups</dd></div><div><dt>Identity</dt><dd>{displayId(result.identity?.assetId)} · reading {displayId(result.identity?.readingId, '—')} · config {result.identity?.configurationVersion ?? '—'}</dd></div>{result.mode !== 'sample' && <div><dt>Stream</dt><dd>{displaySource(result.identity?.source)} / {result.identity?.runId ?? 'none'}</dd></div>}</dl>
    {result.stale && <p className="inline-notice warning">Stale evidence: this calculation describes the recorded time, not the present condition.</p>}
    {result.breaches.length > 0 && <p className="error">Configured limit breach: {result.breaches.map(factor => factor.label).join(', ')}. An aggregate score never cancels this evidence.</p>}
    <div className="rating-factors">{result.factors.map(factor => <article className={`factor-row factor-${factor.classification ?? 'missing'}`} key={factor.id}><div><strong>{factor.label}</strong><span>{factor.weight}% base weight</span></div><dl><div><dt>Measurement</dt><dd>{number(factor.value, 2)} {factor.unit}</dd></div><div><dt>Configured limit</dt><dd>{number(factor.limit, 2)} {factor.unit}</dd></div><div><dt>Configured rule source</dt><dd>{factor.limitProvenance ?? 'No rule provenance'}</dd></div><div><dt>Sub-score</dt><dd>{factor.subScore ?? 'Excluded'}</dd></div></dl><p>Quality: {factor.quality ?? "unavailable"}</p><p>{factor.reason ?? (factor.breached ? 'Actual configured maximum breached.' : factor.classification === 'warning' ? 'Approaching the configured limit.' : 'Below the configured limit.')}</p></article>)}</div>
    <details><summary>Calculation method</summary><p>Base weights: loading 35, measured thermal 35, approved imbalance 15, oil minimum 15. Eligible weighted mean only. At least {CONDITION_POLICY.minimumFactors} groups and {CONDITION_POLICY.minimumCoverage}% base-weight coverage are required. Maximum rules warn at 90% of the configured limit, including equality; a breach requires a value strictly above it. Normal=100, warning=70, breached=25. Missing, suspect, bad, unbound or unit-incompatible evidence is excluded, not counted as physical damage.</p></details>
  </div>;
}
