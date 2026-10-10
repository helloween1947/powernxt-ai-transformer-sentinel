import { useEffect, useState } from 'react';
import { AnimatePresence, LayoutGroup, motion, MotionConfig } from 'motion/react';
import { Activity, ArrowDownToLine, ArrowUpRight, ChevronRight, CircleHelp, Database, MapPin, RefreshCw, ShieldCheck, Thermometer, Zap } from 'lucide-react';
import { Sidebar, Topbar } from './components/layout/AppShell.jsx';
import DigitalTwin from './components/digital-twin/DigitalTwin.jsx';
import MetricPanel, { MetricDetails, Parameters } from './components/metrics/MetricPanel.jsx';
import HistoryChart from './components/charts/HistoryChart.jsx';
import { EmptyState, IncidentsView, MaintenanceView, QualityView, ReportsView, WhatIfView } from './components/workflows/OperatorViews.jsx';
import { Button } from './components/ui/button.jsx';
import { DetailDialog } from './components/ui/dialog.jsx';
import ConditionRating, { RatingExplanation } from './components/condition/ConditionRating.jsx';
import CapabilityExplorer from './components/condition/CapabilityExplorer.jsx';
import EvidenceRail from './components/telemetry/EvidenceRail.jsx';
import { conditionRating } from './domain/conditionRating.js';
import { inspectHistoryRecord, metricTrend } from './domain/inspection.js';
import { chartPointsForContext } from './domain/chartProvenance.js';
import { motionTiming } from './domain/motion.js';
import BackendIncidents from './components/BackendIncidents.jsx';
import BackendWhatIf from './components/BackendWhatIf.jsx';
import BackendMaintenance from './components/BackendMaintenance.jsx';
import OperatorAuthBar from './components/OperatorAuthBar.jsx';
import { useOperatorSession } from './hooks/useOperatorSession.js';
import { useRuntimeContract } from './hooks/useRuntimeContract.js';
import { useAssets, useWorkstation } from './hooks/useWorkstation.js';
import { navigation } from './data/navigation.js';
import { resolveMetrics } from './data/capabilities.js';
import { downloadReport } from './services/reportExport.js';
import { usableMeasurement } from './services/telemetryAdapter.js';
import { displayId, displayLocation, displayStatus } from './lib/presentation.js';
import { number, readPreference, savePreference, time } from './lib/utils.js';

const temperatureSeries = [{ key: 'measured', label: 'Measured oil', color: 'var(--chart-measured)' }, { key: 'predicted', label: 'Estimated top-oil', color: 'var(--chart-estimated)', dashed: true }];
const focusedAssetId = import.meta.env.VITE_FOCUSED_ASSET_ID || '';
const focused = Boolean(focusedAssetId);
const tabs = ['Overview', 'Electrical', 'Thermal', 'Condition', 'Data quality'];
const titles = { capabilities: 'Condition explorer', twin: 'Digital twin', trends: 'Trends & history', incidents: 'Alerts & incidents', maintenance: 'Maintenance', whatif: 'What-if analysis', reports: 'Reports' };
const descriptions = { capabilities: 'Inspect measurements, instruments and future model requirements.', trends: 'Inspect measurements and stored estimates over time.', incidents: 'Trace configured-limit evidence to its source reading.', maintenance: 'Review assignments, task progress and recorded work.', whatif: 'Compare conditional healthy-model forecasts from immutable backend state.', reports: 'Export retrieved records and inspect validation references.' };

function initialScreen() { return navigation.some(item => item.id === location.hash.slice(1)) ? location.hash.slice(1) : 'twin'; }
function initialTheme() { return readPreference('powernxt-theme', window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }

export default function App() {
  const [screen, setScreen] = useState(initialScreen);
  const [openedTaskId, setOpenedTaskId] = useState(null);
  const [theme, setTheme] = useState(initialTheme);
  const [mode, setMode] = useState(() => focused || import.meta.env.VITE_DATA_MODE === 'live' ? 'live' : 'sample');
  const [baseUrl, setBaseUrl] = useState(() => focused ? import.meta.env.VITE_API_BASE_URL : readPreference('powernxt-api-origin', import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'));
  const [baseDraft, setBaseDraft] = useState(baseUrl);
  const [settingsError, setSettingsError] = useState('');
  const [assetId, setAssetId] = useState(() => focusedAssetId || readPreference(`powernxt-context:${baseUrl}:asset`));
  const [assetOffset, setAssetOffset] = useState(0);
  const [source, setSource] = useState(() => readPreference(`powernxt-context:${baseUrl}:source`, import.meta.env.VITE_DEFAULT_SOURCE || 'device'));
  const [runId, setRunId] = useState(() => readPreference(`powernxt-context:${baseUrl}:run`, import.meta.env.VITE_DEFAULT_RUN_ID || ''));
  const [runDraft, setRunDraft] = useState(runId);
  const [range, setRange] = useState(focused ? 'all' : '24h');
  const [offset, setOffset] = useState(0);
  const [condition, setCondition] = useState('steady');
  const [refresh, setRefresh] = useState(0);
  const [tab, setTab] = useState('Overview');
  const [selectedId, setSelectedId] = useState('oil_temperature_c');
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [notice, setNotice] = useState('');
  const [ratingOpen, setRatingOpen] = useState(false);
  const [historicalSelection, setHistoricalSelection] = useState({});
  const [collapsed, setCollapsed] = useState(true);
  const [clock, setClock] = useState(() => Date.now());
  const [trendMetric, setTrendMetric] = useState('temperature');
  const assets = useAssets(mode, baseUrl, assetOffset, refresh);
  const activeAssetId = assetId || assets.items[0]?.asset_id || '';
  useEffect(() => {
    if (mode !== 'live') return;
    savePreference(`powernxt-context:${baseUrl}:asset`, activeAssetId);
    savePreference(`powernxt-context:${baseUrl}:source`, source);
    savePreference(`powernxt-context:${baseUrl}:run`, runId);
  }, [mode, baseUrl, activeAssetId, source, runId]);
  const runtime = useRuntimeContract(mode, baseUrl, refresh);
  const auth = useOperatorSession(baseUrl, mode === 'live');
  const workflowKey = JSON.stringify({ baseUrl, activeAssetId, source, runId, actor: auth.operator?.actorRef });
  const workflowProps = { focusedContext: focused, baseUrl, selectedAssetId: activeAssetId, selectedSource: source, selectedRunId: runId };
  const state = useWorkstation({ mode, baseUrl, assetId: activeAssetId, source, runId, range, offset, condition, refresh, analyticsEnabled: runtime.analytics === true });
  const snapshot = state.snapshot;
  const asset = snapshot?.details ?? assets.items.find(item => item.asset_id === activeAssetId);
  const inspectionKey = JSON.stringify({ mode, baseUrl, activeAssetId, source, runId, range, offset });
  const selectedReadingId = historicalSelection.key === inspectionKey ? historicalSelection.readingId : null;
  const inspection = inspectHistoryRecord(snapshot, selectedReadingId, mode);
  const inspectedSnapshot = inspection.snapshot;
  const rating = conditionRating(inspectedSnapshot, mode, clock);
  const metrics = resolveMetrics(inspectedSnapshot, mode, rating);
  const selected = metrics.find(metric => metric.id === selectedId) ?? metrics[0];
  const metric = id => metrics.find(item => item.id === id);
  const measured = inspectedSnapshot?.latest;
  const age = measured ? Math.max(0, Math.floor((clock - Date.parse(measured.measurementTime)) / 60000)) : null;
  const freshness = inspection.historical ? 'Historical reading' : mode === 'sample' ? 'Recorded history' : !measured ? 'No reading retrieved' : source !== 'device' ? 'Stored history' : age > 2 ? `Stored device reading · ${age >= 1440 ? `${Math.floor(age / 1440)}d` : `${age}m`} old` : 'Recent device measurement';

  useEffect(() => { document.documentElement.dataset.theme = theme; savePreference('powernxt-theme', theme); }, [theme]);
  useEffect(() => {
    const changed = () => setScreen(initialScreen());
    window.addEventListener('popstate', changed);
    const timer = setInterval(() => setClock(Date.now()), 30000);
    return () => { window.removeEventListener('popstate', changed); clearInterval(timer); };
  }, []);
  useEffect(() => { if (!notice) return; const timer = setTimeout(() => setNotice(''), 5000); return () => clearTimeout(timer); }, [notice]);
  function navigate(next) { window.scrollTo({ top: 0, behavior: 'instant' }); setScreen(next); history.pushState(null, '', `#${next}`); setNotice(''); }
  function selectAsset(next) { setAssetId(next); setOffset(0); setSelectedId('oil_temperature_c'); setNotice(''); }
  function selectMetric(id, expand = false) { if (id === 'condition_rating') { setRatingOpen(true); return; } setSelectedId(id); setTrendMetric(metricTrend(id)); if (expand || window.innerWidth < 1000) setDetailsOpen(true); }
  function selectReading(readingId) { setHistoricalSelection({ key: inspectionKey, readingId }); }
  function clearHistory() { setHistoricalSelection({}); }
  function openTrend(next) { setTrendMetric(next); navigate('trends'); }
  function changeMode(next) { setMode(next); setAssetId(''); setOffset(0); setAssetOffset(0); setNotice(''); setDetailsOpen(false); }
  function exportData() { if (downloadReport(snapshot, mode)) setNotice('History exported as CSV.'); }
  function setTimeRange(next) { setRange(next); setOffset(0); }
  function openSettings() { setBaseDraft(baseUrl); setSettingsOpen(true); }
  const allErrors = [assets.message, state.message, ...(snapshot?.errors ?? [])].filter(Boolean);
  const historyPoints = snapshot?.points ?? [];
  const ungroupedPoints = ['temperature', 'residual', 'loading', 'power'].includes(trendMetric) ? historyPoints : (snapshot?.history ?? []).map(reading => ({ timestamp: reading.measurementTime, readingId: reading.readingId, configurationVersion: reading.configurationVersion, ...Object.fromEntries(Object.keys(reading.measurements).map(name => [name, usableMeasurement(reading, name)])), status: reading.processingJobStatus, reasons: Object.values(reading.qualityFlags ?? {}).flat() }));
  const chartConfiguration = inspectedSnapshot?.latest?.configurationVersion ?? null;
  const chartModel = inspectedSnapshot?.analytics?.result?.model_version ?? null;
  const points = mode === 'sample' ? ungroupedPoints : chartPointsForContext(ungroupedPoints, chartConfiguration, chartModel);
  const series = trendMetric === 'temperature' ? temperatureSeries : trendMetric === 'residual' ? [{ key: 'residual', label: 'Measured minus estimated', color: 'var(--chart-measured)' }] : trendMetric === 'loading' ? [{ key: 'capacityLoading', label: 'Capacity loading', color: 'var(--chart-measured)' }, { key: 'phaseLoading', label: 'Worst-phase loading', color: 'var(--chart-estimated)', dashed: true }] : trendMetric === 'power' ? [{ key: 'apparentPower', label: 'Apparent power', color: 'var(--chart-measured)' }] : trendMetric === 'oil_level' ? [{ key: 'oil_level_pct', label: 'Oil level', color: 'var(--chart-measured)' }] : ['r', 'y', 'b'].map((phase, index) => ({ key: `${trendMetric}_${phase}_${trendMetric === 'voltage' ? 'v' : 'a'}`, label: `${phase.toUpperCase()} phase`, color: ['var(--chart-measured)', 'var(--chart-estimated)', 'var(--chart-third)'][index] }));

  const pageContent = screen === 'capabilities' ? <CapabilityExplorer metrics={metrics} selected={selected} onSelect={selectMetric} snapshot={inspectedSnapshot} onTrend={openTrend} /> : screen === 'twin' ? <>
    <div className="view-tabs" role="tablist" aria-label="Transformer views">{tabs.map(item => <button key={item} role="tab" id={`tab-${item.replaceAll(' ', '-')}`} aria-controls="transformer-tabpanel" aria-selected={tab === item} tabIndex={tab === item ? 0 : -1} onKeyDown={event => {
      if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
        event.preventDefault(); const index = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (tabs.indexOf(item) + (event.key === 'ArrowLeft' ? -1 : 1) + tabs.length) % tabs.length;
        setTab(tabs[index]); document.getElementById(`tab-${tabs[index].replaceAll(' ', '-')}`)?.focus();
      }
    }} onClick={() => setTab(item)}>{item}{tab === item && <motion.span className="tab-indicator" layoutId="transformer-tab-indicator" transition={motionTiming.micro} aria-hidden="true" />}</button>)}</div>
    <div role="tabpanel" id="transformer-tabpanel" aria-labelledby={`tab-${tab.replaceAll(' ', '-')}`}>
      <ConditionRating result={rating} onOpen={() => setRatingOpen(true)} />
        {inspection.historical && <div className="historical-banner" role="status">Historical inspection · reading {displayId(inspectedSnapshot.latest.readingId)} · {inspectedSnapshot.latest.measurementTime} UTC<Button variant="outline" size="sm" onClick={clearHistory}>Return to latest</Button></div>}
      <motion.div key={tab} className="tab-content" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={motionTiming.view}>{tab === 'Overview' ? <>
        <div className="twin-layout"><DigitalTwin metrics={metrics} selected={selected} onSelect={selectMetric} onInspect={id => selectMetric(id, true)} mode={mode} dark={theme === 'dark'} /><MetricPanel metrics={metrics} selected={selected} onSelect={selectMetric} snapshot={inspectedSnapshot} mode={mode} onTrend={() => openTrend(metricTrend(selected.id))} onClear={() => selectMetric('oil_temperature_c')} onExpand={() => setDetailsOpen(true)} /></div>
        <EvidenceRail snapshot={snapshot} selectedId={inspection.historical ? selectedReadingId : null} onSelect={selectReading} onLatest={clearHistory} mode={mode} /><div className="summary-strip">{[{ id: 'rated_capacity', icon: Zap, label: 'Rated capacity' }, { id: 'apparent_power', icon: Activity, label: 'Apparent power' }, { id: 'ambient_temperature_c', icon: Thermometer, label: 'Ambient temperature' }, { id: 'health', icon: ShieldCheck, label: 'Health assessment' }].map(({ id, icon: Icon, label }) => <button key={id} onClick={() => selectMetric(id, true)}><span className="summary-icon"><Icon size={18} strokeWidth={1.6} /></span><div><span>{label}</span><strong>{id === 'health' ? 'Not assessed' : number(metric(id)?.value, metric(id)?.digits)}{id !== 'health' && <small>{metric(id)?.unit}</small>}</strong>{id !== 'health' && metric(id)?.state !== 'Sample' && <em>{metric(id)?.type === 'configuration' ? `Configuration v${asset?.current_configuration?.version ?? '—'}` : metric(id)?.state}</em>}</div><ArrowUpRight size={13} /></button>)}</div>
        <div className="overview-lower"><section className="card overview-chart"><div className="panel-head"><div><h2>Selected measurement history</h2></div><div className="range-picker" aria-label="History time range">{['1h', '6h', '24h', 'all'].map(item => <button key={item} aria-pressed={range === item} onClick={() => setTimeRange(item)}>{item === 'all' ? 'All' : item.toUpperCase()}</button>)}</div></div><HistoryChart title={`Related ${selected?.label ?? 'measurement'} evidence`} points={points} series={series} unit={trendMetric === 'voltage' ? 'V' : trendMetric === 'current' ? 'A' : trendMetric === 'power' ? 'kVA' : ['loading', 'oil_level'].includes(trendMetric) ? '%' : '°C'} compact onSelect={selectReading} selectedId={selectedReadingId} /><button className="text-link" onClick={() => navigate('trends')}>Explore trends & history<ArrowUpRight size={13} /></button></section><section className="card assessment-card"><div className="panel-head"><h2>Condition assessment</h2><CircleHelp size={16} /></div><span className="assessment-icon"><ShieldCheck size={25} strokeWidth={1.5} /></span><h3>Evidence before assessment</h3><p>Review measurements against configured limits.</p>{mode !== 'sample' && <div><span>Analytics</span><strong>{displayStatus(inspectedSnapshot?.analytics?.status)}</strong></div>}<button className="text-link" onClick={() => navigate('incidents')}>Inspect limit checks<ArrowUpRight size={13} /></button></section></div>
      </> : tab === 'Data quality' ? <QualityView snapshot={inspectedSnapshot} mode={mode} /> : <Parameters category={tab} metrics={metrics} selected={selected} onSelect={id => selectMetric(id, true)} />}</motion.div>
    </div>
  </> : screen === 'trends' ? <>
    <section className="card"><div className="panel-head"><h2>Measurement history</h2><div className="trend-controls"><label><span className="sr-only">History measurement</span><select aria-label="History measurement" value={trendMetric} onChange={event => setTrendMetric(event.target.value)}><option value="temperature">Oil temperature</option><option value="residual">Thermal residual</option><option value="voltage">Phase voltage</option><option value="current">Phase current</option><option value="loading">Loading</option><option value="power">Apparent power</option><option value="oil_level">Oil level</option></select></label><label><span className="sr-only">History range</span><select aria-label="History range" value={range} onChange={event => setTimeRange(event.target.value)}><option value="1h">Last hour</option><option value="6h">Last 6 hours</option><option value="24h">Last 24 hours</option><option value="all">All stored time</option></select></label></div></div><HistoryChart title={trendMetric === 'temperature' ? 'Measured and estimated oil temperature' : trendMetric === 'residual' ? 'Thermal residual' : trendMetric === 'loading' ? 'Capacity and worst-phase loading' : trendMetric === 'power' ? 'Apparent power' : trendMetric === 'oil_level' ? 'Oil level' : `Three-phase ${trendMetric}`} points={points} series={series} onSelect={selectReading} selectedId={selectedReadingId} unit={['temperature', 'residual'].includes(trendMetric) ? '°C' : trendMetric === 'voltage' ? 'V' : trendMetric === 'current' ? 'A' : trendMetric === 'power' ? 'kVA' : '%'} /></section>
    <EvidenceRail snapshot={snapshot} selectedId={inspection.historical ? selectedReadingId : null} onSelect={selectReading} onLatest={clearHistory} mode={mode} />{inspection.historical && <section className="card historical-record"><h2>Historical reading {displayId(inspectedSnapshot.latest.readingId)}</h2><MetricDetails metric={selected} snapshot={inspectedSnapshot} mode={mode} /></section>}<div className="history-pager"><span>{snapshot?.history?.length ?? 0} retrieved records · Page {Math.floor(offset / 20) + 1}</span><div><Button variant="outline" size="sm" disabled={mode === 'sample' || offset === 0 || state.phase === 'loading'} onClick={() => setOffset(value => Math.max(0, value - 20))}>Previous</Button><Button variant="outline" size="sm" disabled={mode === 'sample' || (snapshot?.history?.length ?? 0) < 20 || state.phase === 'loading'} onClick={() => setOffset(value => value + 20)}>Next page<ChevronRight size={14} /></Button></div></div><QualityView snapshot={inspectedSnapshot} mode={mode} />
  </> : screen === 'incidents' ? (mode === 'live' && runtime.incidents ? <BackendIncidents key={workflowKey} {...workflowProps} operator={auth.operator} onOpenMaintenanceTask={task => { setOpenedTaskId(task.id); navigate('maintenance'); }} /> : <IncidentsView snapshot={inspectedSnapshot} mode={mode} />) : screen === 'maintenance' ? (mode === 'live' && runtime.sampleMaintenance ? <BackendMaintenance key={`${workflowKey}:${openedTaskId}`} {...workflowProps} operator={auth.operator} initialTaskId={openedTaskId} /> : <MaintenanceView key={`${mode}:${baseUrl}:${activeAssetId}`} mode={mode} baseUrl={baseUrl} assetId={activeAssetId} contractEnabled={runtime.sampleMaintenance === true} onAssetChange={selectAsset} />) : screen === 'whatif' ? (mode === 'live' && runtime.whatIf ? <BackendWhatIf key={workflowKey} {...workflowProps} /> : <WhatIfView key={`${activeAssetId}:${measured?.readingId}`} snapshot={inspectedSnapshot} mode={mode} />) : <ReportsView snapshot={snapshot} mode={mode} onExport={() => setNotice('Retrieved history page exported as CSV.')} />;

  return <MotionConfig reducedMotion="user" transition={motionTiming.micro}><LayoutGroup id="sentinel"><div className={`app-shell ${collapsed ? 'rail-collapsed' : ''}`}><a className="skip-link" href="#main-content">Skip to content</a><Sidebar screen={screen} onNavigate={navigate} mode={mode} onSettings={openSettings} collapsed={collapsed} onCollapse={() => setCollapsed(value => !value)} /><div className="workspace-main"><Topbar screen={screen} mode={mode} theme={theme} onTheme={() => setTheme(value => value === 'dark' ? 'light' : 'dark')} onMenu={() => setMenuOpen(true)} onMode={changeMode} onSettings={openSettings} focused={focused} />
    <main id="main-content" className="main-content"><div className="page-heading"><div><div className="eyebrow"><span />ASSET INTELLIGENCE</div><h1>{titles[screen]}</h1>{screen !== 'twin' && <p>{descriptions[screen]}</p>}</div><div className="heading-actions"><Button variant="outline" size="sm" disabled={state.phase === 'loading' || assets.phase === 'loading'} onClick={() => setRefresh(value => value + 1)}><RefreshCw size={14} />Refresh</Button><Button size="sm" disabled={!snapshot?.history?.length} onClick={exportData}><ArrowDownToLine size={14} />Export report</Button></div></div>
      <section className="asset-context" aria-label="Selected transformer"><span className="asset-context-icon"><Zap size={21} strokeWidth={1.5} /></span><div className="asset-selection"><label><span className="sr-only">Selected transformer</span><select aria-label="Selected transformer" disabled={focused} value={activeAssetId} onChange={event => selectAsset(event.target.value)}>{!activeAssetId && <option value="">{assets.phase === 'loading' ? 'Loading assets…' : 'No registered assets'}</option>}{activeAssetId && !assets.items.some(item => item.asset_id === activeAssetId) && <option value={activeAssetId}>{asset?.name ?? activeAssetId}</option>}{assets.items.filter(item => !focused || item.asset_id === focusedAssetId).map(item => <option value={item.asset_id} key={item.asset_id}>{item.name}</option>)}</select></label><span><span className="asset-id">{displayId(activeAssetId || null, 'No asset')}</span><span className="context-separator">·</span><MapPin size={12} />{displayLocation(asset?.location)}</span></div><div className="asset-context-rating"><strong>{number(asset?.current_configuration?.rated_kva, 0)} <small>kVA</small></strong><span>{asset?.current_configuration?.cooling_type ?? 'Cooling unavailable'} · {asset?.current_configuration?.measurement_side ?? 'Side unknown'}</span></div><div className="data-freshness"><span><span className={`status-dot ${mode === 'live' && source === 'device' && age != null && age > 2 ? 'warning-dot' : 'neutral'}`} />{freshness}</span><small>{measured ? `Measured ${time(measured.measurementTime, true)} IST` : 'Measurement time unavailable'}</small></div></section>
      <div className="stream-toolbar">{mode === 'sample' ? <><label><span className="sr-only">Operating condition</span><select aria-label="Operating condition" value={condition} onChange={event => setCondition(event.target.value)}><option value="steady">Steady loading</option><option value="overload">High loading & temperature</option><option value="missing">Missing oil sensor</option></select></label></> : <><label>Source<select aria-label="Telemetry source" value={source} onChange={event => { setSource(event.target.value); setRunId(''); setRunDraft(''); setOffset(0); }}><option value="device">Device</option><option value="simulator">Stored run</option><option value="file_replay">File replay</option></select></label>{source !== 'device' && <form className="run-form" onSubmit={event => { event.preventDefault(); setRunId(runDraft.trim()); setOffset(0); }}><label><span className="sr-only">Run ID</span><input aria-label="Run ID" maxLength={100} pattern="[A-Za-z0-9][A-Za-z0-9._-]*" required placeholder="Enter stored run ID" value={runDraft} onChange={event => setRunDraft(event.target.value)} /></label><Button type="submit" variant="outline" size="sm">Apply run</Button></form>}<span className="stream-hint">{runId || (source === 'device' ? 'Device stream · run ID is null' : 'Run ID required')}</span><span className="processing-tag">Processing: {displayStatus(snapshot?.analytics?.status ?? snapshot?.latest?.processingJobStatus)}</span></>}
      </div>
      <p className="subtle-note" data-testid="focused-provenance">Asset: {activeAssetId || 'Unavailable'} | Source: {source} | Run: {source === 'device' ? 'none' : runId || 'Unavailable'} | Chart configuration: {chartConfiguration ?? 'Unavailable'} | Stored model: {chartModel ?? 'Unavailable'}. Charts show one configuration/model; historical records remain available in the evidence list.</p>
      {mode === 'sample' && <div className="inline-notice" role="status">Sample UI illustration. These readings, limits and workflow examples are not persisted incidents or physical measurements.</div>}
      {mode === 'live' && source !== 'device' && <div className="inline-notice">{source === 'simulator' ? 'Simulator stream: synthetic inputs' : 'File replay stream: historical inputs'}. Persisted records do not establish physical validation.</div>}
      {mode === 'live' && runtime.incidents && <div className="backend-workflow"><OperatorAuthBar {...auth} /></div>}
      {allErrors.length > 0 && <div className="request-errors" role="alert"><Database size={17} /><div><strong>{assets.phase === 'error' ? 'Asset registry could not be retrieved' : 'Some evidence is unavailable'}</strong><p>{[...new Set(allErrors)].slice(0, 4).join(' ')}</p><small>A request failure does not establish asset failure. Available records remain visible.</small></div><Button size="sm" variant="outline" onClick={() => setRefresh(value => value + 1)}>Retry</Button></div>}
      {mode === 'live' && assets.phase === 'ready' && !assets.items.length && !activeAssetId && <section className="card"><EmptyState title="No transformers registered">Register an asset and configuration through the backend before loading telemetry.</EmptyState></section>}
      {state.phase === 'loading' && <div className="loading-status" role="status"><RefreshCw size={14} />Retrieving selected stream…</div>}
      {mode === 'live' && state.phase === 'ready' && !snapshot?.latest && <div className="inline-notice">This selected stream has no telemetry. Measurements and assessments remain unavailable.</div>}
      <AnimatePresence initial={false} mode="popLayout"><motion.div key={screen} className="page-content" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, pointerEvents: 'none', transition: motionTiming.exit }} transition={motionTiming.view}>{pageContent}</motion.div></AnimatePresence>
    </main>
  </div><AnimatePresence>{notice && <motion.div key={notice} className="toast" role="status" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 3 }} transition={motionTiming.micro}><CheckIcon />{notice}</motion.div>}</AnimatePresence>
  <DetailDialog open={detailsOpen} onOpenChange={setDetailsOpen} title={selected?.label ?? 'Measurement'} sheet><MetricDetails metric={selected} snapshot={inspectedSnapshot} mode={mode} rating={rating} onTrend={() => { setDetailsOpen(false); openTrend(metricTrend(selected.id)); }} /></DetailDialog>
  <DetailDialog open={ratingOpen} onOpenChange={setRatingOpen} title="Transformer Condition Rating" description="Transparent factors, configured limits and coverage" sheet><RatingExplanation result={rating} /></DetailDialog>
  <DetailDialog open={menuOpen} onOpenChange={setMenuOpen} title="Navigation" description="Operator workflows"><Sidebar screen={screen} onNavigate={navigate} mode={mode} onSettings={openSettings} close={() => setMenuOpen(false)} /></DetailDialog>
  <DetailDialog open={settingsOpen} onOpenChange={setSettingsOpen} title="Backend connection" description="Use the verified /api/v1 contracts on your server."><form className="connection-form" onSubmit={event => {
    event.preventDefault();
    if (focused) return;
    try { const url = new URL(baseDraft.trim()); if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error('Use an HTTP(S) address without credentials, query or fragment.'); const next = url.href.replace(/\/+$/, ''); setBaseUrl(next); savePreference('powernxt-api-origin', next); setSettingsOpen(false); setSettingsError(''); setRefresh(value => value + 1); } catch (failure) { setSettingsError(failure.message); }
  }}><label>API base URL<input required type="url" readOnly={focused} value={baseDraft} onChange={event => setBaseDraft(event.target.value)} placeholder="http://localhost:8000" /></label><p>Also configurable with <code>VITE_API_BASE_URL</code>. {focused ? 'The isolated application uses its configured API address.' : 'This browser preference takes precedence.'}</p>{settingsError && <p role="alert" className="error">{settingsError}</p>}<Button type="submit" disabled={focused}>Save connection</Button></form><div className="connection-contracts"><h3>Verified route families</h3><p>Asset registry and telemetry are implemented in this checkout. Analytics and maintenance use the connected server.</p></div></DetailDialog>
  </div></LayoutGroup></MotionConfig>;
}
function CheckIcon() { return <ShieldCheck size={16} />; }
