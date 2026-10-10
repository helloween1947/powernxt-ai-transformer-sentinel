import { useEffect, useRef, useState } from 'react';
import { Database, Play, Upload } from 'lucide-react';
import { Button } from '../ui/button.jsx';
import { createDataInputsClient, datasetChannels } from '../../services/dataInputs.js';
import { number, time } from '../../lib/utils.js';

const scenarios = { normal: 'Normal operation', overload: 'Overload', overheating: 'Overheating', low_oil: 'Low oil level', phase_imbalance: 'Phase imbalance', undervoltage: 'Undervoltage' };
const configFields = [['rated_kva', 'Rated capacity (kVA)', 1000], ['rated_voltage_v', 'Rated line voltage (V)', 11000], ['max_load_pct', 'Maximum loading (%)', 120], ['max_top_oil_temp_c', 'Maximum oil temperature (°C)', 105], ['min_oil_level_pct', 'Minimum oil level (%)', 60], ['max_current_imbalance_pct', 'Maximum current imbalance (%)', 10], ['min_voltage_pu', 'Minimum voltage (pu)', .9], ['max_voltage_pu', 'Maximum voltage (pu)', 1.1]];

export default function DataInputs({ baseUrl, assetId, asset, source, runId, onStream, onAsset, onRefresh }) {
  const controller = useRef(null);
  const [runs, setRuns] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [scenario, setScenario] = useState('normal');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [mapping, setMapping] = useState({});
  const [sheet, setSheet] = useState('');
  const [report, setReport] = useState(null);
  const client = () => createDataInputsClient(baseUrl, controller.current.signal);
  useEffect(() => {
    const active = new AbortController(); controller.current = active;
    if (assetId) createDataInputsClient(baseUrl, active.signal).runs(assetId).then(result => setRuns(result.items)).catch(e => { if (!active.signal.aborted) setError(e.message); });
    return () => active.abort();
  }, [baseUrl, assetId]);
  async function action(work) {
    setBusy(true); setError(''); setMessage('');
    try { await work(); }
    catch (e) { if (!controller.current.signal.aborted) setError(e.message); }
    finally { if (!controller.current.signal.aborted) setBusy(false); }
  }
  async function reloadRuns() { setRuns((await client().runs(assetId)).items); }
  function configurationFrom(form) {
    const entries = Object.fromEntries(configFields.map(([key]) => [key, Number(form.get(key))]));
    const { rated_kva, rated_voltage_v, ...operational_limits } = entries;
    return { rated_kva, rated_voltage_v, operational_limits };
  }
  async function loadPreview(chosen, selectedSheet = '') {
    const form = new FormData(); form.append('file', chosen); if (selectedSheet) form.append('sheet', selectedSheet);
    const result = await client().preview(assetId, form);
    setPreview(result); setSheet(result.selected_sheet ?? '');
    setMapping(Object.fromEntries(datasetChannels.map(([key]) => [key, result.columns.includes(key) ? key : ''])));
  }
  const activeRun = runs.find(run => run.run_id === runId);
  return <details className="card data-inputs" open={!assetId}>
    <summary><Database size={16} />Data inputs & transformer configuration</summary>
    <div className="data-input-grid">
      <section><h2>Live synthetic feed</h2><p>Generate changing readings and test specific operating conditions.</p>
        <label>Operating condition<select aria-label="Synthetic operating condition" value={scenario} onChange={e => setScenario(e.target.value)}>{Object.entries(scenarios).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <Button disabled={busy || !assetId} onClick={() => action(async () => { const run = await client().start({ asset_id: assetId, scenario, interval_seconds: 2, seed: 42 }); await reloadRuns(); onStream('simulator', run.run_id); setMessage('Synthetic feed started. Readings update every 2 seconds.'); })}><Play size={14} />Start feed</Button>
        {source === 'simulator' && activeRun && <div className="input-actions"><Button variant="outline" disabled={busy} onClick={() => action(async () => { await client().update(runId, { scenario }); await reloadRuns(); setMessage('Operating condition updated.'); })}>Apply condition</Button><Button variant="outline" disabled={busy} onClick={() => action(async () => { await client().update(runId, { status: activeRun.status === 'running' ? 'stopped' : 'running' }); await reloadRuns(); onRefresh(); })}>{activeRun.status === 'running' ? 'Stop feed' : 'Resume feed'}</Button></div>}
        <label>Saved feed or dataset<select aria-label="Saved feed or dataset" value={runId} disabled={busy || !runs.length} onChange={e => { const run = runs.find(item => item.run_id === e.target.value); if (run) { onStream(run.source, run.run_id); if (run.scenario) setScenario(run.scenario); setReport(null); if (run.source === 'file_replay') action(async () => setReport(await client().report(assetId, run.run_id))); } }}><option value="">Select a run</option>{runs.map(run => <option key={run.run_id} value={run.run_id}>{run.source === 'simulator' ? `${scenarios[run.scenario]} · ${run.status}` : run.filename} · {run.run_id.slice(0, 8)}</option>)}</select></label>
      </section>
      <section><h2>Upload transformer measurements</h2><p>CSV or XLSX · up to 20,000 rows and 10 MiB. Units must match the mapped fields.</p>
        <label>Dataset<input aria-label="Transformer dataset" type="file" accept=".csv,.xlsx" disabled={busy || !assetId} onChange={e => { const chosen = e.target.files[0]; setFile(chosen ?? null); setPreview(null); setReport(null); if (chosen) action(() => loadPreview(chosen)); }} /></label>
        {preview && <form onSubmit={e => { e.preventDefault(); const values = new FormData(e.currentTarget); action(async () => { const body = new FormData(); body.append('file', file); body.append('column_map', JSON.stringify(Object.fromEntries(Object.entries(mapping).filter(([, value]) => value)))); body.append('timezone_name', values.get('timezone')); if (sheet) body.append('sheet', sheet); const result = await client().upload(assetId, body); setReport(result.analysis); await reloadRuns(); onStream('file_replay', result.run_id); setMessage(`${result.row_count} readings imported and analyzed.`); }); }}>
          {preview.sheets.length > 1 && <label>Worksheet<select value={sheet} disabled={busy} onChange={e => action(() => loadPreview(file, e.target.value))}>{preview.sheets.map(name => <option key={name}>{name}</option>)}</select></label>}
          <div className="column-mapping">{datasetChannels.map(([key, label]) => <label key={key}>{label}<select aria-label={`Dataset column for ${label}`} value={mapping[key] ?? ''} required={key === 'timestamp'} onChange={e => setMapping(previous => ({ ...previous, [key]: e.target.value }))}><option value="">{key === 'timestamp' ? 'Choose time column' : 'Not supplied'}</option>{preview.columns.map(column => <option key={column}>{column}</option>)}</select></label>)}</div>
          <label>Timezone for timestamps without an offset<input name="timezone" defaultValue={asset?.timezone ?? 'UTC'} required placeholder="Asia/Kolkata" /></label><Button type="submit" disabled={busy}><Upload size={14} />Import & analyze</Button>
        </form>}
      </section>
      <section><h2>{assetId ? 'Transformer configuration' : 'Register your transformer'}</h2><p>Use the actual nameplate ratings and approved operating limits. These settings govern the condition checks.</p>
        <form onSubmit={e => { e.preventDefault(); const form = new FormData(e.currentTarget); const configuration = configurationFrom(form); action(async () => { if (assetId) { await client().configure(assetId, configuration); onRefresh(); setMessage('Configuration saved as a new version. Earlier readings retain their original settings.'); } else { const result = await client().assets({ asset_id: form.get('asset_id'), name: form.get('name'), configuration }); onAsset(result.asset_id); } }); }}>
          {!assetId && <><label>Transformer ID<input name="asset_id" required pattern="[A-Za-z0-9_-]+" defaultValue="TX-01" /></label><label>Name<input name="name" required defaultValue="Central distribution transformer" /></label></>}
          <div className="column-mapping">{configFields.map(([key, label, fallback]) => <label key={key}>{label}<input name={key} type="number" step="any" required defaultValue={asset?.current_configuration?.[key] ?? asset?.current_configuration?.operational_limits?.[key] ?? fallback} /></label>)}</div><Button variant="outline" type="submit" disabled={busy}>{assetId ? 'Save configuration' : 'Register transformer'}</Button>
        </form>
      </section>
    </div>
    {busy && <p role="status">Processing…</p>}{error && <p className="data-input-error" role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {report && <section className="dataset-results"><h2>Dataset findings</h2><p>{report.readings_analyzed} readings analyzed · {report.total_findings} configured-limit breaches · {report.unavailable_checks} checks lacked required measurements.</p><div className="input-actions">{Object.entries(report.counts).map(([code, count]) => <span className="tiny-tag" key={code}>{scenarios[code] ?? code}: {count}</span>)}</div>{!report.total_findings && <p>No configured limits were breached in the supplied measurements.</p>}<div className="dataset-table"><table><thead><tr><th>Time (IST)</th><th>Finding</th><th>Value</th><th>Limit</th><th>Reason</th></tr></thead><tbody>{report.items.slice(0, 20).map((item, index) => <tr key={`${item.reading_id}:${item.quantity}:${index}`}><td>{time(item.measurement_time, true)}</td><td>{scenarios[item.code] ?? item.code}</td><td>{number(item.value, 2)} {item.unit === 'C' ? '°C' : item.unit}</td><td>{number(item.threshold, 2)} {item.unit === 'C' ? '°C' : item.unit}</td><td>{item.interpretation}</td></tr>)}</tbody></table></div>{report.total_findings > 20 && <p>Showing the first 20 findings. Counts cover the entire uploaded dataset.</p>}</section>}
  </details>;
}
