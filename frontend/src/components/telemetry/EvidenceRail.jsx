import { useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight, Clock3 } from 'lucide-react';
import { Button } from '../ui/button.jsx';
import { displayId } from '../../lib/presentation.js';
import { time } from '../../lib/utils.js';
export default function EvidenceRail({ snapshot, selectedId, onSelect, onLatest }) {
  const records = snapshot?.history ?? [];
  const index = records.findIndex(reading => reading.readingId === selectedId);
  const railRef = useRef(null);
  useEffect(() => {
    const rail = railRef.current;
    const selected = rail?.querySelector('button[aria-pressed="true"]');
    if (!selected) return;
    const railBounds = rail.getBoundingClientRect();
    const selectedBounds = selected.getBoundingClientRect();
    const left = Math.max(0, Math.min(rail.scrollWidth - rail.clientWidth,
      rail.scrollLeft + selectedBounds.left - railBounds.left - (rail.clientWidth - selectedBounds.width) / 2));
    // Scroll only the time strip, preserving the chart's vertical position
    // and pointer capture while the operator scrubs through readings.
    if (Math.abs(rail.scrollLeft - left) > 1) rail.scrollTo({ left, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  }, [selectedId, snapshot?.history]);
  return <section className="evidence-rail" aria-label="Timestamped reading evidence"><div className="evidence-rail-title"><Clock3 size={16} /><div><strong>{selectedId == null ? 'Latest telemetry' : 'Historical inspection'}</strong><small>{records.length} records</small></div>{selectedId != null && <Button variant="outline" size="sm" onClick={onLatest}>Return to latest</Button>}</div><div className="evidence-records" ref={railRef}>{records.length ? records.map(reading => <button key={reading.readingId} aria-pressed={reading.readingId === selectedId} onClick={() => onSelect(reading.readingId)} aria-label={`Inspect reading ${displayId(reading.readingId)} at ${reading.measurementTime}`}><span className={`record-status record-${reading.processingJobStatus}`} /><strong>{time(reading.measurementTime)}</strong>{reading.processingJobStatus !== 'sample' && <small>{reading.processingJobStatus ?? 'not retrieved'}</small>}</button>) : <p>No timestamped records in this retrieved page.</p>}</div><div className="evidence-step"><Button variant="ghost" size="icon" aria-label="Inspect previous reading" disabled={!records.length || index === 0} onClick={() => onSelect(records[Math.max(0, index < 0 ? records.length - 1 : index - 1)].readingId)}><ChevronLeft size={16} /></Button><Button variant="ghost" size="icon" aria-label="Inspect next reading" disabled={index < 0 || index === records.length - 1} onClick={() => onSelect(records[index + 1].readingId)}><ChevronRight size={16} /></Button></div></section>;
}
