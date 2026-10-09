import { demoAssets, makeDemoDashboard, makeDemoComparison } from '../data/demoData';

export const DEMO_MODE = import.meta.env.VITE_DATA_MODE !== 'live';
const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const dashboardPath = import.meta.env.VITE_DASHBOARD_PATH || '/dashboard';
const comparisonPath = import.meta.env.VITE_COMPARISON_PATH || '/what-if';
const tasksPath = import.meta.env.VITE_TASKS_PATH || '/maintenance/tasks';
const alertsPath = import.meta.env.VITE_ALERTS_PATH || '/alerts';
const storeKey = 'person-c-demo-tasks-v1';

async function request(path, options = {}) {
  if (!base) throw new Error('Set VITE_API_BASE_URL before selecting live mode.');
  const response = await fetch(`${base}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new Error(`Request failed (${response.status}).`);
  if (response.status === 204) return null;
  return response.json();
}

export async function getAssets() {
  return DEMO_MODE ? demoAssets : request('/assets');
}
export async function getDashboard(assetId, scenario) {
  return DEMO_MODE ? makeDemoDashboard(assetId, scenario) : request(`${dashboardPath}?assetId=${encodeURIComponent(assetId)}`);
}
export async function compareScenarios(assetId, alternative) {
  return DEMO_MODE ? makeDemoComparison(assetId, alternative) : request(comparisonPath, {
    method: 'POST', body: JSON.stringify({ assetId, alternative }),
  });
}
export async function acknowledgeAlert(alertId) {
  return DEMO_MODE ? { status: 'Acknowledged' } : request(`${alertsPath}/${encodeURIComponent(alertId)}/acknowledge`, { method: 'POST' });
}
export async function getTasks() {
  if (!DEMO_MODE) return request(tasksPath);
  return JSON.parse(localStorage.getItem(storeKey) || '[]');
}
export async function createTask(task) {
  if (!DEMO_MODE) return request(tasksPath, { method: 'POST', body: JSON.stringify(task) });
  const tasks = await getTasks();
  const saved = { ...task, id: crypto.randomUUID(), status: 'Open', notes: '', createdAt: new Date().toISOString() };
  localStorage.setItem(storeKey, JSON.stringify([saved, ...tasks]));
  return saved;
}
export async function updateTask(id, changes) {
  if (!DEMO_MODE) return request(`${tasksPath}/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(changes) });
  const tasks = await getTasks();
  const updated = tasks.map(task => task.id === id ? { ...task, ...changes } : task);
  localStorage.setItem(storeKey, JSON.stringify(updated));
  return updated.find(task => task.id === id);
}
