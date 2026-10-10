import { useState, useRef, useMemo } from 'react';
import TrendChart from './TrendChart.jsx';
import { createWhatIfClient } from '../services/whatIfApi.js';
import { createMaintenanceClient } from '../services/maintenanceApi.js';

const scenarioSeries = [
  { key: 'baseline', label: 'Baseline forecast (healthy model)', color: '#a16207', dashed: true },
  { key: 'alternative', label: 'Reduced load forecast', color: '#0e7490', dashed: true },
];

export default function BackendWhatIf() {
  const whatIfClient = useMemo(() => createWhatIfClient({ baseUrl: import.meta.env.VITE_API_BASE_URL }), []);
  const assetClient = useMemo(() => createMaintenanceClient({ baseUrl: import.meta.env.VITE_API_BASE_URL }), []);

  const [assets, setAssets] = useState([]);
  const [assetsLoaded, setAssetsLoaded] = useState(false);
  const [assetId, setAssetId] = useState('');
  const [source, setSource] = useState('device');
  const [runId, setRunId] = useState('');
  const [stateRef, setStateRef] = useState('');

  // Scenario parameters
  const [durationS, setDurationS] = useState(7200);
  const [ambientC, setAmbientC] = useState(25);
  const [baselineLoadPu, setBaselineLoadPu] = useState(1.2);
  const [reducedLoadPu, setReducedLoadPu] = useState(0.9);

  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [errorDetail, setErrorDetail] = useState(null);
  const [notice, setNotice] = useState('');
  const lock = useRef(false);

  async function loadAssets() {
    setError('');
    setErrorDetail(null);
    try {
      const page = await assetClient.assets(0);
      setAssets(page.items ?? []);
      setAssetsLoaded(true);
    } catch (err) {
      setError(err.message);
    }
  }

  async function runComparison(e) {
    if (e) e.preventDefault();
    if (lock.current) return;
    if (!assetId) {
      setError('Please select a registered transformer.');
      return;
    }
    if (source !== 'device' && !runId.trim()) {
      setError('Simulator and file replay streams require a Run ID.');
      return;
    }
    if (Number(reducedLoadPu) > Number(baselineLoadPu)) {
      setError('Reduced load cannot exceed baseline load.');
      return;
    }

    lock.current = true;
    setBusy(true);
    setError('');
    setErrorDetail(null);
    setNotice('');

    try {
      const outcome = await whatIfClient.compare(assetId, {
        source,
        runId: source === 'device' ? null : runId.trim(),
        stateRef: stateRef.trim() || null,
        durationS: Number(durationS),
        ambientC: Number(ambientC),
        baselineLoadPu: Number(baselineLoadPu),
        reducedLoadPu: Number(reducedLoadPu),
      });

      setResult(outcome.adapted);
      // Automatically keep the state_ref so subsequent runs compare from the exact same snapshot
      if (outcome.adapted.stateRef) {
        setStateRef(outcome.adapted.stateRef);
      }
      setNotice('Scenario forecast generated successfully.');
    } catch (failure) {
      setError(failure.message);
      if (failure.code || failure.reasons) {
        setErrorDetail({ code: failure.code, reasons: failure.reasons || [] });
      }
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  function clearStateRef() {
    setStateRef('');
    setNotice('State reference cleared. Next run will capture the current committed worker watermark state.');
  }

  return (
    <section className="panel">
      <h2>Backend What-if scenario comparison</h2>
      <div className="banner">
        <strong>Conditional healthy-model estimates:</strong> This tool computes deterministic top-oil temperature forecasts using the Model 1.0.2 / 1.0.1 thermal differential equations under constant-load assumptions. Assumed coefficients remain labeled uncalibrated. This does not simulate faults or cooling restoration interventions.
      </div>

      {error && (
        <div role="alert" className="error">
          <strong>{error}</strong>
          {errorDetail && (
            <div style={{ marginTop: '8px', fontSize: '13px' }}>
              <p style={{ margin: '4px 0' }}>Code: <code>{errorDetail.code}</code></p>
              {errorDetail.reasons.length > 0 && (
                <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
                  {errorDetail.reasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              )}
              {errorDetail.code === 'state_unavailable' && (
                <p style={{ marginTop: '6px', color: '#1e293b' }}>
                  <em>Note:</em> The worker has not yet committed forward analytics state for this stream. Ensure telemetry has been ingested and the analytics worker has processed at least one reading.
                </p>
              )}
            </div>
          )}
        </div>
      )}
      {notice && <p role="status" className="success">{notice}</p>}

      <form onSubmit={runComparison}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '15px' }}>
          <div>
            <button disabled={busy} type="button" onClick={loadAssets} style={{ marginBottom: '8px' }}>
              {assetsLoaded ? 'Refresh asset registry' : 'Load registered transformers'}
            </button>
            <label>
              Transformer
              <select
                value={assetId}
                disabled={busy}
                onChange={e => {
                  setAssetId(e.target.value);
                  setResult(null);
                  setStateRef('');
                }}
              >
                <option value="">Select a transformer</option>
                {assets.map(asset => (
                  <option key={asset.asset_id} value={asset.asset_id}>
                    {asset.asset_id} — {asset.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label>
            Stream source
            <select
              value={source}
              disabled={busy}
              onChange={e => {
                setSource(e.target.value);
                if (e.target.value === 'device') setRunId('');
                setResult(null);
                setStateRef('');
              }}
            >
              <option value="device">Device (Live)</option>
              <option value="simulator">Simulator</option>
              <option value="file_replay">File replay</option>
            </select>
          </label>

          {source !== 'device' && (
            <label>
              Run ID
              <input
                type="text"
                placeholder="Enter run ID"
                value={runId}
                disabled={busy}
                onChange={e => {
                  setRunId(e.target.value);
                  setResult(null);
                  setStateRef('');
                }}
              />
            </label>
          )}

          <div>
            <label>
              Initial state reference (UUID)
              <input
                type="text"
                placeholder="Omit to use latest worker watermark state"
                value={stateRef}
                disabled={busy}
                onChange={e => setStateRef(e.target.value)}
              />
            </label>
            {stateRef && (
              <button
                type="button"
                disabled={busy}
                onClick={clearStateRef}
                style={{ fontSize: '11px', padding: '4px 8px', marginTop: '4px' }}
              >
                Clear state ref (capture fresh watermark)
              </button>
            )}
          </div>
        </div>

        <h3 style={{ marginTop: '20px', marginBottom: '10px' }}>Simulation Parameters</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
          <label>
            Forecast horizon (seconds)
            <input
              type="number"
              min={60}
              max={86400}
              step={60}
              value={durationS}
              disabled={busy}
              onChange={e => setDurationS(e.target.value)}
            />
          </label>

          <label>
            Ambient temperature (°C)
            <input
              type="number"
              min={-50}
              max={80}
              step={0.5}
              value={ambientC}
              disabled={busy}
              onChange={e => setAmbientC(e.target.value)}
            />
          </label>

          <label>
            Baseline thermal load (p.u.)
            <input
              type="number"
              min={0}
              max={10}
              step={0.05}
              value={baselineLoadPu}
              disabled={busy}
              onChange={e => setBaselineLoadPu(e.target.value)}
            />
          </label>

          <label>
            Reduced thermal load (p.u.)
            <input
              type="number"
              min={0}
              max={10}
              step={0.05}
              value={reducedLoadPu}
              disabled={busy}
              onChange={e => setReducedLoadPu(e.target.value)}
            />
          </label>
        </div>

        <button
          disabled={busy || !assetId || (source !== 'device' && !runId.trim())}
          type="submit"
          style={{ marginTop: '15px' }}
        >
          {busy ? 'Computing What-if forecast…' : 'Compute What-if forecast'}
        </button>
      </form>

      {result && (
        <div style={{ marginTop: '30px' }}>
          <TrendChart
            title="Future oil temperature: Baseline vs Reduced load forecast"
            points={result.points}
            series={scenarioSeries}
          />

          <div className="metrics" style={{ marginTop: '20px' }}>
            <div className="metric">
              <span>Baseline Peak / Final</span>
              <strong>{result.baselinePeak.toFixed(1)}°C <small>/ {result.baselineFinal.toFixed(1)}°C</small></strong>
              <div className="source">Baseline load: {baselineLoadPu} p.u.</div>
            </div>

            <div className="metric">
              <span>Reduced Peak / Final</span>
              <strong>{result.reducedPeak.toFixed(1)}°C <small>/ {result.reducedFinal.toFixed(1)}°C</small></strong>
              <div className="source">Reduced load: {reducedLoadPu} p.u.</div>
            </div>

            <div className="metric">
              <span>Final Difference</span>
              <strong style={{ color: result.finalDifferenceC < 0 ? '#0e7490' : '#163041' }}>
                {result.finalDifferenceC > 0 ? `+${result.finalDifferenceC.toFixed(2)}` : result.finalDifferenceC.toFixed(2)}°C
              </strong>
              <div className="source">Reduced minus baseline</div>
            </div>

            <div className="metric">
              <span>Configured Top-Oil Limit</span>
              <strong>{result.configuredLimit != null ? `${result.configuredLimit}°C` : 'Not set'}</strong>
              <div className="source">
                {result.baselineCrossing.status === 'crossing'
                  ? `Baseline crosses at ${result.baselineCrossing.time_s}s`
                  : result.baselineCrossing.status === 'no_crossing_within_horizon'
                  ? 'No crossing within horizon'
                  : 'Crossing status unavailable'}
              </div>
            </div>
          </div>

          <div className="panel" style={{ background: '#f8fafc', fontSize: '13px', marginTop: '15px' }}>
            <span className="eyebrow">FORECAST PROVENANCE & MODEL REFERENCES</span>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', marginTop: '10px' }}>
              <div><strong>Model version:</strong> {result.model?.model_version || 'Unavailable'}</div>
              <div><strong>Configuration version:</strong> v{result.configuration?.version}</div>
              <div><strong>Parameter version:</strong> {result.configuration?.parameter_version}</div>
              <div><strong>Origin measurement time:</strong> {new Date(result.origin).toLocaleString()}</div>
              <div style={{ gridColumn: '1 / -1', wordBreak: 'break-all' }}>
                <strong>Captured state reference:</strong> <code>{result.stateRef}</code>
              </div>
            </div>
            <p style={{ marginTop: '10px', color: '#64748b' }}>
              <strong>Assumptions:</strong> {result.assumptions}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
