import { useEffect, useRef, useState } from 'react';
import ReadingCard from './components/ReadingCard';
import TrendChart from './components/TrendChart';
import { DEMO_MODE, getAssets, getDashboard, compareScenarios, acknowledgeAlert, getTasks, createTask, updateTask } from './services/api';

const screens = ['Fleet', 'Transformer', 'Alerts', 'What-if', 'Maintenance'];
const temperatureSeries = [
  { key: 'measuredOil', label: 'Observed oil temperature', color: '#0e7490' },
  { key: 'predictedOil', label: 'Twin prediction', color: '#a16207', dashed: true },
];

export default function App() {
  const [screen, setScreen] = useState('Fleet');
  const [assets, setAssets] = useState([]);
  const [assetId, setAssetId] = useState('');
  const [scenario, setScenario] = useState('overload');
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const actionLock = useRef(false);
  const [retry, setRetry] = useState(0);
  const [clock, setClock] = useState(() => Date.now());
  const [alternative, setAlternative] = useState('lower-load');
  const [comparison, setComparison] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [owner, setOwner] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [taskAlert, setTaskAlert] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getAssets().then(result => { if (!cancelled) { setAssets(result); setAssetId(current => current || result[0]?.id || ''); if (!result.length) setLoading(false); } }).catch(err => { if (!cancelled) { setError(err.message); setLoading(false); } });
    return () => { cancelled = true; };
  }, [retry]);

  useEffect(() => {
    if (!assetId) return;
    let cancelled = false;
    let pending = false;
    async function load() {
      if (pending) return;
      pending = true;
      try {
        const result = await getDashboard(assetId, scenario);
        if (!cancelled) { setDashboard(result); setError(''); }
      } catch (err) { if (!cancelled) setError(err.message); }
      finally { pending = false; if (!cancelled) setLoading(false); }
    }
    load();
    const timer = DEMO_MODE ? null : setInterval(load, 5000);
    return () => { cancelled = true; if (timer) clearInterval(timer); };
  }, [assetId, scenario, retry]);

  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (screen === 'Maintenance') getTasks().then(setTasks).catch(err => setError(err.message));
  }, [screen]);

  function resetDashboardView() {
  setDashboard(null);
  setLoading(true);
  setComparison(null);
  setError('');
  setNotice('');
}

function changeAsset(nextId) {
  if (nextId !== assetId) {
    resetDashboardView();
    setAssetId(nextId);
  }
  setTaskAlert(null);
  setTaskTitle('');
}

function changeScenario(nextScenario) {
  if (nextScenario !== scenario) {
    resetDashboardView();
    setScenario(nextScenario);
  }
  setTaskAlert(null);
  setTaskTitle('');
}

function reloadDashboard() {
  resetDashboardView();
  setRetry(value => value + 1);
}
async function run(action) {
    if (actionLock.current) return;
    actionLock.current = true; setBusy(true); setError(''); setNotice('');
    try { await action(); }
    catch (err) { setError(err.message); }
    finally { actionLock.current = false; setBusy(false); }
  }

  const stale = dashboard && !DEMO_MODE && clock - Date.parse(dashboard.timestamp) > (dashboard.staleAfterSeconds ?? 30) * 1000;
  const alerts = dashboard?.alerts ?? [];

  function openTask(alert) {
    setTaskAlert(alert); setTaskTitle(alert.recommendation); setScreen('Maintenance');
  }

  async function saveTask(event) {
    event.preventDefault();
    await run(async () => {
      const saved = await createTask({ title: taskTitle.trim(), owner: owner.trim(), assetId, alertId: taskAlert?.id ?? null, evidence: taskAlert?.evidence ?? '', recommendation: taskAlert?.recommendation ?? '' });
      setTasks(await getTasks()); setTaskTitle(''); setTaskAlert(null);
      setNotice(`Task saved: ${saved.title}`);
    });
  }

  return <div className="shell">
    <aside><div className="brand">Transformer<br /><strong>Sentinel</strong></div><p>Operator dashboard</p><nav aria-label="Main navigation">{screens.map(item => <button key={item} aria-current={screen === item ? 'page' : undefined} onClick={() => setScreen(item)}>{item}</button>)}</nav><div className="aside-note">Person C starter<br />{DEMO_MODE ? 'Sample data mode' : 'API mode: 5-second polling'}</div></aside>
    <main>
      <header><div><span className="eyebrow">POWER SYSTEM CONDITION MONITORING</span><h1>{screen === 'Fleet' ? 'Fleet overview' : screen === 'Transformer' ? 'Transformer detail' : screen === 'What-if' ? 'What-if comparison' : screen}</h1></div><label>Transformer<select value={assetId} disabled={busy} onChange={event => changeAsset(event.target.value)}>{assets.map(asset => <option key={asset.id} value={asset.id}>{asset.id} — {asset.name}</option>)}</select></label></header>
      {DEMO_MODE && <div className="banner">DEMO: sensor readings, health, alerts and forecast curves are illustrative fixtures. Tasks are saved only in this browser. This mode does not run B's model or D's maintenance backend.</div>}
      {DEMO_MODE && <label className="scenario">Sample condition<select value={scenario} disabled={busy} onChange={event => changeScenario(event.target.value)}><option value="normal">Normal operation</option><option value="overload">Overload / abnormal heating</option><option value="sensor-loss">Oil sensor loss</option></select></label>}
      {error && <div role="alert" className="error">{error} <button onClick={reloadDashboard}>Retry data loading</button></div>}
      {notice && <div role="status" className="success">{notice}</div>}
      {loading && <p role="status">Loading transformer data...</p>}
      {!loading && !assets.length && !error && <p>No transformers registered.</p>}
      {dashboard && <>
        <div className="status-line"><span>{dashboard.asset.name} · {dashboard.asset.rating}</span><span>{DEMO_MODE ? 'Sample timestamp' : 'Last sensor timestamp'}: {new Date(dashboard.timestamp).toLocaleString()} {stale && <strong className="warning"> STALE DATA</strong>}</span></div>
        {screen === 'Fleet' && <section className="panel"><h2>Registered transformers</h2><p>Select an asset to inspect its latest readings. This starter loads condition details for the selected asset.</p><div className="asset-grid">{assets.map(asset => <button className="asset" key={asset.id} onClick={() => { changeAsset(asset.id); setScreen('Transformer'); }}><strong>{asset.id}</strong><span>{asset.name}</span><small>{asset.rating}</small>{asset.id === assetId && <small>{dashboard.analytics.condition} · {alerts.length} alert(s)</small>}</button>)}</div></section>}
        {(screen === 'Fleet' || screen === 'Transformer') && <>
          <div className="metrics"><ReadingCard label="Loading" value={dashboard.readings.loading} unit="%" source={dashboard.source} /><ReadingCard label="Oil temperature" value={dashboard.readings.oilTemperature} unit="C" source={dashboard.source} /><ReadingCard label="Ambient temperature" value={dashboard.readings.ambientTemperature} unit="C" source={dashboard.source} /><ReadingCard label="Data confidence" value={dashboard.analytics.confidence} unit="" source="Analytics assessment" /></div>
          <section className="panel"><h2>Condition: {dashboard.analytics.condition}</h2><p>Data quality: {dashboard.dataQuality}</p><ul>{dashboard.analytics.contributors.map(item => <li key={item}>{item}</li>)}</ul><button onClick={() => setScreen('Alerts')}>Inspect alerts ({alerts.length})</button></section>
        </>}
        {screen === 'Transformer' && <>
          <section className="panel"><h2>Electrical readings</h2><div className="table-wrap"><table><thead><tr><th>Phase</th><th>Voltage (V)</th><th>Current (A)</th><th>Source</th></tr></thead><tbody>{['A', 'B', 'C'].map((phase, index) => <tr key={phase}><td>{phase}</td><td>{dashboard.readings.voltage[index] ?? 'Unavailable'}</td><td>{dashboard.readings.current[index] ?? 'Unavailable'}</td><td>{dashboard.source}</td></tr>)}</tbody></table></div></section>
          <section className="panel"><TrendChart title="Observed temperature versus twin prediction" points={dashboard.history} series={temperatureSeries} /></section>
        </>}
        {screen === 'Alerts' && <section className="panel"><h2>Alert investigation</h2>{!alerts.length && <p>No active alerts for this transformer.</p>}{alerts.map(alert => <article className="alert-card" key={alert.id}><span className="badge">{alert.severity} · {alert.status}</span><h3>{alert.type}</h3><p><strong>Evidence:</strong> {alert.evidence}</p><p><strong>Recommendation:</strong> {alert.recommendation}</p><p>First seen: {new Date(alert.firstSeen).toLocaleString()}</p><div className="actions"><button disabled={busy || alert.status === 'Acknowledged'} onClick={() => run(async () => { await acknowledgeAlert(alert.id); setDashboard(current => ({ ...current, alerts: current.alerts.map(item => item.id === alert.id ? { ...item, status: 'Acknowledged' } : item) })); setNotice(DEMO_MODE ? 'Acknowledged in this preview; acknowledgement resets when sample data reloads.' : 'Alert acknowledged.'); })}>Acknowledge</button><button disabled={busy} onClick={() => openTask(alert)}>Create maintenance task</button></div></article>)}{alerts.length > 0 && <TrendChart title="Temperature evidence" points={dashboard.history} series={temperatureSeries} />}</section>}
        {screen === 'What-if' && <section className="panel"><h2>Compare possible actions</h2><p>{DEMO_MODE ? 'Try two fixed UI examples. The sample curves are not tied to the selected operating condition.' : 'The scenario identifiers and result format must be agreed with Person B.'}</p><label>Alternative<select value={alternative} disabled={busy} onChange={event => { setAlternative(event.target.value); setComparison(null); }}><option value="lower-load">Reduce loading</option><option value="restore-cooling">Restore cooling</option></select></label><button className="compare-button" disabled={busy} onClick={() => run(async () => setComparison(await compareScenarios(assetId, alternative)))}>{busy ? 'Comparing...' : 'Compare scenarios'}</button>{comparison && <><p>{comparison.assumptions}</p><p>{comparison.explanation}</p><TrendChart title="Future oil temperature — baseline and alternative" points={comparison.points} series={[{ key: 'baseline', label: 'Baseline forecast', color: '#a16207', dashed: true }, { key: 'alternative', label: 'Alternative forecast', color: '#0e7490', dashed: true }]} /><button onClick={() => { setTaskTitle('Review the scenario comparison and arrange an inspection'); setTaskAlert(null); setScreen('Maintenance'); }}>Prepare maintenance task</button></>}</section>}
        {screen === 'Maintenance' && <section className="panel"><h2>Create maintenance task</h2>{taskAlert && <p>Linked alert: {taskAlert.id} · {taskAlert.evidence}</p>}<form onSubmit={saveTask}><label>Task title<input required maxLength={200} value={taskTitle} onChange={event => setTaskTitle(event.target.value)} /></label><label>Assigned person<input required maxLength={100} value={owner} onChange={event => setOwner(event.target.value)} /></label><button disabled={busy || !taskTitle.trim() || !owner.trim()} type="submit">{busy ? 'Saving...' : 'Save task'}</button></form><h2>Saved tasks</h2>{!tasks.length && <p>No maintenance tasks created yet.</p>}{tasks.map(task => <article key={task.id} className="task"><h3>{task.title}</h3><p>{task.assetId} · Assigned to {task.owner} · {task.status}</p>{task.alertId && <p>Linked alert: {task.alertId}</p>}{task.evidence && <p>Evidence: {task.evidence}</p>}<form onSubmit={event => { event.preventDefault(); const values = new FormData(event.currentTarget); run(async () => { await updateTask(task.id, { status: values.get('status'), notes: values.get('notes') }); setTasks(await getTasks()); setNotice('Task updated.'); }); }}><label>Status<select name="status" defaultValue={task.status}><option>Open</option><option>In progress</option><option>Completed</option></select></label><label>Completion / progress notes<textarea name="notes" defaultValue={task.notes} maxLength={2000} /></label><button disabled={busy}>Save changes</button></form></article>)}</section>}
      </>}
    </main>
  </div>;
}
