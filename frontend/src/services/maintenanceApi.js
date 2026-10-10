import { adaptTask, createRequest, createAnalyticsRequest, updateRequest, validateActor, pageParameters } from './maintenanceAdapter.js';

export class MaintenanceApiError extends Error {
  constructor(status, message) { super(message); this.name = 'MaintenanceApiError'; this.status = status; }
}

export function createMaintenanceClient({ baseUrl, fetchImpl = globalThis.fetch }) {
  const base = (baseUrl ?? '').trim().replace(/\/+$/, '');
  const controllers = new Set();
  const root = '/api/v1/maintenance/tasks';

  async function request(path, { parameters = {}, method = 'GET', body, actor, token } = {}) {
    if (!base) throw new Error('Set VITE_API_BASE_URL to a reachable backend and restart Vite.');
    const controller = new AbortController();
    controllers.add(controller);
    try {
    const url = new URL(`${base}${path}`);
    for (const [key, value] of Object.entries(parameters)) {
      if (value !== '' && value != null) url.searchParams.set(key, value);
    }

    const headers = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (token) {
      headers['Authorization'] = `Bearer ${token.trim()}`;
    } else if (actor !== undefined) {
      headers['X-Demo-Actor'] = actor;
    }

    let response;
    try {
      response = await fetchImpl(url, {
        method,
        headers,
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
      if (response.status === 401 && token) globalThis.dispatchEvent?.(new Event('powernxt-credential-invalid'));
      const detail = result.detail;
      const message = result.message || (typeof detail === 'string' ? detail : Array.isArray(detail)
        ? detail.map(item => `${item.loc?.join('.') ?? 'request'}: ${item.msg}`).join('; ')
        : `Maintenance request failed (${response.status}).`);
      throw new MaintenanceApiError(response.status, message);
    }
    return result;
    } finally { controllers.delete(controller); }
  }

  return {
    cancelAll() { for (const controller of controllers) controller.abort(); controllers.clear(); },
    assets: (offset = 0) => request('/api/v1/assets', { parameters: pageParameters(20, offset) }),
    tasks: async (assetId = '', offset = 0, source = 'sample', token = null) => {
      const parameters = { ...pageParameters(20, offset), source };
      if (assetId) parameters.asset_id = assetId;
      const page = await request(root, { parameters, token });
      return { ...page, items: page.items.map(adaptTask) };
    },
    task: async (id, token = null) => adaptTask(await request(`${root}/${encodeURIComponent(id)}`, { token })),
    create: async (draft, token = null) => {
      const body = draft.sampleMode === true
        ? createRequest(draft)
        : createAnalyticsRequest(draft);
      return adaptTask(await request(root, { method: 'POST', body, token }));
    },
    update: async (task, draft, actor = null, token = null) => {
      const isAnalytics = task.incidentId != null || task.alert?.source === 'analytics';
      return adaptTask(await request(`${root}/${encodeURIComponent(task.id)}`, {
        method: 'PATCH',
        body: updateRequest(task, draft),
        actor: isAnalytics ? undefined : validateActor(actor),
        token: isAnalytics ? token : undefined,
      }));
    },
    history: (id, offset = 0, token = null) => request(`${root}/${encodeURIComponent(id)}/history`, {
      parameters: pageParameters(20, offset),
      token,
    }),
  };
}
