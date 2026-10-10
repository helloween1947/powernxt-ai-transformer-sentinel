import { useEffect, useMemo, useRef, useState } from 'react';
import { createMaintenanceClient } from '../services/maintenanceApi.js';
import { allowedStatuses, isTerminal, statusLabels } from '../services/maintenanceAdapter.js';

const emptyPage = () => ({ items: [], limit: 20, offset: 0 });
const sampleId = () => `sample-c-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
const draftFor = task => ({ owner: task.owner, status: task.status, notes: task.notes });

function Pager({ page, busy, onPage, label }) {
  return (
    <div className="actions" aria-label={`${label} pagination`}>
      <button disabled={busy || page.offset === 0} onClick={() => onPage(page.offset - page.limit)}>
        Previous {label} page
      </button>
      <button disabled={busy || page.items.length < page.limit} onClick={() => onPage(page.offset + page.limit)}>
        Next {label} page
      </button>
      <span>Page {Math.floor(page.offset / page.limit) + 1} · {page.items.length} item(s)</span>
    </div>
  );
}

function TaskEditor({ task, client, actor, token, canWrite = true, onHistory, onRefresh }) {
  const [saved, setSaved] = useState(task);
  const [draft, setDraft] = useState(() => draftFor(task));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [conflict, setConflict] = useState(null);
  const lock = useRef(false);
  const readOnly = isTerminal(saved.status) || !canWrite;
  const isAnalytics = saved.incidentId != null || saved.alert?.source === 'analytics';

  async function retrieveConflict() {
    try {
      const latest = await client.task(saved.id, token);
      setSaved(latest);
      onRefresh(latest);
      setConflict({ latest });
      setError('The backend rejected this update (409). Latest task loaded. Your draft is retained; review it before submitting again.');
    } catch (failure) {
      setError(`Update conflict. Latest task could not be loaded: ${failure.message}. Your draft is retained and saving is blocked.`);
    }
  }

  async function save(event) {
    event.preventDefault();
    if (lock.current || readOnly || conflict) return;
    lock.current = true;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const updated = await client.update(saved, draft, isAnalytics ? null : actor, isAnalytics ? token : null);
      setSaved(updated);
      setDraft(draftFor(updated));
      onRefresh(updated);
      setNotice(`Saved backend version ${updated.version}.`);
    } catch (failure) {
      if (failure.status === 409) {
        setConflict({ latest: null });
        await retrieveConflict();
      } else {
        setError(failure.message);
      }
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  function edit(key, value) {
    setDraft(current => ({ ...current, [key]: value }));
  }

  const choices = allowedStatuses(saved.status);
  const canSubmit = isAnalytics ? !!token : !!actor.trim();

  return (
    <article className="task" data-task-id={saved.id} style={{ borderLeft: isAnalytics ? '4px solid #0e7490' : undefined }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
        <h3>{saved.title}</h3>
        <span className="badge" style={{ background: isAnalytics ? '#e0f2fe' : '#fef3c7', color: isAnalytics ? '#0369a1' : '#92400e' }}>
          {isAnalytics ? 'Analytics Incident Task' : 'Sample Task'}
        </span>
      </div>
      <p>Task ID: {saved.id} · Asset: {saved.assetId}</p>
      <p>Saved: {statusLabels[saved.status]} · Owner: {saved.owner || 'Unassigned'} · Version: {saved.version}</p>
      <p>Saved notes: {saved.notes || 'None'}</p>
      {isAnalytics ? (
        <p>Linked Incident: <code>{saved.incidentId || saved.alert?.alert_id}</code> · {saved.alert?.summary}</p>
      ) : (
        <p>Sample alert: {saved.alert?.alert_id} · {saved.alert?.summary}</p>
      )}
      <p>Created: {saved.createdAt} · Updated: {saved.updatedAt}</p>
      {error && <p role="alert" className="error">{error}</p>}
      {notice && <p role="status" className="success">{notice}</p>}
      {conflict && (
        <div className="banner">
          <p>Retained draft: owner {draft.owner || 'Unassigned'}, status {statusLabels[draft.status]}, notes {draft.notes || 'None'}.</p>
          {conflict.latest ? (
            <>
              <p>Compare the saved fields above with your draft below. Saving submits the draft owner, status and notes together.</p>
              {!readOnly && (
                <button type="button" onClick={() => { setConflict(null); setError(''); }}>
                  I reviewed the latest task; enable saving my draft
                </button>
              )}
              <button type="button" onClick={() => { setDraft(draftFor(saved)); setConflict(null); setError(''); }}>
                Discard my draft and use the latest task
              </button>
            </>
          ) : (
            <button disabled={busy} type="button" onClick={async () => { setBusy(true); await retrieveConflict(); setBusy(false); }}>
              Retrieve latest task for review
            </button>
          )}
        </div>
      )}
      {readOnly && <p>{isTerminal(saved.status) ? 'This completed/cancelled task is read-only.' : 'Reader role: this task is read-only.'}</p>}
      <form onSubmit={save}>
        <label>
          Assigned person
          <input
            maxLength={100}
            value={draft.owner}
            disabled={busy || readOnly}
            onChange={event => edit('owner', event.target.value)}
          />
        </label>
        <label>
          Status
          <select
            aria-label="Task status"
            value={draft.status}
            disabled={busy || readOnly}
            onChange={event => edit('status', event.target.value)}
          >
            {!choices.includes(draft.status) && (
              <option value={draft.status} disabled>{statusLabels[draft.status]}</option>
            )}
            {choices.map(status => (
              <option key={status} value={status}>{statusLabels[status]}</option>
            ))}
          </select>
        </label>
        <label>
          Progress or completion notes / cancellation reason
          <textarea
            aria-label="Task notes"
            maxLength={2000}
            value={draft.notes}
            disabled={busy || readOnly}
            onChange={event => edit('notes', event.target.value)}
          />
        </label>
        <button disabled={busy || readOnly || !!conflict || !canSubmit} type="submit">
          {busy ? 'Saving…' : 'Save task update'}
        </button>
      </form>
      <button disabled={busy} type="button" onClick={() => onHistory(saved.id)}>
        View history
      </button>
    </article>
  );
}

export default function BackendMaintenance({ focusedContext = false, operator, initialTaskId = null, baseUrl = import.meta.env.VITE_API_BASE_URL, selectedAssetId = '' }) {
  const client = useMemo(() => createMaintenanceClient({ baseUrl }), [baseUrl]);
  const [mode, setMode] = useState(() => initialTaskId || focusedContext ? 'analytics' : 'sample');
  const [assets, setAssets] = useState(emptyPage);
  const [assetsLoaded, setAssetsLoaded] = useState(false);
  const [assetId, setAssetId] = useState(selectedAssetId);
  const [page, setPage] = useState(emptyPage);
  const [tasksLoaded, setTasksLoaded] = useState(false);
  const [createdTask, setCreatedTask] = useState(null);

  // Sample mode fields
  const [actor, setActor] = useState('Person C demo operator');
  const [title, setTitle] = useState('Sample cooling inspection');
  const [owner, setOwner] = useState('');
  const [summary, setSummary] = useState('Sample alert for integration testing; not a detector result.');
  const [alertId, setAlertId] = useState(sampleId);

  // Analytics mode fields
  const [analyticsIncidentId, setAnalyticsIncidentId] = useState('');
  const [analyticsTitle, setAnalyticsTitle] = useState('Inspect high top-oil temperature anomaly');
  const [analyticsOwner, setAnalyticsOwner] = useState('');
  const [analyticsSummary, setAnalyticsSummary] = useState('Genuine detector incident response task.');

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [history, setHistory] = useState(null);
  const [epoch, setEpoch] = useState(0);
  const lock = useRef(false);
  useEffect(() => {
    let cancelled = false;
    if (initialTaskId && operator?.token) client.task(initialTaskId, operator.token).then(task => {
      if (!cancelled) setCreatedTask(task);
    }).catch(error => {
      if (!cancelled) setError(`Linked task could not be loaded: ${error.message}`);
    });
    return () => { cancelled = true; client.cancelAll(); };
  }, [client, initialTaskId, operator?.token]);

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

  function loadAssets(offset = 0) {
    return perform(async () => {
      setAssets(await client.assets(offset));
      setAssetsLoaded(true);
    });
  }

  function loadTasks(offset = 0) {
    return perform(async () => {
      const isAnalytics = mode === 'analytics';
      if (isAnalytics && !operator?.token) {
        throw new Error('Operator authentication token is required to load analytics tasks.');
      }
      setPage(await client.tasks(assetId, offset, mode, isAnalytics ? operator?.token : null));
      setTasksLoaded(true);
      setCreatedTask(null);
      setHistory(null);
      setEpoch(value => value + 1);
    });
  }

  function viewHistory(id, offset = 0) {
    return perform(async () => {
      const isAnalytics = mode === 'analytics';
      const historyPage = await client.history(id, offset, isAnalytics ? operator?.token : null);
      setHistory({ ...historyPage, taskId: id });
    });
  }

  async function createSample(event) {
    event.preventDefault();
    await perform(async () => {
      const saved = await client.create({ title, owner, assetId, alertId, summary, sampleMode: true });
      setCreatedTask(saved);
      setNotice(`Backend sample task saved: ${saved.id}.`);
      setAlertId(sampleId());
      setPage(emptyPage());
      setTasksLoaded(false);
      setHistory(null);
      setPage(await client.tasks(assetId, 0, 'sample'));
      setTasksLoaded(true);
      setEpoch(value => value + 1);
    });
  }

  async function createAnalytics(event) {
    event.preventDefault();
    if (!operator?.token) {
      setError('Operator authentication token is required.');
      return;
    }
    await perform(async () => {
      const saved = await client.create({
        title: analyticsTitle,
        owner: analyticsOwner,
        assetId,
        incidentId: analyticsIncidentId.trim(),
        summary: analyticsSummary,
        sampleMode: false,
      }, operator.token);

      setCreatedTask(saved);
      setNotice(`Genuine backend task saved: ${saved.id}.`);
      setPage(emptyPage());
      setTasksLoaded(false);
      setHistory(null);
      setPage(await client.tasks(assetId, 0, 'analytics', operator.token));
      setTasksLoaded(true);
      setEpoch(value => value + 1);
    });
  }

  function refreshed(updated) {
    setPage(current => ({ ...current, items: current.items.map(task => task.id === updated.id ? updated : task) }));
    setCreatedTask(current => current?.id === updated.id ? updated : current);
    setHistory(null);
  }

  return (
    <section className="panel backend-workflow">
      <h2>Backend maintenance</h2>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
        <button
          type="button"
          onClick={() => { setMode('sample'); setTasksLoaded(false); setPage(emptyPage()); setCreatedTask(null); setHistory(null); setError(''); setNotice(''); }}
          style={{
            background: mode === 'sample' ? '#102b3c' : '#fff',
            color: mode === 'sample' ? '#fff' : '#153c50',
            fontWeight: mode === 'sample' ? 600 : 400,
          }}
        >
          Sample Alerts Mode
        </button>
        <button
          type="button"
          onClick={() => { setMode('analytics'); setTasksLoaded(false); setPage(emptyPage()); setCreatedTask(null); setHistory(null); setError(''); setNotice(''); }}
          style={{
            background: mode === 'analytics' ? '#0e7490' : '#fff',
            color: mode === 'analytics' ? '#fff' : '#153c50',
            fontWeight: mode === 'analytics' ? 600 : 400,
          }}
        >
          Genuine Incident Tasks Mode
        </button>
      </div>

      {mode === 'sample' ? (
        <div className="banner">
          SAMPLE ALERTS ONLY. This screen calls the backend task API. Actor and assignment names are demo display labels, not authentication. Completing a task does not recover or acknowledge an alert.
        </div>
      ) : (
        <div className="banner" style={{ background: '#f0fdf4', borderColor: '#86efac' }}>
          GENUINE INCIDENT MAINTENANCE. Tasks created here link directly to persisted incident records via foreign keys. Updating or viewing analytics tasks requires valid Operator Bearer authentication.
        </div>
      )}

      {mode === 'sample' && (
        <label>
          Demo actor
          <input maxLength={100} value={actor} onChange={event => setActor(event.target.value)} />
        </label>
      )}

      {mode === 'analytics' && !operator && (
        <p role="alert" className="error">
          Please authenticate in the Operator bar above to view or manage genuine incident maintenance tasks.
        </p>
      )}

      {error && <p role="alert" className="error">{error}</p>}
      {notice && <p role="status" className="success">{notice}</p>}
      {busy && <p role="status">Loading maintenance data…</p>}

      <button disabled={busy} onClick={() => loadAssets()} hidden={focusedContext}>
        {assetsLoaded ? 'Refresh registered assets' : 'Load registered assets'}
      </button>

      {assetsLoaded && (
        <>
          <Pager page={assets} busy={busy} onPage={loadAssets} label="asset" />
          {!assets.items.length && <p>No registered assets on this page.</p>}
        </>
      )}

      <label>
        Maintenance asset
        <select
          aria-label="Maintenance asset"
          value={assetId}
          disabled={busy || focusedContext}
          onChange={event => {
            setAssetId(event.target.value);
            setPage(emptyPage());
            setTasksLoaded(false);
            setCreatedTask(null);
            setHistory(null);
            setError('');
            setNotice('');
          }}
        >
          <option value="">Select a registered asset</option>
          {assetId && !assets.items.some(asset => asset.asset_id === assetId) && <option value={assetId}>{assetId}</option>}
          {assets.items.map(asset => (
            <option key={asset.asset_id} value={asset.asset_id}>
              {asset.asset_id} — {asset.name}
            </option>
          ))}
        </select>
      </label>

      <p>Reloading or changing task pages discards unsaved drafts on this screen.</p>
      <button
        disabled={busy || !assetId || (mode === 'analytics' && !operator)}
        onClick={() => loadTasks()}
      >
        Load / refresh {mode === 'analytics' ? 'incident-linked' : 'sample'} tasks
      </button>

      {mode === 'sample' ? (
        <>
          <h3>Create a sample-alert task</h3>
          <p>Sample alert ID: {alertId}</p>
          <form onSubmit={createSample}>
            <label>Sample task action<input required maxLength={1000} value={title} disabled={busy} onChange={event => setTitle(event.target.value)} /></label>
            <label>Sample alert summary<textarea required maxLength={500} value={summary} disabled={busy} onChange={event => setSummary(event.target.value)} /></label>
            <label>Initial assigned person<input maxLength={100} value={owner} disabled={busy} onChange={event => setOwner(event.target.value)} /></label>
            <button disabled={busy || !assetId || !title.trim() || !summary.trim()} type="submit">Create sample backend task</button>
          </form>
        </>
      ) : (
        <>
          <h3>Create an incident-linked maintenance task</h3>
          <form onSubmit={createAnalytics}>
            <label>
              Linked Incident ID (UUID)
              <input
                required
                maxLength={100}
                placeholder="e.g. c1a2b3c4-1111-2222-3333-444455556666"
                value={analyticsIncidentId}
                disabled={busy}
                onChange={event => setAnalyticsIncidentId(event.target.value)}
              />
            </label>
            <label>Task action<input required maxLength={1000} value={analyticsTitle} disabled={busy} onChange={event => setAnalyticsTitle(event.target.value)} /></label>
            <label>Incident summary<textarea required maxLength={500} value={analyticsSummary} disabled={busy} onChange={event => setAnalyticsSummary(event.target.value)} /></label>
            <label>Initial assigned person<input maxLength={100} value={analyticsOwner} disabled={busy} onChange={event => setAnalyticsOwner(event.target.value)} /></label>
            <button disabled={busy || !['operator', 'admin'].includes(operator?.role) || !assetId || !analyticsIncidentId.trim() || !analyticsTitle.trim()} type="submit">
              Create genuine incident task
            </button>
          </form>
        </>
      )}

      <h3>{mode === 'analytics' ? 'Incident-Linked Tasks' : 'Sample Tasks'}</h3>
      {createdTask && !page.items.some(task => task.id === createdTask.id) && (
        <>
          <p>Recently created task — shown separately because it is outside this oldest-first page.</p>
          <TaskEditor
            key={`created:${createdTask.id}`}
            task={createdTask}
            client={client}
            actor={actor}
            token={operator?.token}
            canWrite={createdTask.alert?.source !== 'analytics' || ['operator', 'admin'].includes(operator?.role)}
            onRefresh={refreshed}
            onHistory={viewHistory}
          />
        </>
      )}

      {!tasksLoaded && <p>Select an asset and load its tasks.</p>}
      {tasksLoaded && !page.items.length && <p>No {mode === 'analytics' ? 'incident-linked' : 'sample'} tasks on this page.</p>}
      {page.items.map(task => (
        <TaskEditor
          key={`${task.id}:${epoch}`}
          task={task}
          client={client}
          actor={actor}
          token={operator?.token}
          canWrite={task.alert?.source !== 'analytics' || ['operator', 'admin'].includes(operator?.role)}
          onRefresh={refreshed}
          onHistory={viewHistory}
        />
      ))}
      {tasksLoaded && <Pager page={page} busy={busy} onPage={loadTasks} label="task" />}

      {history && (
        <section className="panel" style={{ marginTop: '20px' }}>
          <h3>History for {history.taskId}</h3>
          {!history.items.length && <p>No history entries on this page.</p>}
          {history.items.map(row => (
            <article key={row.id}>
              <p>Version {row.version}: {statusLabels[row.previous_status] ?? 'Creation/import'} → {statusLabels[row.new_status] ?? row.new_status}</p>
              <p>Owner: {row.previous_owner ?? 'Unassigned'} → {row.new_owner ?? 'Unassigned'}</p>
              <p>Previous notes: {row.previous_notes ?? 'None'} · Notes: {row.notes || 'None'}</p>
              <p>{row.created_at} · Actor: {row.actor ?? 'Not recorded'} · Identity source: {row.identity_source}</p>
            </article>
          ))}
          <Pager page={history} busy={busy} onPage={offset => viewHistory(history.taskId, offset)} label="history" />
        </section>
      )}
    </section>
  );
}
