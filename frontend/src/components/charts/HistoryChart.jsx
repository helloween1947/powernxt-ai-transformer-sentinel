import { useRef, useState } from 'react';
import { motion } from 'motion/react';
import { motionTiming } from '../../domain/motion.js';
import { nearestChartReading } from '../../domain/chartTimeline.js';
import { displayId, displayStatus } from '../../lib/presentation.js';
import { number, time } from '../../lib/utils.js';

export default function HistoryChart({ title, points = [], series, unit = '°C', compact = false, step, decimals = 1, onSelect, selectedId }) {
  const gesture = useRef({ pointerId: null, readingId: null });
  const [scrubbing, setScrubbing] = useState(false);
  const validPoints = [...points].filter(point => Number.isFinite(Date.parse(point.timestamp))).sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  const values = validPoints.flatMap(point => series.map(line => point[line.key])).filter(Number.isFinite);
  const hasData = values.length > 0;
  const low = hasData ? Math.min(...values) : 0;
  const high = hasData ? Math.max(...values) : 1;
  const padding = step ?? Math.max((high - low) * 0.25, 1);
  const min = Math.floor((low - padding) * 10) / 10;
  const max = Math.ceil((high + padding) * 10) / 10;
  const start = Date.parse(validPoints[0]?.timestamp);
  const span = Date.parse(validPoints.at(-1)?.timestamp) - start;
  const x = index => 47 + (span > 0 ? (Date.parse(validPoints[index].timestamp) - start) / span : 0.5) * 685;
  const y = value => 158 - (value - min) * 127 / (max - min);
  const selected = validPoints.find(point => point.readingId === selectedId);
  const selectable = validPoints.filter(point => point.readingId != null);
  const cursorIndex = Math.max(0, selectable.findIndex(point => point.readingId === (selected?.readingId ?? selectable.at(-1)?.readingId)));
  const selectedIndex = validPoints.findIndex(point => point.readingId === selectedId);
  function selectPointer(event, starting = false) {
    const svg = event.currentTarget;
    const matrix = svg.getScreenCTM();
    if (!matrix) return false;
    const position = svg.createSVGPoint();
    position.x = event.clientX; position.y = event.clientY;
    const local = position.matrixTransform(matrix.inverse());
    if (starting && (local.x < 37 || local.x > 742 || local.y < 25 || local.y > 190)) return false;
    const reading = nearestChartReading(validPoints, (local.x - 47) / 685);
    if (!reading) return false;
    if (starting || gesture.current.readingId !== reading.readingId) {
      gesture.current.readingId = reading.readingId;
      onSelect(reading.readingId);
    }
    return true;
  }
  function finishGesture(event) {
    if (gesture.current.pointerId !== event.pointerId) return;
    if (event.type === 'pointerup') selectPointer(event);
    gesture.current.pointerId = null;
    setScrubbing(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }
  function selectKey(event) {
    const delta = { ArrowLeft: -1, ArrowDown: -1, ArrowRight: 1, ArrowUp: 1, PageDown: -5, PageUp: 5 }[event.key];
    if (delta == null && !['Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const index = event.key === 'Home' ? 0 : event.key === 'End' ? selectable.length - 1 : Math.max(0, Math.min(selectable.length - 1, cursorIndex + delta));
    if (selectable[index]) onSelect(selectable[index].readingId);
  }
  return <div className={`history-chart ${compact ? 'compact-chart' : ''}`}>
    <div className="chart-header"><h3>{title}</h3><span>{unit}</span></div>
    {onSelect && hasData && <p className="chart-instruction">Click or drag to inspect a time</p>}
    {hasData ? <svg viewBox="0 0 750 200" className={onSelect ? 'chart-interactive' : undefined} role={onSelect ? 'group' : 'img'} aria-label={`${title}, ${unit}. Exact values are available in the table below.`}
      onPointerDown={onSelect ? event => { if (!event.isPrimary || event.button !== 0) return; if (selectPointer(event, true)) { event.preventDefault(); gesture.current.pointerId = event.pointerId; setScrubbing(true); event.currentTarget.setPointerCapture(event.pointerId); } } : undefined}
      onPointerMove={onSelect ? event => { if (gesture.current.pointerId === event.pointerId) selectPointer(event); } : undefined}
      onPointerUp={onSelect ? finishGesture : undefined} onPointerCancel={onSelect ? finishGesture : undefined} onLostPointerCapture={() => { gesture.current.pointerId = null; setScrubbing(false); }}>
      {onSelect && selectable.length > 0 && <rect className="chart-timeline-control" x="47" y="25" width="685" height="140" fill="transparent" role="slider" tabIndex={0} aria-label="Inspect chart time" aria-orientation="horizontal" aria-valuemin={0} aria-valuemax={selectable.length - 1} aria-valuenow={cursorIndex} aria-valuetext={`${selectable[cursorIndex].timestamp} · reading ${displayId(selectable[cursorIndex].readingId)}`} onKeyDown={selectKey} />}
      {[0, 1, 2, 3].map(index => { const value = min + index * (max - min) / 3; return <g key={index}><line x1="47" x2="732" y1={y(value)} y2={y(value)} className="chart-grid" /><text x="0" y={y(value) + 4}>{number(value, decimals)}</text></g>; })}
      {series.map(line => {
        let connected = false;
        const d = validPoints.map((point, index) => {
          if (!Number.isFinite(point[line.key])) { connected = false; return ''; }
          const result = `${connected ? 'L' : 'M'}${x(index)},${y(point[line.key])}`;
          connected = true; return result;
        }).join(' ');
        return <g key={line.key} data-series={line.key}><path d={d} fill="none" stroke={line.color} strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" strokeDasharray={line.dashed ? '5 4' : undefined} />{validPoints.filter(point => Number.isFinite(point[line.key])).length < 3 && validPoints.map((point, index) => Number.isFinite(point[line.key]) && <circle key={index} cx={x(index)} cy={y(point[line.key])} r="3" fill={line.color} />)}</g>;
      })}
      {validPoints.map((point, index) => point.reasons?.length && Number.isFinite(point[series[0].key]) ? <circle key={`quality-${index}`} cx={x(index)} cy={y(point[series[0].key])} r="3.5" fill="var(--surface)" stroke="var(--warning)" strokeWidth="1.5"><title>{point.reasons.join(', ')}</title></circle> : null)}
      {onSelect && validPoints.map((point, index) => <g key={`record-${point.readingId}`} role="button" tabIndex={0} aria-label={`Select chart reading ${displayId(point.readingId)} at ${point.timestamp}`} onKeyDown={event => { if (['Enter',' '].includes(event.key)) { event.preventDefault(); onSelect(point.readingId); } }}>
        <circle className="chart-record-hit" cx={x(index)} cy={Number.isFinite(point[series[0].key]) ? y(point[series[0].key]) : 165} r="10"><title>Inspect reading {displayId(point.readingId)} · {point.timestamp}</title></circle>
      </g>)}
      {onSelect && selectedIndex >= 0 && <motion.g className="chart-cursor" initial={false} animate={{ x: x(selectedIndex) }} transition={scrubbing ? { duration: 0 } : motionTiming.cursor} pointerEvents="none">
        <line x1="0" x2="0" y1="25" y2="165" stroke="var(--accent)" strokeDasharray="3 3" />
        {Number.isFinite(selected[series[0].key]) && <motion.circle className="chart-selection" cx="0" initial={false} animate={{ cy: y(selected[series[0].key]) }} transition={scrubbing ? { duration: 0 } : motionTiming.cursor} r="4" />}
      </motion.g>}
      {validPoints.length > 1 && [0, Math.floor((validPoints.length - 1) / 2), validPoints.length - 1].map((index, position) => <text key={position} x={x(index)} y="186" textAnchor={position === 0 ? 'start' : position === 2 ? 'end' : 'middle'}>{time(validPoints[index].timestamp)}</text>)}
    </svg> : <div className="chart-empty">No usable values in this retrieved history page.</div>}
    {selected && <p className="chart-selected-record" role="status">Inspected reading {displayId(selected.readingId)} · {selected.timestamp} UTC{selected.status !== 'sample' && ` · ${selected.status ?? 'not retrieved'}`}</p>}
    <div className="chart-legend">{series.map(line => <span key={line.key}><i style={{ borderColor: line.color, borderStyle: line.dashed ? 'dashed' : 'solid' }} />{line.label}</span>)}<small>Measurement time · IST</small></div>
    <details className="chart-values"><summary>View exact values ({validPoints.length})</summary><div className="table-wrap"><table><caption>{title} · {unit} · UTC timestamps</caption><thead><tr><th>Measurement time</th><th>Reading</th>{series.map(line => <th key={line.key}>{line.label} ({unit})</th>)}<th>Processing / quality</th></tr></thead><tbody>{validPoints.map((point, index) => <tr key={point.readingId ?? index}><td>{point.timestamp}</td><td>{onSelect ? <button className="text-link" aria-label={`Inspect table reading ${displayId(point.readingId)}`} onClick={() => onSelect(point.readingId)}>{displayId(point.readingId)}</button> : displayId(point.readingId, '—')}</td>{series.map(line => <td key={line.key}>{number(point[line.key], 2)}</td>)}<td>{displayStatus(point.status)} {point.reasons?.join(', ')}</td></tr>)}</tbody></table></div></details>
  </div>;
}
