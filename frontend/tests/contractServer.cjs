/* Local test double, never imported by the application. Not a backend deployment.
   Used for browser contract checks of pending analytics, history and maintenance conflicts. */
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/analytics-worker-result.json')));
const telemetryFixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../src/data/telemetryResponseSample.json')));
const configuration = { version: 1, rated_kva: 1000, rated_voltage_v: 11000, rated_current_a: 52.49, measurement_side: 'primary', voltage_convention: 'line_to_line', cooling_type: 'ONAN', operational_limits: { max_load_pct: 120, max_top_oil_temp_c: 105 }, thermal_parameters: {}, parameter_provenance: { rated_kva: 'assumed', 'operational_limits.max_load_pct': 'assumed', 'operational_limits.max_top_oil_temp_c': 'assumed' }, created_at: '2026-01-01T00:00:00Z' };
const assets = [1, 2].map(id => ({ asset_id: `CONTRACT-TX-0${id}`, name: `Contract test fixture ${id}`, location: 'Local API test double', timezone: 'Asia/Kolkata', current_configuration: { ...configuration, asset_id: `CONTRACT-TX-0${id}` } }));
let tasks = [];
let events = [];
let conflictOnce = true;
function reading(id, asset, source, run) {
  const raw = structuredClone(telemetryFixture);
  const timestamp = `2026-01-01T00:${String(id).padStart(2, '0')}:00Z`;
  Object.assign(raw, { id, asset_id: asset, source, run_id: run, measurement_time: timestamp, arrival_time: timestamp, analytics_status: id === 25 ? 'pending' : 'completed', quality_flags: {}, processing_job: { id, status: id === 25 ? 'pending' : 'completed', state_policy: 'forward_only' } });
  Object.assign(raw.normalized_telemetry, { asset_id: asset, source, run_id: run, timestamp, configuration_version: 1, measurements: { voltage_r_v: 10954.1, voltage_y_v: 11058.9, voltage_b_v: 11143.5, current_r_a: 35.1, current_y_a: 35.4, current_b_a: 35.7, oil_temperature_c: 44.678637, ambient_temperature_c: 25.04363, oil_level_pct: null } });
  raw.normalized_telemetry.measurement_quality = Object.fromEntries(Object.entries(raw.normalized_telemetry.measurements).map(([key, value]) => [key, value == null ? 'missing' : 'good']));
  raw.original_payload = raw.normalized_telemetry;
  raw.quality_flags = { oil_level_pct: ['missing'] };
  return raw;
}
function analytics(id, asset, source, run) {
  const item = structuredClone(fixture);
  const raw = reading(id, asset, source, run);
  Object.assign(item, { reading_id: id, asset_id: asset, source, run_id: run, measurement_time: raw.measurement_time, status: id === 25 ? 'pending' : 'completed' });
  Object.assign(item.result, { id, reading_id: id });
  Object.assign(item.result.payload.metadata, { stream: { asset_id: asset, source, run_id: run }, measurement_time: raw.measurement_time, measurement_source: source, reading_identity: { reading_id: id, message_id: raw.message_id } });
  if (id === 25) item.result = null;
  return item;
}
function send(response, status, body) { response.writeHead(status, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type,X-Demo-Actor', 'Access-Control-Allow-Methods': 'GET,POST,PATCH,OPTIONS' }); response.end(JSON.stringify(body)); }
http.createServer(async (request, response) => {
  const url = new URL(request.url, 'http://127.0.0.1:8008');
  if (url.pathname === '/openapi.json') return send(response, 200, { openapi: '3.1.0', info: { version: 'frontend-test-double' }, paths: { '/api/v1/telemetry/{reading_id}/analytics': { get: {} }, '/api/v1/assets/{asset_id}/analytics/latest': { get: {} }, '/api/v1/maintenance/tasks': { get: {}, post: {} }, '/api/v1/maintenance/tasks/{task_id}': { get: {}, patch: {} }, '/api/v1/maintenance/tasks/{task_id}/history': { get: {} } } });
  if (request.method === 'OPTIONS') return send(response, 200, {});
  let body = '';
  for await (const chunk of request) body += chunk;
  const input = body ? JSON.parse(body) : null;
  const segments = url.pathname.split('/').filter(Boolean);
  const asset = segments[3] || assets[0].asset_id;
  const source = url.searchParams.get('source') || 'device';
  const run = source === 'device' ? null : url.searchParams.get('run_id');
  const limit = Number(url.searchParams.get('limit') || 20);
  const offset = Number(url.searchParams.get('offset') || 0);
  if (run === 'slow') await new Promise(resolve => setTimeout(resolve, 500));
  if (url.pathname === '/api/v1/assets') return send(response, 200, { items: assets.slice(offset, offset + limit), limit, offset });
  if (segments[2] === 'assets' && segments.length === 4) return send(response, 200, assets.find(item => item.asset_id === asset) || assets[0]);
  if (segments[2] === 'assets' && segments[4] === 'telemetry') {
    if (source !== 'device' && !run) return send(response, 422, { detail: 'run_id required' });
    if (run === 'empty') return segments[5] === 'latest' ? send(response, 404, { detail: 'No telemetry in selected stream' }) : send(response, 200, { items: [], limit, offset });
    if (segments[5] === 'latest') return send(response, 200, reading(25, asset, source, run));
    let readings = Array.from({ length: 25 }, (_, index) => reading(index + 1, asset, source, run));
    const start = url.searchParams.get('start'); const end = url.searchParams.get('end');
    readings = readings.filter(item => (!start || item.measurement_time >= start) && (!end || item.measurement_time < end));
    return send(response, 200, { items: readings.slice(offset, offset + limit), limit, offset });
  }
  if (segments[2] === 'assets' && segments[4] === 'analytics') {
    if (run === 'noanalytics') return send(response, 404, { detail: 'Analytics route absent on older branch' });
    const completed = analytics(24, asset, source, run);
    return send(response, 200, { schema_version: '1.0.0', asset_id: asset, source, run_id: run, latest_telemetry_reading_id: 25, latest_telemetry_status: 'pending', latest_telemetry_measurement_time: reading(25, asset, source, run).measurement_time, latest_completed_reading_id: 24, latest_completed_measurement_time: completed.measurement_time, result: completed.result });
  }
  if (segments[2] === 'telemetry' && segments[4] === 'analytics') {
    // getReadingAnalytics has no stream query. Infer the active stream from latest calls.
    return send(response, 200, analytics(Number(segments[3]), active.asset, active.source, active.run));
  }
  if (segments[2] === 'maintenance' && segments[3] === 'tasks') {
    const id = segments[4]; const now = new Date().toISOString();
    if (request.method === 'POST') {
      const task = { id: '550e8400-e29b-41d4-a716-446655440000', asset_id: input.alert.asset_id, alert: input.alert, action: input.action, owner: input.owner, status: 'open', notes: '', version: 1, created_at: now, updated_at: now };
      tasks.push(task); events.push({ id: 1, task_id: task.id, version: 1, event_type: 'created', previous_status: null, new_status: 'open', previous_owner: null, new_owner: task.owner, notes: '', actor: null, identity_source: 'unattributed_creation', created_at: now });
      return send(response, 201, task);
    }
    const task = tasks.find(item => item.id === id);
    if (request.method === 'PATCH') {
      if (conflictOnce) { conflictOnce = false; task.version++; task.owner = 'Other test operator'; return send(response, 409, { detail: 'Task version changed' }); }
      if (input.expected_version !== task.version) return send(response, 409, { detail: 'Task version changed' });
      const previous = { ...task }; Object.assign(task, input, { version: task.version + 1, updated_at: now }); delete task.expected_version;
      events.push({ id: events.length + 1, task_id: id, version: task.version, event_type: 'updated', previous_status: previous.status, new_status: task.status, previous_owner: previous.owner, new_owner: task.owner, previous_notes: previous.notes, notes: task.notes, actor: request.headers['x-demo-actor'], identity_source: 'demo_header', created_at: now });
      return send(response, 200, task);
    }
    if (segments[5] === 'history') return send(response, 200, { items: events.filter(item => item.task_id === id).slice(offset, offset + limit), limit, offset });
    if (id) return send(response, task ? 200 : 404, task || { detail: 'No task' });
    return send(response, 200, { items: tasks.filter(item => !url.searchParams.get('asset_id') || item.asset_id === url.searchParams.get('asset_id')).slice(offset, offset + limit), limit, offset });
  }
  return send(response, 404, { detail: 'Test route not defined' });
}).on('request', request => {
  const url = new URL(request.url, 'http://127.0.0.1:8008');
  const match = url.pathname.match(/^\/api\/v1\/assets\/([^/]+)\/(?:telemetry|analytics)\/latest$/);
  if (match) active = { asset: match[1], source: url.searchParams.get('source') || 'device', run: url.searchParams.get('run_id') || null };
}).listen(8008, '127.0.0.1', () => console.log('Frontend contract fixture server: http://127.0.0.1:8008 (TEST DOUBLE ONLY)'));
let active = { asset: assets[0].asset_id, source: 'device', run: null };
