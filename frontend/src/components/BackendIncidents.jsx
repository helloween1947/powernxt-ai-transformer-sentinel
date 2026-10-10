import { useState, useRef, useMemo } from 'react';
import { createIncidentClient } from '../services/incidentApi.js';
import { createMaintenanceClient } from '../services/maintenanceApi.js';
import { severityColors, conditionColors, monitoringColors } from '../services/incidentAdapter.js';

export default function BackendIncidents({ operator, onOpenMaintenanceTask }) {
  const incidentClient = useMemo(() => createIncidentClient({ baseUrl: import.meta.env.VITE_API_BASE_URL }), []);
  const maintenanceClient = useMemo(() => createMaintenanceClient({ baseUrl: import.meta.env.VITE_API_BASE_URL }), []);

  const [assets, setAssets] = useState([]);
  const [assetsLoaded, setAssetsLoaded] = useState(false);
  const [assetId, setAssetId] = useState('');
  const [source, setSource] = useState('device');
  const [runId, setRunId] = useState('');
  const [conditionFilter, setConditionFilter] = useState('');

  const [incidents, setIncidents] = useState([]);
  const [incidentsLoaded, setIncidentsLoaded] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [events, setEvents] = useState([]);
  const [evidence, setEvidence] = useState([]);

  // Maintenance task creation from incident
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskOwner, setTaskOwner] = useState('');
  const [taskSummary, setTaskSummary] = useState('');

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const lock = useRef(false);

  async function perform(action) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
    } catch (failure) {
      setError(failure.message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  async function loadAssets() {
    await perform(async () => {
      const page = await maintenanceClient.assets(0);
      setAssets(page.items ?? []);
      setAssetsLoaded(true);
    });
  }

  async function loadIncidents() {
    if (!operator?.token) {
      setError('Operator authentication token is required to list incidents.');
      return;
    }
    if (!assetId) {
      setError('Please select a registered transformer.');
      return;
    }
    if (source !== 'device' && !runId.trim()) {
      setError('Simulator and file replay streams require a Run ID.');
      return;
    }

    await perform(async () => {
      setSelectedIncident(null);
      setEvents([]);
      setEvidence([]);
      const page = await incidentClient.listIncidents({
        assetId,
        source,
        runId: source === 'device' ? null : runId.trim(),
        conditionStatus: conditionFilter || null,
        token: operator.token,
      });
      setIncidents(page.items);
      setIncidentsLoaded(true);
      if (!page.items.length) {
        setNotice('No incidents found for the selected stream and filter.');
      }
    });
  }

  async function inspectIncident(incident) {
    setSelectedIncident(incident);
    await perform(async () => {
      const [eventsPage, evidencePage] = await Promise.all([
        incidentClient.getEvents(incident.id, { token: operator.token }),
        incidentClient.getEvidence(incident.id, { token: operator.token }),
      ]);
      setEvents(eventsPage.items);
      setEvidence(evidencePage.items);
    });
  }

  async function handleAcknowledge(incident) {
    if (!operator?.token) return;
    const canAck = operator.role === 'operator' || operator.role === 'admin';
    if (!canAck) {
      setError('Only operator and admin roles can acknowledge incidents.');
      return;
    }

    await perform(async () => {
      const idempotencyKey = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-ack`;
      const updated = await incidentClient.acknowledge(incident.id, {
        expectedVersion: incident.version,
        idempotencyKey,
        token: operator.token,
      });

      setIncidents(current => current.map(item => item.id === updated.id ? updated : item));
      setSelectedIncident(updated);
      setNotice(`Incident ${updated.id.slice(0, 8)}… acknowledged at version ${updated.version}.`);

      // Refresh events
      const eventsPage = await incidentClient.getEvents(updated.id, { token: operator.token });
      setEvents(eventsPage.items);
    });
  }

  function openCreateTask(incident) {
    setTaskTitle(`Resolve incident: ${incident.category} (${incident.severity})`);
    setTaskOwner('');
    setTaskSummary(`Incident ${incident.id} on ${incident.assetId} (${incident.conditionStatus}). Severity: ${incident.severity}. Opened at: ${incident.openedAt}.`);
    setTaskModalOpen(true);
  }

  async function submitCreateTask(e) {
    e.preventDefault();
    if (!selectedIncident || !operator?.token) return;

    await perform(async () => {
      const saved = await maintenanceClient.create({
        assetId: selectedIncident.assetId,
        incidentId: selectedIncident.id,
        summary: taskSummary,
        title: taskTitle,
        owner: taskOwner,
        sampleMode: false,
      }, operator.token);

      setNotice(`Maintenance task created: ${saved.id}.`);
      setTaskModalOpen(false);
      if (onOpenMaintenanceTask) {
        onOpenMaintenanceTask(saved);
      }
    });
  }

  return (
    <section className="panel">
      <h2>Backend incidents</h2>
      <p>
        Live incident investigation and operational acknowledgement. Incidents are authoritative backend records evaluated by genuine detectors and persisted with immutable audit trails.
      </p>

      {error && <p role="alert" className="error">{error}</p>}
      {notice && <p role="status" className="success">{notice}</p>}

      {!operator && (
        <div className="banner" style={{ background: '#fef2f2', borderColor: '#fca5a5', color: '#991b1b' }}>
          <strong>Authentication required:</strong> Use the Operator Authentication bar above to enter a Bearer token before querying incidents.
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '15px', margin: '15px 0' }}>
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
                setIncidentsLoaded(false);
                setSelectedIncident(null);
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
              setIncidentsLoaded(false);
              setSelectedIncident(null);
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
                setIncidentsLoaded(false);
                setSelectedIncident(null);
              }}
            />
          </label>
        )}

        <label>
          Condition status filter
          <select
            value={conditionFilter}
            disabled={busy}
            onChange={e => setConditionFilter(e.target.value)}
          >
            <option value="">All conditions</option>
            <option value="active">Active</option>
            <option value="recovered">Recovered</option>
          </select>
        </label>
      </div>

      <button
        disabled={busy || !operator || !assetId || (source !== 'device' && !runId.trim())}
        type="button"
        onClick={loadIncidents}
        style={{ marginBottom: '20px' }}
      >
        {busy ? 'Loading incidents…' : 'Query stream incidents'}
      </button>

      {incidentsLoaded && (
        <>
          <h3>Incidents ({incidents.length})</h3>
          {!incidents.length ? (
            <p>No incidents found matching this stream and criteria.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Severity</th>
                    <th>Condition</th>
                    <th>Monitoring</th>
                    <th>Opened at</th>
                    <th>Acknowledgement</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map(inc => {
                    const isSelected = selectedIncident?.id === inc.id;
                    return (
                      <tr key={inc.id} style={{ background: isSelected ? '#f0f9ff' : undefined }}>
                        <td>
                          <strong>{inc.category}</strong>
                          <br />
                          <small style={{ color: '#64748b' }}>{inc.id.slice(0, 8)}…</small>
                        </td>
                        <td>
                          <span
                            className="badge"
                            style={{
                              background: '#fff',
                              border: `1px solid ${severityColors[inc.severity] || '#64748b'}`,
                              color: severityColors[inc.severity] || '#64748b',
                              fontWeight: 600,
                            }}
                          >
                            {inc.severity}
                          </span>
                        </td>
                        <td>
                          <span style={{ color: conditionColors[inc.conditionStatus] || '#000', fontWeight: 600 }}>
                            {inc.conditionStatus}
                          </span>
                        </td>
                        <td>
                          <span style={{ color: monitoringColors[inc.monitoringStatus] || '#000' }}>
                            {inc.monitoringStatus}
                          </span>
                        </td>
                        <td>{new Date(inc.openedAt).toLocaleString()}</td>
                        <td>
                          {inc.acknowledgement.status === 'acknowledged' ? (
                            <span style={{ color: '#15803d', fontWeight: 600 }}>Acknowledged</span>
                          ) : (
                            <span style={{ color: '#b91c1c' }}>Unacknowledged</span>
                          )}
                        </td>
                        <td>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => inspectIncident(inc)}
                            style={{ padding: '6px 12px', fontSize: '12px' }}
                          >
                            {isSelected ? 'Viewing' : 'Inspect'}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {selectedIncident && (
        <div className="panel" style={{ marginTop: '24px', border: '1px solid #93c5fd', background: '#f8fafc' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '15px' }}>
            <div>
              <span className="eyebrow">INCIDENT DETAILS</span>
              <h3 style={{ margin: '4px 0' }}>{selectedIncident.category}</h3>
              <p style={{ margin: 0, fontSize: '13px', color: '#475569' }}>
                ID: {selectedIncident.id} · Version: {selectedIncident.version}
              </p>
            </div>

            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {selectedIncident.acknowledgement.status !== 'acknowledged' ? (
                <button
                  type="button"
                  disabled={busy || (operator.role !== 'operator' && operator.role !== 'admin')}
                  onClick={() => handleAcknowledge(selectedIncident)}
                  style={{ background: '#0e7490', color: '#fff', borderColor: '#0e7490' }}
                >
                  {busy ? 'Processing…' : 'Acknowledge incident'}
                </button>
              ) : (
                <span className="badge" style={{ background: '#dcfce7', color: '#166534', fontWeight: 600, padding: '8px 12px' }}>
                  Acknowledged ({selectedIncident.acknowledgement.acknowledgedAt ? new Date(selectedIncident.acknowledgement.acknowledgedAt).toLocaleTimeString() : 'Recorded'})
                </span>
              )}

              <button
                type="button"
                disabled={busy}
                onClick={() => openCreateTask(selectedIncident)}
              >
                Create maintenance task
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginTop: '16px', fontSize: '13px' }}>
            <div><strong>Asset ID:</strong> {selectedIncident.assetId}</div>
            <div><strong>Severity:</strong> {selectedIncident.severity}</div>
            <div><strong>Condition:</strong> {selectedIncident.conditionStatus}</div>
            <div><strong>Monitoring:</strong> {selectedIncident.monitoringStatus}</div>
            <div><strong>Opened At:</strong> {new Date(selectedIncident.openedAt).toLocaleString()}</div>
            <div><strong>Recovered At:</strong> {selectedIncident.recoveredAt ? new Date(selectedIncident.recoveredAt).toLocaleString() : 'None'}</div>
            <div><strong>Last Evaluated:</strong> {new Date(selectedIncident.lastEvaluatedTime).toLocaleString()}</div>
            <div><strong>Evidence Status:</strong> {selectedIncident.lastEvidenceStatus}</div>
            <div style={{ gridColumn: '1 / -1', wordBreak: 'break-all' }}>
              <strong>Detector Epoch:</strong> {selectedIncident.detectorEpoch} · <strong>Episode Key:</strong> {selectedIncident.detectorEpisodeKey}
            </div>
          </div>

          {/* Events Timeline */}
          <h4 style={{ marginTop: '20px', marginBottom: '8px' }}>Events Timeline ({events.length})</h4>
          {!events.length ? (
            <p style={{ fontSize: '13px', color: '#64748b' }}>No events recorded for this incident.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Event type</th>
                    <th>Recorded at</th>
                    <th>Actor ID</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map(ev => (
                    <tr key={ev.eventId}>
                      <td>v{ev.incidentVersion}</td>
                      <td><strong>{ev.eventType}</strong></td>
                      <td>{new Date(ev.recordedAt).toLocaleString()}</td>
                      <td>{ev.actorId ? `${ev.actorId.slice(0, 8)}…` : 'System/Worker'}</td>
                      <td><pre style={{ margin: 0, fontSize: '11px' }}>{JSON.stringify(ev.payload)}</pre></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Evidence Payloads */}
          <h4 style={{ marginTop: '20px', marginBottom: '8px' }}>Evidence Records ({evidence.length})</h4>
          {!evidence.length ? (
            <p style={{ fontSize: '13px', color: '#64748b' }}>No evidence payloads stored.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Evidence ID</th>
                    <th>Version</th>
                    <th>Recorded at</th>
                    <th>Payload snapshot</th>
                  </tr>
                </thead>
                <tbody>
                  {evidence.map(ev => (
                    <tr key={ev.evidenceId}>
                      <td>#{ev.evidenceId}</td>
                      <td>v{ev.incidentVersion}</td>
                      <td>{new Date(ev.recordedAt).toLocaleString()}</td>
                      <td><pre style={{ margin: 0, fontSize: '11px', maxHeight: '100px', overflowY: 'auto' }}>{JSON.stringify(ev.payload, null, 2)}</pre></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modal / Form to create task from incident */}
      {taskModalOpen && selectedIncident && (
        <div className="panel" style={{ border: '2px solid #0e7490', background: '#f0fdf4', marginTop: '20px' }}>
          <h3>Create Genuine Maintenance Task from Incident</h3>
          <p>
            This links an authoritative maintenance task directly to incident <code>{selectedIncident.id}</code> with immutable foreign key integrity.
          </p>
          <form onSubmit={submitCreateTask}>
            <label>
              Task Action Title
              <input
                required
                maxLength={1000}
                value={taskTitle}
                onChange={e => setTaskTitle(e.target.value)}
                disabled={busy}
              />
            </label>
            <label>
              Assigned Person (optional)
              <input
                maxLength={100}
                value={taskOwner}
                onChange={e => setTaskOwner(e.target.value)}
                disabled={busy}
              />
            </label>
            <label>
              Incident Alert Summary
              <textarea
                required
                maxLength={500}
                value={taskSummary}
                onChange={e => setTaskSummary(e.target.value)}
                disabled={busy}
              />
            </label>
            <div className="actions">
              <button disabled={busy || !taskTitle.trim() || !taskSummary.trim()} type="submit">
                {busy ? 'Saving task…' : 'Create incident task'}
              </button>
              <button disabled={busy} type="button" onClick={() => setTaskModalOpen(false)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}
