// Small reusable bridge for C's current UI fields. Import into C's service layer.
// Only explicitly declared sample alerts are accepted; this is not a detector adapter.
const toApiStatus = { Open: 'open', 'In progress': 'in_progress', Completed: 'completed', Cancelled: 'cancelled' };
const toUiStatus = Object.fromEntries(Object.entries(toApiStatus).map(([ui, api]) => [api, ui]));

export function toCreateRequest(task, { sampleMode = false } = {}) {
  if (!sampleMode) throw new Error('Genuine alerts need an agreed persisted alert contract.');
  if (!task.alertId) throw new Error('This milestone requires a linked sample alert.');
  const alertId = task.alertId.startsWith('sample-') ? task.alertId : `sample-${task.alertId}`;
  return {
    alert: { source: 'sample', alert_id: alertId, asset_id: task.assetId, summary: task.evidence },
    action: task.title,
    ...(task.owner == null ? {} : { owner: task.owner }),
  };
}

export function toFrontendTask(task) {
  if (!toUiStatus[task.status]) throw new Error(`Unsupported task status: ${task.status}`);
  return {
    id: task.id, title: task.action, owner: task.owner ?? '', assetId: task.asset_id,
    alertId: task.alert.alert_id, evidence: task.alert.summary, recommendation: task.action,
    status: toUiStatus[task.status], notes: task.notes, createdAt: task.created_at,
    updatedAt: task.updated_at, version: task.version, alertSource: task.alert.source,
  };
}

export function toFrontendPage(page) {
  return { ...page, items: page.items.map(toFrontendTask) };
}

export function toUpdateRequest(changes, expectedVersion) {
  const result = { expected_version: expectedVersion };
  for (const key of Object.keys(changes)) {
    if (!['status', 'owner', 'notes'].includes(key)) throw new Error(`Unsupported task update: ${key}`);
    if (key === 'status') {
      if (!toApiStatus[changes.status]) throw new Error(`Unsupported status: ${changes.status}`);
      result.status = toApiStatus[changes.status];
    } else result[key] = changes[key];
  }
  return result;
}
