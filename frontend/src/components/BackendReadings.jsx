import { useRef, useState } from 'react';
import {
  getAssetPage,
  getAssetDetails,
  getLatestTelemetry,
  getTelemetryHistory,
} from '../services/telemetryApi.js';

const channels = [
  ['voltage_r_v', 'R-phase voltage', 'V'],
  ['voltage_y_v', 'Y-phase voltage', 'V'],
  ['voltage_b_v', 'B-phase voltage', 'V'],
  ['current_r_a', 'R-phase current', 'A'],
  ['current_y_a', 'Y-phase current', 'A'],
  ['current_b_a', 'B-phase current', 'A'],
  ['oil_temperature_c', 'Oil temperature', '°C'],
  ['ambient_temperature_c', 'Ambient temperature', '°C'],
  ['oil_level_pct', 'Oil level', '%'],
];

export default function BackendReadings() {
  const [assets, setAssets] = useState([]);
  const [assetId, setAssetId] = useState('');
  const [source, setSource] = useState('device');
  const [runId, setRunId] = useState('');
  const [details, setDetails] = useState(null);
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState([]);
  const [assetOffset, setAssetOffset] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [assetsLoaded, setAssetsLoaded] = useState(false);
  const [readingsLoaded, setReadingsLoaded] = useState(false);
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const requestLock = useRef(false);

  function clearReadings() {
    setDetails(null);
    setLatest(null);
    setHistory([]);
    setHistoryOffset(0);
    setReadingsLoaded(false);
    setMessages([]);
  }

  async function perform(action) {
    if (requestLock.current) return;

    requestLock.current = true;
    setBusy(true);
    setMessages([]);

    try {
      await action();
    } catch (error) {
      setMessages([error.message]);
    } finally {
      requestLock.current = false;
      setBusy(false);
    }
  }

  function loadAssets(offset = 0) {
    return perform(async () => {
      const page = await getAssetPage(20, offset);

      setAssets(page.items);
      setAssetOffset(offset);
      setAssetsLoaded(true);
    });
  }

  function loadReadings(offset = 0) {
    return perform(async () => {
      if (!assetId.trim()) {
        throw new Error('Select a registered transformer first.');
      }

      if (source !== 'device' && !runId.trim()) {
        throw new Error('Enter the simulator or replay run ID.');
      }

      setLatest(null);
      setHistory([]);
      setDetails(null);
      setReadingsLoaded(false);

      // Confirm the asset exists before interpreting a latest-reading 404.
      const asset = await getAssetDetails(assetId);
      setDetails(asset);

      const selectedRun = source === 'device' ? null : runId.trim();

      const results = await Promise.allSettled([
        getLatestTelemetry(assetId, source, selectedRun),
        getTelemetryHistory(assetId, {
          source,
          runId: selectedRun,
          limit: 20,
          offset,
        }),
      ]);

      const notes = [];
      const latestResult = results[0];
      const historyResult = results[1];

      if (latestResult.status === 'fulfilled') {
        setLatest(latestResult.value);
      } else {
        notes.push(
          latestResult.reason.status === 404
            ? 'No latest reading exists for this selected stream.'
            : `Latest reading: ${latestResult.reason.message}`,
        );
      }

      if (historyResult.status === 'fulfilled') {
        setHistory(historyResult.value.items);
        setHistoryOffset(offset);
      } else {
        notes.push(`History: ${historyResult.reason.message}`);
      }

      setMessages(notes);
      setReadingsLoaded(true);
    });
  }

  return (
    <section className="panel">
      <h2>Backend readings</h2>

      <p>
        This screen requests the asset registry and stored telemetry.
        It does not generate predictions, health scores, or alerts.
      </p>

      <button disabled={busy} onClick={() => loadAssets(0)}>
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
              disabled={busy || assetOffset === 0}
              onClick={() => loadAssets(assetOffset - 20)}
            >
              Previous asset page
            </button>
            <button
              disabled={busy || assets.length < 20}
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
          disabled={busy}
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
          disabled={busy}
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
            disabled={busy}
            placeholder="Enter the exact run ID from Person A"
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

      {busy && <p role="status">Loading backend data…</p>}

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

          <p>
            Analytical outputs are not displayed here because no verified
            result-retrieval contract has been connected.
          </p>
        </>
      )}

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
                    <th>Analytics</th>
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
                      <td>{reading.analyticsStatus}</td>
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