import { useMemo, useState } from 'react';
import { createMaintenanceClient } from '../../../integration/frontend/maintenanceClient.mjs';

const terminal = status => ['Completed', 'Cancelled'].includes(status);
const sampleId = () => `sample-ui-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;

function TaskEditor({ task, client, actor, onRefresh, onHistory }) {
  const [owner, setOwner] = useState(task.owner);
  const [status, setStatus] = useState(task.status);
  const [notes, setNotes] = useState(task.notes);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(null);
  const readOnly = terminal(task.status);
  async function save(event) {
    event.preventDefault();
    if (busy || readOnly || conflict) return;
    setBusy(true); setError('');
    try {
      const updated = await client.update(task, { owner: owner.trim() || null, status, notes }, actor.trim());
      onRefresh(updated); setOwner(updated.owner); setStatus(updated.status); setNotes(updated.notes);
    } catch (failure) {
      if (failure.status === 409) {
        setConflict({ latest: null });
        try {
          const latest = await client.task(task.id);
          onRefresh(latest); setConflict({ latest });
          setError(`${failure.message}. Latest task loaded; your draft is retained. Review it before another save.`);
        } catch (reloadFailure) {
          setError(`Conflict detected, but refresh failed: ${reloadFailure.message}. Saving is blocked; reload tasks before reviewing.`);
        }
      } else setError(failure.message);
    } finally { setBusy(false); }
  }
  const choices = task.status === 'Open' ? ['Open', 'In progress', 'Cancelled']
    : task.status === 'In progress' ? ['In progress', 'Completed', 'Cancelled'] : [task.status];
  return <article className="task" data-task-id={task.id}>
    <h3>{task.title}</h3>
    <p>Task ID: {task.id}</p>
    <p>Saved: {task.status} · Owner: {task.owner || 'Unassigned'} · Version: {task.version}</p>
    <p>Saved notes: {task.notes || 'None'}</p>
    <p>Sample alert: {task.alertId} · {task.evidence}</p>
    {error && <p role="alert" className="error">{error}</p>}
    {conflict && <div className="banner">
      <p>Review your retained draft: owner {owner || 'Unassigned'}, status {status}, notes {notes || 'None'}.</p>
      {conflict.latest && !terminal(conflict.latest.status) && <button type="button" onClick={() => setConflict(null)}>I reviewed the latest task; enable saving my draft</button>}
      {readOnly && <p>The latest task is terminal. Your draft cannot be submitted.</p>}
    </div>}
    {readOnly && <p>This completed/cancelled task is read-only.</p>}
    <form onSubmit={save}>
      <label>Assigned person<input maxLength={100} value={owner} disabled={busy || readOnly} onChange={event => setOwner(event.target.value)} /></label>
      <label>Status<select aria-label="Task status" value={status} disabled={busy || readOnly} onChange={event => setStatus(event.target.value)}>
        {!choices.includes(status) && <option disabled>{status}</option>}
        {choices.map(value => <option key={value}>{value}</option>)}
      </select></label>
      <label>Progress or completion notes / cancellation reason<textarea aria-label="Task notes" maxLength={2000} value={notes} disabled={busy || readOnly} onChange={event => setNotes(event.target.value)} /></label>
      <button type="submit" disabled={busy || readOnly || !!conflict || !actor.trim()}>{busy ? 'Saving…' : 'Save task update'}</button>
    </form>
    <button type="button" onClick={() => onHistory(task.id)}>View history</button>
  </article>;
}

export default function BackendMaintenance() {
  const client = useMemo(() => createMaintenanceClient({ baseUrl: import.meta.env.VITE_API_BASE_URL }), []);
  const [assets, setAssets] = useState({ items: [], limit: 20, offset: 0 });
  const [assetId, setAssetId] = useState('');
  const [page, setPage] = useState({ items: [], limit: 20, offset: 0 });
  const [actor, setActor] = useState('Person C demo operator');
  const [title, setTitle] = useState('Sample cooling inspection');
  const [owner, setOwner] = useState('');
  const [summary, setSummary] = useState('Sample alert for maintenance integration; not a detector result.');
  const [alertId, setAlertId] = useState(sampleId);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [history, setHistory] = useState(null);
  async function perform(action) {
    if (busy) return;
    setBusy(true); setError(''); setNotice('');
    try { await action(); } catch (failure) { setError(failure.message); } finally { setBusy(false); }
  }
  function loadTasks(offset = 0) {
    return perform(async () => { setPage(await client.tasks(assetId, offset)); setHistory(null); });
  }
  function viewHistory(id, offset = 0) {
    return perform(async () => { const result = await client.history(id, offset); setHistory({ ...result, taskId: id }); });
  }
  async function create(event) {
    event.preventDefault();
    await perform(async () => {
      const saved = await client.create({ title, owner: owner.trim() || null, assetId, alertId, evidence: summary });
      setNotice(`Created backend task ${saved.id}.`); setAlertId(sampleId());
      setPage(await client.tasks(assetId));
    });
  }
  function refreshed(updated) {
    setPage(current => ({ ...current, items: current.items.map(task => task.id === updated.id ? updated : task) }));
    setHistory(null);
  }
  return <section className="panel">
    <h2>Backend maintenance</h2>
    <div className="banner">SAMPLE ALERTS ONLY. Tasks/history are stored in the backend PostgreSQL database. Actor and assignment names are demo display labels, not authenticated identities. Completing a task does not recover or acknowledge an alert.</div>
    <label>Demo actor<input maxLength={100} value={actor} onChange={event => setActor(event.target.value)} /></label>
    {error && <p role="alert" className="error">{error}</p>}
    {notice && <p role="status" className="success">{notice}</p>}
    {busy && <p role="status">Loading maintenance data…</p>}
    <button disabled={busy} onClick={() => perform(async () => setAssets(await client.assets()))}>Load registered assets</button>
    <div className="actions">
      <button disabled={busy || assets.offset === 0} onClick={() => perform(async () => setAssets(await client.assets(assets.offset - 20)))}>Previous asset page</button>
      <button disabled={busy || assets.items.length < 20} onClick={() => perform(async () => setAssets(await client.assets(assets.offset + 20)))}>Next asset page</button>
    </div>
    <label>Maintenance asset<select aria-label="Maintenance asset" value={assetId} disabled={busy} onChange={event => { setAssetId(event.target.value); setPage({ items: [], limit: 20, offset: 0 }); setHistory(null); }}>
      <option value="">Select a registered asset</option>
      {assetId && !assets.items.some(asset => asset.asset_id === assetId) && <option>{assetId}</option>}
      {assets.items.map(asset => <option key={asset.asset_id} value={asset.asset_id}>{asset.asset_id} — {asset.name}</option>)}
    </select></label>
    <button disabled={busy || !assetId} onClick={() => loadTasks()}>Load backend tasks</button>
    <h3>Create a sample-alert task</h3>
    <p>Sample alert ID: {alertId}</p>
    <form onSubmit={create}>
      <label>Sample task action<input required maxLength={1000} value={title} onChange={event => setTitle(event.target.value)} /></label>
      <label>Sample alert summary<textarea required maxLength={500} value={summary} onChange={event => setSummary(event.target.value)} /></label>
      <label>Initial assigned person<input maxLength={100} value={owner} onChange={event => setOwner(event.target.value)} /></label>
      <button disabled={busy || !assetId || !title.trim() || !summary.trim()} type="submit">Create backend task</button>
    </form>
    <h3>Backend tasks — page {Math.floor(page.offset / page.limit) + 1}</h3>
    {!page.items.length && <p>No tasks loaded on this page. Select an asset and load its tasks.</p>}
    {page.items.map(task => <TaskEditor key={task.id} task={task} client={client} actor={actor} onRefresh={refreshed} onHistory={viewHistory} />)}
    <div className="actions">
      <button disabled={busy || !assetId || page.offset === 0} onClick={() => loadTasks(page.offset - page.limit)}>Previous task page</button>
      <button disabled={busy || !assetId || page.items.length < page.limit} onClick={() => loadTasks(page.offset + page.limit)}>Next task page</button>
    </div>
    {history && <section className="panel">
      <h3>History for {history.taskId}</h3>
      <p>History page {Math.floor(history.offset / history.limit) + 1}</p>
      {history.items.map(row => <article key={row.id}>
        <p>Version {row.version}: {row.previous_status ?? 'Creation/import'} → {row.new_status}</p>
        <p>Owner: {row.previous_owner ?? 'Unassigned'} → {row.new_owner ?? 'Unassigned'}</p>
        <p>Notes: {row.notes || 'None'}</p>
        <p>{row.created_at} · Actor: {row.actor ?? 'Not recorded'} · {row.identity_source}</p>
      </article>)}
      <button disabled={busy || history.offset === 0} onClick={() => viewHistory(history.taskId, history.offset - history.limit)}>Previous history page</button>
      <button disabled={busy || history.items.length < history.limit} onClick={() => viewHistory(history.taskId, history.offset + history.limit)}>Next history page</button>
    </section>}
  </section>;
}
