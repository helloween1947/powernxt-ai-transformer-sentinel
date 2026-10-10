import { Component, lazy, Suspense, useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import { motionTiming } from '../../domain/motion.js';
import { Box, Hand, Layers3, RotateCcw, Tags } from 'lucide-react';
import { Button } from '../ui/button.jsx';
import { number } from '../../lib/utils.js';
import { calloutMetrics } from '../../data/capabilities.js';

const Scene = lazy(() => import('./TransformerScene.jsx'));
class SceneBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { this.props.onUnavailable(); }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}
function supportsWebGL() {
  try {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('webgl2') || canvas.getContext('webgl');
    context?.getExtension('WEBGL_lose_context')?.loseContext();
    return !!context;
  } catch { return false; }
}

export default function DigitalTwin({ metrics, selected, onSelect, onInspect, dark }) {
  const reduced = useReducedMotion();
  const [labelsVisible, setLabelsVisible] = useState(true);
  const [category, setCategory] = useState('All');
  const [interactive, setInteractive] = useState(false);
  const [reset, setReset] = useState(0);
  const [modelUnavailable, setModelUnavailable] = useState(() => !supportsWebGL());
  const [projection, setProjection] = useState({});
  const [calloutPositions, setCalloutPositions] = useState({});
  const sceneRef = useRef(null);
  const calloutRefs = useRef([]);
  const [mobile, setMobile] = useState(() => window.innerWidth < 620);
  useEffect(() => {
    const query = window.matchMedia('(max-width: 620px)');
    const update = () => setMobile(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  const callouts = labelsVisible ? calloutMetrics(metrics, category, mobile) : [];
  const calloutKey = callouts.map(metric => metric.id).join('|');
  useEffect(() => {
    const nodes = calloutRefs.current.filter(Boolean);
    const scene = sceneRef.current;
    if (!scene || !nodes.length) return;
    const observer = new ResizeObserver(() => {
      const positions = Object.fromEntries(nodes.map(node => [node.dataset.calloutSlot, {
        x: node.offsetLeft + (Number(node.dataset.calloutSlot) % 2 === 0 ? node.offsetWidth : 0),
        y: node.offsetTop + node.offsetHeight / 2,
      }]));
      setCalloutPositions(previous => JSON.stringify(previous) === JSON.stringify(positions) ? previous : positions);
    });
    observer.observe(scene);
    nodes.forEach(node => observer.observe(node));
    return () => observer.disconnect();
  }, [calloutKey]);
  function projected(points) { if (points == null) setModelUnavailable(true); else setProjection(points); }
  const fallback = <div className="scene-unavailable" role="status"><strong>3D view unavailable</strong><span>Measurements remain available.</span></div>;
  return <section className="twin-card" aria-label="Interactive transformer digital twin">
    <div className="twin-top"><div className="twin-label"><Box size={15} /><span>DIGITAL REPLICA</span></div><span className="tiny-tag"><span className="status-dot neutral" />Telemetry</span></div>
    <div className="scene-filter" aria-label="Measurement callout category">{['All', 'Electrical', 'Thermal', 'Condition'].map(item => <button key={item} aria-pressed={category === item} onClick={() => setCategory(item)}>{category === item && <motion.span className="selection-surface" layoutId="callout-category" transition={motionTiming.micro} aria-hidden="true" />}<span className="control-label">{item === 'All' ? <Layers3 size={13} /> : null}{item}</span></button>)}</div>
    <div ref={sceneRef} className={`scene-viewport ${interactive ? 'interactive' : ''}`}>
      {modelUnavailable ? fallback : <SceneBoundary fallback={fallback} onUnavailable={() => setModelUnavailable(true)}><Suspense fallback={<div className="scene-loading" role="status">Building digital replica…</div>}><Scene selected={selected?.anchor} onSelect={onSelect} onProject={projected} dark={dark} interactive={interactive} reduced={reduced} reset={reset} /></Suspense></SceneBoundary>}
      {!modelUnavailable && <svg className="leader-lines" width="100%" height="100%" aria-hidden="true">{callouts.map((metric, index) => {
        const anchor = projection[metric.anchor];
        const callout = calloutPositions[index];
        if (!anchor || !callout) return null;
        return <g key={metric.id}><line x1={callout.x} y1={callout.y} x2={anchor.x} y2={anchor.y} /><circle cx={anchor.x} cy={anchor.y} r="3" /></g>;
      })}</svg>}
      <div className="callout-overlay">{callouts.map((metric, index) => <button key={`${index}:${metric.id}`} ref={node => { calloutRefs.current[index] = node; }} data-callout-slot={index} className={`measurement-bubble bubble-${index} ${selected?.id === metric.id ? 'selected' : ''}`} aria-pressed={selected?.id === metric.id} aria-label={`${metric.label}: ${number(metric.value, metric.digits)} ${metric.unit}. ${metric.state === 'Sample' ? '' : metric.state}`} onClick={() => { onSelect(metric.id); onInspect(metric.id); }}>
        <span className="bubble-glass">
        <span>{metric.label}<span className="bubble-dot" /></span><strong>{number(metric.value, metric.digits)}<small>{metric.unit}</small></strong>{metric.state !== 'Sample' && <em>{metric.state === 'Unavailable' ? 'Unavailable' : metric.type === 'estimated' ? 'Estimated' : metric.type === 'derived' ? 'Derived' : 'Measured'}</em>}</span>
      </button>)}</div>
      {!modelUnavailable && projection.axes && <svg className="scene-axis" viewBox="0 0 48 48" aria-hidden="true">
        {projection.axes.map(axis => <g key={axis.label} data-axis={axis.label}>
          <line x1="24" y1="24" x2={24 + axis.x * 15} y2={24 + axis.y * 15} />
          <text x={24 + axis.x * 21} y={24 + axis.y * 21}>{axis.label}</text>
        </g>)}
        <circle cx="24" cy="24" r="1.5" />
      </svg>}
      <div className="model-caption">DISTRIBUTION TRANSFORMER</div>
      <div className="scene-tools"><Button variant="outline" size="icon" aria-label={labelsVisible ? 'Hide measurement labels' : 'Show measurement labels'} aria-pressed={labelsVisible} onClick={() => setLabelsVisible(value => !value)}><Tags size={15} /></Button>
        <Button variant="outline" size="icon" aria-label="Reset camera" disabled={modelUnavailable} onClick={() => { setReset(value => value + 1); setInteractive(false); }}><RotateCcw size={15} /></Button>
        <Button variant={interactive ? 'default' : 'outline'} size="icon" disabled={modelUnavailable} aria-pressed={interactive} aria-label="Enable rotation and zoom" onClick={() => setInteractive(value => !value)}><Hand size={15} /></Button>
      </div>
    </div>
    <div className="twin-bottom"><span>{interactive && !modelUnavailable ? 'Drag to rotate · Scroll or pinch to zoom' : 'Select a measurement to inspect its details'}</span><span>3D DIGITAL TWIN</span></div>
  </section>;
}
