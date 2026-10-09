import { toCreateRequest, toFrontendTask, toFrontendPage, toUpdateRequest } from './maintenanceAdapter.mjs';

export class MaintenanceApiError extends Error {
  constructor(status, message) { super(message); this.name = 'MaintenanceApiError'; this.status = status; }
}

export function createMaintenanceClient({ baseUrl, fetchImpl = globalThis.fetch }) {
  const base = (baseUrl ?? '').trim().replace(/\/+$/, '');
  const root = '/api/v1/maintenance/tasks';
  async function request(path, { method = 'GET', body, actor } = {}) {
    if (!base) throw new Error('Set VITE_API_BASE_URL to a reachable backend before loading maintenance.');
    const response = await fetchImpl(`${base}${path}`, {
      method, headers: { ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(actor === undefined ? {} : { 'X-Demo-Actor': actor }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: AbortSignal.timeout(10000),
    });
    let result;
    try { result = await response.json(); } catch { throw new MaintenanceApiError(response.status, 'Backend returned an unreadable response.'); }
    if (!response.ok) {
      const detail = result.detail;
      const message = typeof detail === 'string' ? detail : Array.isArray(detail)
        ? detail.map(item => `${item.loc?.join('.') ?? 'request'}: ${item.msg}`).join('; ')
        : `Maintenance request failed (${response.status}).`;
      throw new MaintenanceApiError(response.status, message);
    }
    return result;
  }
  return {
    assets: (offset = 0) => request(`/api/v1/assets?limit=20&offset=${offset}`),
    tasks: (assetId, offset = 0) => request(`${root}?asset_id=${encodeURIComponent(assetId)}&limit=20&offset=${offset}`).then(toFrontendPage),
    task: id => request(`${root}/${encodeURIComponent(id)}`).then(toFrontendTask),
    create: ui => request(root, { method: 'POST', body: toCreateRequest(ui, { sampleMode: true }) }).then(toFrontendTask),
    update: (task, changes, actor) => request(`${root}/${encodeURIComponent(task.id)}`, {
      method: 'PATCH', body: toUpdateRequest(changes, task.version), actor,
    }).then(toFrontendTask),
    history: (id, offset = 0) => request(`${root}/${encodeURIComponent(id)}/history?limit=20&offset=${offset}`),
  };
}
