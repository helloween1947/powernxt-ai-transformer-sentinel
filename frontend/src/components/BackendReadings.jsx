import { useEffect, useRef, useState } from 'react';
import StoredAnalytics from './StoredAnalytics.jsx';
import ThermalComparison from './ThermalComparison.jsx';
import { telemetryClient, getAssetPage } from '../services/telemetryApi.js';
import { createStreamLoader } from '../services/storedStream.js';

const channels = [
  ['voltage_r_v', 'R-phase voltage', 'V'], ['voltage_y_v', 'Y-phase voltage', 'V'], ['voltage_b_v', 'B-phase voltage', 'V'],
  ['current_r_a', 'R-phase current', 'A'], ['current_y_a', 'Y-phase current', 'A'], ['current_b_a', 'B-phase current', 'A'],
  ['oil_temperature_c', 'Oil temperature', '°C'], ['ambient_temperature_c', 'Ambient temperature', '°C'], ['oil_level_pct', 'Oil level', '%'],
];

export default function BackendReadings() {
  const [assets, setAssets] = useState([]);
  const [assetId, setAssetId] = useState('');
  const [source, setSource] = useState('device');
  const [runId, setRunId] = useState('');
  const [assetOffset, setAssetOffset] = useState(0);
  const [assetsLoaded, setAssetsLoaded] = useState(false);
  const [assetBusy, setAssetBusy] = useState(false);
  const [assetError, setAssetError] = useState('');
  const [state, setState] = useState({ phase: 'idle' });
  const loader = useRef(null);
  const assetRequest = useRef(null);
  useEffect(() => {
    const active = createStreamLoader(telemetryClient, setState);
    loader.current = active;
    return () => { active.cancel(); assetRequest.current?.abort(); };
  }, []);

  const snapshot = state.snapshot;
  const details = snapshot?.details;
  const latest = snapshot?.latest;
  const analytics = snapshot?.analytics;
  const history = snapshot?.history ?? [];
  const historyOffset = snapshot?.page?.offset ?? 0;
  const readingsLoaded = !!snapshot;
  const busy = state.phase === 'loading';
  const messages = [assetError, state.message, ...(snapshot?.errors ?? [])].filter(Boolean);

  function clearReadings() {
    loader.current?.cancel();
    setState({ phase: 'idle' });
  }
  async function loadAssets(offset = 0) {
    assetRequest.current?.abort();
    const controller = new AbortController();
    assetRequest.current = controller;
    setAssetBusy(true);
    setAssetError('');
    try {
      const page = await getAssetPage(20, offset, controller.signal);
      if (controller.signal.aborted) return;
      setAssets(page.items); setAssetOffset(offset); setAssetsLoaded(true);
    } catch (error) { if (!controller.signal.aborted) setAssetError(error.message); }
    finally { if (!controller.signal.aborted) setAssetBusy(false); }
  }
  function loadReadings(offset = 0) {
    if (!assetId || (source !== 'device' && !runId.trim())) return;
    loader.current?.start({assetId, source, runId: source === 'device' ? null : runId.trim(), offset});
  }

  return (
    <section className="panel">
      <h2>Backend readings</h2>

      <p>
        This screen requests the asset registry and stored telemetry.
        It does not generate predictions, health scores, or alerts. Simulator and replay timestamps describe stored demonstrations, not fresh device telemetry. Empty quality flags do not establish transformer health.
      </p>

      <button disabled={assetBusy} onClick={() => loadAssets(0)}>
        Load registered transformers
      </button>

      {assetsLoaded && (
        <>
          <p>
            Asset page: {Math.floor(assetOffset / 20) + 1}.
            Showing {assets.length} asset(s).
          </p>

          <div className="actions">
            <button
              disabled={assetBusy || assetOffset === 0}
              onClick={() => loadAssets(assetOffset - 20)}
            >
              Previous asset page
            </button>
            <button
              disabled={assetBusy || assets.length < 20}
              onClick={() => loadAssets(assetOffset + 20)}
            >
              Next asset page
            </button>
          </div>

          {!assets.length && <p>No assets on this page.</p>}
        </>
      )}

      <label>
        Registered transformer
        <select
          value={assetId}
          onChange={event => {
            setAssetId(event.target.value);
            clearReadings();
          }}
        >
          <option value="">Select a transformer</option>
          {assetId && !assets.some(asset => asset.asset_id === assetId) && (
            <option value={assetId}>{assetId}</option>
          )}
          {assets.map(asset => (
            <option key={asset.asset_id} value={asset.asset_id}>
              {asset.asset_id} — {asset.name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Telemetry source
        <select
          value={source}
          onChange={event => {
            setSource(event.target.value);
            setRunId('');
            clearReadings();
          }}
        >
          <option value="device">Device</option>
          <option value="simulator">Simulator</option>
          <option value="file_replay">File replay</option>
        </select>
      </label>

      {source !== 'device' && (
        <label>
          Run ID
          <input
            value={runId}
              placeholder="Enter the run ID generated on this backend"
            onChange={event => {
              setRunId(event.target.value);
              clearReadings();
            }}
          />
        </label>
      )}

      <p>
        Selected stream: {assetId || 'No asset selected'} / {source} /
        {' '}{source === 'device' ? 'No run ID' : runId || 'Run ID required'}
      </p>

      <button
        disabled={busy || !assetId || (source !== 'device' && !runId.trim())}
        onClick={() => loadReadings(0)}
      >
        Load latest reading and history
      </button>

      {busy && <p role="status">Loading backend data… Stream controls remain available; changing a filter cancels this request.</p>}
      {assetBusy && <p role="status">Loading asset registry…</p>}
      {state.polling && <p role="status">Processing is active. Polling every 5 seconds, up to six refreshes ({state.poll}/6).</p>}
      {state.exhausted && <p role="status">Polling limit reached. Use Load latest reading and history to check again.</p>}
      {snapshot && <p>Last successful API retrieval (UTC): {snapshot.retrievedAt}. Connectivity and processing status do not make historical measurement timestamps current.</p>}

      {messages.map(message => (
        <p className="error" role="alert" key={message}>
          {message}
        </p>
      ))}

      {details && (
        <>
          <h3>{details.name}</h3>
          <p>Asset ID: {details.asset_id}</p>
          <p>Location: {details.location}</p>
          <p>
            Current registry configuration:
            {' '}{details.current_configuration?.version ?? 'Unavailable'}
          </p>
          <p>
            Rated capacity:
            {' '}{details.current_configuration?.rated_kva == null
              ? 'Unavailable'
              : `${details.current_configuration.rated_kva} kVA`}
          </p>
        </>
      )}

      {latest && (
        <>
          <h3>Latest stored reading</h3>

          <p>
            Measurement time:
            {' '}{new Date(latest.measurementTime).toLocaleString()}
          </p>
          <p>
            Arrival time:
            {' '}{new Date(latest.arrivalTime).toLocaleString()}
          </p>
          <p>
            Source: {latest.source} / Run: {latest.runId ?? 'None'}
          </p>
          <p>Reading configuration: {latest.configurationVersion}</p>
          <p>Analytics status: {latest.analyticsStatus}</p>
          <p>Processing job: {latest.processingJobStatus}</p>
          <p>
            Out of order:
            {' '}{latest.outOfOrder == null
              ? 'Unavailable'
              : latest.outOfOrder ? 'Yes' : 'No'}
          </p>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Channel</th>
                  <th>Value</th>
                  <th>Unit</th>
                  <th>Quality</th>
                </tr>
              </thead>
              <tbody>
                {channels.map(([key, label, unit]) => {
                  const flags = latest.qualityFlags[key] ?? [];

                  return (
                    <tr key={key}>
                      <td>{label}</td>
                      <td>{latest.measurements[key] ?? 'Unavailable'}</td>
                      <td>{unit}</td>
                      <td>
                        {flags.length
                          ? flags.join(', ')
                          : latest.measurementQuality[key] ?? 'Not provided'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {analytics && <StoredAnalytics analytics={analytics} />}
        </>
      )}

      {readingsLoaded && <>
        {!latest && <p>No latest reading exists for this selected stream.</p>}
        <ThermalComparison points={snapshot.points} latestEnvelope={snapshot.latestEnvelope} completedAnalytics={snapshot.completedAnalytics} />
        {snapshot.completedAnalytics && snapshot.completedAnalytics.reading_id !== analytics?.reading_id && <StoredAnalytics analytics={snapshot.completedAnalytics} title="Latest completed analytics — separate stored reading" />}
      </>}

      {readingsLoaded && (
        <>
          <h3>Stored history — oldest first</h3>
          <p>History page: {Math.floor(historyOffset / 20) + 1}</p>

          {!history.length ? (
            <p>No history readings on this page.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Reading ID</th>
                    <th>Measurement time</th>
                    <th>Oil temperature (°C)</th>
                    <th>Arrival time</th><th>Configuration</th><th>Source / run</th><th>Analytics / job</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map(reading => (
                    <tr key={reading.readingId}>
                      <td>{reading.readingId}</td>
                      <td>
                        {new Date(reading.measurementTime).toLocaleString()}
                      </td>
                      <td>
                        {reading.measurements.oil_temperature_c
                          ?? 'Unavailable'}
                      </td>
                      <td>{new Date(reading.arrivalTime).toLocaleString()}</td><td>{reading.configurationVersion}</td><td>{reading.source} / {reading.runId ?? 'None'}</td><td>{reading.analyticsStatus} / {reading.processingJobStatus}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="actions">
            <button
              disabled={busy || historyOffset === 0}
              onClick={() => loadReadings(historyOffset - 20)}
            >
              Previous history page
            </button>
            <button
              disabled={busy || history.length < 20}
              onClick={() => loadReadings(historyOffset + 20)}
            >
              Next history page
            </button>
          </div>
        </>
      )}
    </section>
  );
}
