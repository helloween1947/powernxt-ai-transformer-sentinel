export const statusLabels = { open: 'Open', in_progress: 'In progress', completed: 'Completed', cancelled: 'Cancelled' };
const transitions = { open: ['open', 'in_progress', 'cancelled'], in_progress: ['in_progress', 'completed', 'cancelled'], completed: [], cancelled: [] };

export const isTerminal = status => status === 'completed' || status === 'cancelled';
export const allowedStatuses = status => transitions[status] ?? [];

function text(value, label, maximum, required = true) {
  if (typeof value !== 'string' || (required && !value.trim()) || value.trim().length > maximum) {
    throw new Error(`${label} ${required ? 'is required and ' : ''}must be at most ${maximum} characters.`);
  }
  return value.trim();
}

export function validateActor(actor) {
  const result = text(actor, 'Demo actor', 100);
  if ([...actor].some(character => character.codePointAt(0) < 32 || character.codePointAt(0) === 127)) throw new Error('Demo actor cannot contain control characters.');
  return result;
}

export function createRequest({ assetId, alertId, summary, title, owner = '', sampleMode }) {
  if (sampleMode !== true) throw new Error('Only explicitly labeled sample alerts are supported.');
  const asset = text(assetId, 'Registered asset', 100);
  const alert = text(alertId, 'Sample alert ID', 100);
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(asset) || !/^sample-[A-Za-z0-9._-]+$/.test(alert)) {
    throw new Error('Use a registered asset ID and an alert ID beginning with sample-.');
  }
  return {
    alert: { source: 'sample', alert_id: alert, asset_id: asset, summary: text(summary, 'Sample alert summary', 500) },
    action: text(title, 'Task action', 1000),
    owner: text(owner, 'Assigned person', 100, false) || null,
  };
}

export function createAnalyticsRequest({ assetId, incidentId, title, owner = '' }) {
  const asset = text(assetId, 'Registered asset', 100);
  const incident = text(incidentId, 'Incident ID', 100);
  return {
    alert: { source: 'analytics', incident_id: incident, asset_id: asset },
    action: text(title, 'Task action', 1000),
    owner: text(owner, 'Assigned person', 100, false) || null,
  };
}

export function adaptTask(task) {
  if (!statusLabels[task.status] || !Number.isInteger(task.version) || task.version < 1) {
    throw new Error('Backend returned an unsupported task status or version.');
  }
  return {
    id: task.id, assetId: task.asset_id, title: task.action, owner: task.owner ?? '',
    status: task.status, notes: task.notes ?? '', version: task.version,
    alert: task.alert, incidentId: task.incident_id ?? null,
    createdAt: task.created_at, updatedAt: task.updated_at,
  };
}

export function updateRequest(task, { owner, status, notes }) {
  if (!Number.isInteger(task.version) || task.version < 1) throw new Error('Reload the task to obtain its saved version.');
  if (isTerminal(task.status)) throw new Error('Completed and cancelled tasks are read-only.');
  if (!allowedStatuses(task.status).includes(status)) throw new Error('This status transition is not allowed.');
  const assigned = text(owner, 'Assigned person', 100, false) || null;
  const note = text(notes, 'Notes', 2000, false);
  if (status === 'in_progress' && !assigned) throw new Error('Assign an owner before starting; in-progress tasks cannot be unassigned.');
  if ((status === 'completed' || status === 'cancelled') && !note) throw new Error('Completion or cancellation requires nonblank notes in this update.');
  if (status === 'completed' && !assigned) throw new Error('Completed tasks must retain their assigned owner.');
  if (status === task.status && assigned === (task.owner || null) && note === task.notes) throw new Error('Change the owner, status or notes before saving.');
  return { expected_version: task.version, owner: assigned, status, notes: note };
}

export function pageParameters(limit = 20, offset = 0) {
  if (!Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0) {
    throw new Error('Page limit must be 1–100 and offset must be a nonnegative integer.');
  }
  return { limit, offset };
}
