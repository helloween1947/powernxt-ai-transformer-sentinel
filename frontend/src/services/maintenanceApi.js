import { adaptTask, createRequest, updateRequest, validateActor, pageParameters } from './maintenanceAdapter.js';

export class MaintenanceApiError extends Error {
  constructor(status, message) { super(message); this.name = 'MaintenanceApiError'; this.status = status; }
}

export function createMaintenanceClient({ baseUrl, fetchImpl = globalThis.fetch }) {
  const base = (baseUrl ?? '').trim().replace(/\/+$/, '');
  const root = '/api/v1/maintenance/tasks';
  const activeRequests = new Set();
  async function request(path, { parameters = {}, method = 'GET', body, actor } = {}) {
    if (!base) throw new Error('Set VITE_API_BASE_URL to a reachable backend and restart Vite.');
    const url = new URL(`${base}${path}`);
    for (const [key, value] of Object.entries(parameters)) if (value !== '' && value != null) url.searchParams.set(key, value);
    let response;
    const controller = new AbortController();
    activeRequests.add(controller);
    try {
      try {
        response = await fetchImpl(url, {
          method,
          headers: { ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...(actor === undefined ? {} : { 'X-Demo-Actor': actor }) },
          ...(body === undefined ? {} : { body: JSON.stringify(body) }),
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        });
      } catch {
        throw new Error('Cannot reach the maintenance backend. Check its address, server, network and browser CORS errors.');
      }
      let result;
      try { result = await response.json(); } catch {
        throw new MaintenanceApiError(response.status, 'Backend returned an unreadable response; verify its API address.');
      }
      if (!response.ok) {
        const detail = result.detail;
        const message = typeof detail === 'string' ? detail : Array.isArray(detail)
          ? detail.map(item => `${item.loc?.join('.') ?? 'request'}: ${item.msg}`).join('; ')
          : `Maintenance request failed (${response.status}).`;
        throw new MaintenanceApiError(response.status, message);
      }
      return result;
    } finally { activeRequests.delete(controller); }
  }
  return {
    cancelAll: () => { activeRequests.forEach(controller => controller.abort()); activeRequests.clear(); },
    assets: (offset = 0) => request('/api/v1/assets', { parameters: pageParameters(20, offset) }),
    tasks: async (assetId = '', offset = 0) => {
      const page = await request(root, { parameters: { ...pageParameters(20, offset), asset_id: assetId } });
      return { ...page, items: page.items.map(adaptTask) };
    },
    task: async id => adaptTask(await request(`${root}/${encodeURIComponent(id)}`)),
    create: async draft => adaptTask(await request(root, { method: 'POST', body: createRequest(draft) })),
    update: async (task, draft, actor) => adaptTask(await request(`${root}/${encodeURIComponent(task.id)}`, {
      method: 'PATCH', body: updateRequest(task, draft), actor: validateActor(actor),
    })),
    history: (id, offset = 0) => request(`${root}/${encodeURIComponent(id)}/history`, { parameters: pageParameters(20, offset) }),
  };
}
