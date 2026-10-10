// Actual Google Chrome, production preview and isolated persisted synthetic data.
// Credentials are read privately; no headers, passwords or storage are recorded.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const dir = process.env.REVIEW_EVIDENCE;
if (!dir || !fs.existsSync(path.join(dir, 'seed.json'))) throw Error('Owned review evidence directory required');
const seed = JSON.parse(fs.readFileSync(path.join(dir, 'seed.json')));
const base = process.env.REVIEW_API || 'http://127.0.0.1:15881';
const ui = process.env.REVIEW_UI || 'http://127.0.0.1:15882';
for (const target of [base, ui]) {
  const u = new URL(target);
  assert.equal(u.hostname, '127.0.0.1');
  assert.ok(Number(u.port) > 15000, 'Dedicated review port required');
}
const operator = fs.readFileSync(path.join(dir, 'private/operator.txt'), 'utf8').trim();
const reader = fs.readFileSync(path.join(dir, 'private/reader.txt'), 'utf8').trim();
const result = { executed_utc: new Date().toISOString(), scope: 'Actual installed Google Chrome; persisted worker incidents from labelled synthetic stream', checks: [], requests: [], pageErrors: [] };
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, message) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) { if (await fn()) return; await delay(100); }
  throw Error(message);
}
async function api(route, method = 'GET', body, token = operator) {
  const r = await fetch(base + route, { method, headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
  assert.ok(r.ok, `${method} ${route} -> ${r.status}`);
  return r.json();
}
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  result.browser = await browser.version();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, reducedMotion: 'reduce' });
  const p = await context.newPage();
  p.on('pageerror', e => result.pageErrors.push(e.message));
  p.on('response', r => { if (r.url().startsWith(base)) result.requests.push({ method: r.request().method(), url: r.url(), status: r.status() }); });
  const button = name => p.getByRole('button', { name, exact: true });
  const visible = async text => {
    for (const item of await p.getByText(text, { exact: false }).all()) if (await item.isVisible()) return true;
    return false;
  };
  const nav = async name => { await button(name).click(); await delay(300); };
  const login = async token => {
    if (await button('Disconnect').isVisible().catch(() => false)) await button('Disconnect').click();
    await p.getByLabel('Operator Bearer Token').fill(token);
    await button('Authenticate').click();
    await until(() => button('Disconnect').isVisible(), 'Authentication did not complete');
  };
  const query = async () => { await button('Query stream incidents').click(); await until(() => button('Inspect').first().isVisible(), 'Incidents missing'); };
  const inspect = async id => { await p.locator('tr').filter({ hasText: id.slice(0, 8) }).getByRole('button', { name: 'Inspect', exact: true }).click(); await until(() => visible('Evidence Records ('), 'Incident evidence missing'); };
  const editor = id => p.locator(`[data-task-id="${id}"]`);
  const save = async (id, update, text) => {
    const e = editor(id);
    if (update.owner !== undefined) await e.getByLabel('Assigned person').fill(update.owner);
    if (update.status) await e.getByLabel('Task status').selectOption(update.status);
    if (update.notes !== undefined) await e.getByLabel('Task notes').fill(update.notes);
    await e.getByRole('button', { name: 'Save task update', exact: true }).click();
    await until(() => e.getByText(text, { exact: false }).first().isVisible(), `Task update missing ${text}`);
  };
  try {
    await p.goto(ui);
    await until(() => p.locator('select[aria-label="Selected transformer"] option').count().then(n => n > 1), 'Registry did not load');
    await p.locator('select[aria-label="Selected transformer"]').selectOption(seed.asset_id);
    await p.getByLabel('Telemetry source').selectOption('simulator');
    await p.getByLabel('Run ID', { exact: true }).fill(seed.run_id);
    await button('Apply run').click();
    await until(() => visible('3 records'), 'Persisted telemetry not loaded');
    await nav('Fleet overview');
    assert.ok(await visible('D synthetic integration transformer'));
    await nav('Digital twin');
    assert.ok(await visible('55'));
    await p.getByRole('tab', { name: 'Electrical', exact: true }).click();
    assert.ok(await visible('150'));
    await p.getByRole('tab', { name: 'Overview', exact: true }).click();
    await nav('Trends & history');
    assert.ok(await visible('3 retrieved records'));
    result.checks.push('registered fleet, selected asset, persisted measurements and current-model analytics, timestamped history');
    await login(operator);
    await nav('Alerts & incidents');
    await query();
    await inspect(seed.incident_ids[0]);
    assert.ok(await visible('Detector Epoch'));
    assert.ok(await visible('assumed'));
    await button('Create maintenance task').click();
    await p.getByLabel('Task Action Title').fill('D Chrome investigate synthetic overload');
    await button('Create incident task').click();
    await until(() => p.locator('[data-task-id]').count().then(n => n > 0), 'Linked task did not open');
    const first = await p.locator('[data-task-id]').first().getAttribute('data-task-id');
    result.completed_task_id = first;
    await save(first, { owner: 'D QA assigned display label' }, 'Saved backend version 2');
    await save(first, { status: 'in_progress' }, 'Saved backend version 3');
    await save(first, { status: 'completed', notes: '' }, 'notes');
    assert.equal((await api('/api/v1/maintenance/tasks/' + first)).status, 'in_progress');
    await save(first, { notes: 'Reviewed synthetic evidence; completion does not infer recovery or acknowledgement.' }, 'Saved backend version 4');
    const beforeAck = await api('/api/v1/incidents/' + seed.incident_ids[0]);
    assert.equal(beforeAck.acknowledgement.status, 'unacknowledged');
    assert.equal(beforeAck.condition_status, 'active');
    await nav('Alerts & incidents'); await query(); await inspect(seed.incident_ids[0]);
    await button('Acknowledge incident').click();
    await until(() => visible('Acknowledged ('), 'Acknowledgement not recorded');
    assert.equal((await api('/api/v1/maintenance/tasks/' + first)).status, 'completed');
    result.checks.push('incident evidence, UI-linked task creation, owner assignment, start, completion notes validation, independent acknowledgement/task lifecycle');
    await query(); await inspect(seed.incident_ids[1]);
    await button('Create maintenance task').click();
    await p.getByLabel('Task Action Title').fill('D Chrome inspect synthetic thermal');
    await button('Create incident task').click();
    await until(() => p.locator('[data-task-id]').count().then(n => n > 0), 'Second linked task missing');
    const second = await p.locator('[data-task-id]').first().getAttribute('data-task-id');
    result.cancelled_task_id = second;
    const current = await api('/api/v1/maintenance/tasks/' + second);
    await api('/api/v1/maintenance/tasks/' + second, 'PATCH', { expected_version: current.version, owner: 'Concurrent operator' });
    await save(second, { owner: 'Retained Chrome draft' }, '409');
    assert.equal(await editor(second).getByLabel('Assigned person').inputValue(), 'Retained Chrome draft');
    assert.ok(await editor(second).getByRole('button', { name: 'Save task update', exact: true }).isDisabled());
    assert.equal((await api('/api/v1/maintenance/tasks/' + second)).owner, 'Concurrent operator');
    await editor(second).getByRole('button', { name: 'I reviewed the latest task; enable saving my draft', exact: true }).click();
    await save(second, { owner: 'Retained Chrome draft' }, 'Saved backend version 3');
    await save(second, { status: 'cancelled', notes: '' }, 'notes');
    assert.equal((await api('/api/v1/maintenance/tasks/' + second)).status, 'open');
    await save(second, { notes: 'Synthetic exercise cancelled after explicit review.' }, 'Saved backend version 4');
    await editor(second).getByRole('button', { name: 'View history', exact: true }).click();
    await until(() => visible('History for ' + second), 'Task history missing');
    result.checks.push('stale task409 refresh, retained draft, blocked overwrite, explicit review, cancellation notes, history');
    await button('Sample Alerts Mode').click();
    await button('Load / refresh sample tasks').click();
    await until(() => visible('Page 1 · 20 item(s)'), 'Sample pagination missing');
    await button('Next task page').click();
    await until(() => visible('Page 2 · 1 item(s)'), 'Second sample page missing');
    await button('Previous task page').click();
    await until(() => editor(seed.history_task_id).isVisible(), 'History fixture not on first page');
    await editor(seed.history_task_id).getByRole('button', { name: 'View history', exact: true }).click();
    await until(() => button('Next history page').isEnabled(), 'History next missing');
    await button('Next history page').click();
    await until(() => visible('Page 2 · 2 item(s)'), 'History second page missing');
    result.checks.push('retained sample tasks, task and history pagination');
    await nav('What-if analysis');
    await button('Compute What-if forecast').click();
    await until(() => visible('Captured state reference'), 'Forecast missing');
    result.state_ref = await p.getByLabel('Initial state reference (UUID)').inputValue();
    await p.getByLabel('Reduced thermal load (p.u.)').fill('0.8');
    assert.equal(await visible('Captured state reference'), false);
    await button('Compute What-if forecast').click();
    await until(() => visible('Captured state reference'), 'Repeat forecast missing');
    assert.equal(await p.getByLabel('Initial state reference (UUID)').inputValue(), result.state_ref);
    result.checks.push('actual What-if API, snapshot reuse, stale forecast cleared on input change');
    await nav('Alerts & incidents'); await query(); await inspect(seed.incident_ids[1]);
    const staleIncident = await api('/api/v1/incidents/' + seed.incident_ids[1]);
    await api('/api/v1/incidents/' + seed.incident_ids[1] + '/acknowledgements', 'POST', { schema_version: 'incident-acknowledgement-1.0.0', expected_version: staleIncident.incident_version, idempotency_key: crypto.randomUUID() });
    await button('Acknowledge incident').click();
    await until(() => visible('Conflict (409)'), 'Incident stale conflict not visible');
    assert.ok(await button('Create maintenance task').isDisabled());
    await button('Review refreshed incident').click();
    await login(reader); await query(); await inspect(seed.incident_ids[0]);
    assert.ok(await button('Create maintenance task').isDisabled());
    result.checks.push('incident409 explicit refresh/review and reader mutation controls disabled');
    await login(operator);
    await p.reload();
    await until(() => button('Disconnect').isVisible(), 'Session not restored after refresh');
    await nav('Maintenance');
    await button('Genuine Incident Tasks Mode').click();
    await button('Load / refresh incident-linked tasks').click();
    await until(() => editor(first).isVisible(), 'Records missing after refresh');
    assert.ok(await editor(first).getByText('Saved: Completed', { exact: false }).isVisible());
    assert.ok(await editor(second).getByText('Saved: Cancelled', { exact: false }).isVisible());
    result.checks.push('Chrome refresh persisted completed/cancelled tasks and server-verified session');
    await p.screenshot({ path: path.join(dir, 'chrome-maintenance.png'), fullPage: true });
    // External orchestration stops/restarts ONLY the owned isolated API.
    if (process.env.REVIEW_RESTART === '1') {
      fs.writeFileSync(path.join(dir, 'stop-request.flag'), 'ready');
      await until(() => fs.existsSync(path.join(dir, 'stopped.flag')), 'Owned API stop not confirmed');
      await button('Load / refresh incident-linked tasks').click();
      await until(() => visible('Cannot reach the maintenance backend'), 'Actual offline error missing');
      result.checks.push('actual stopped-backend offline error visible');
      fs.writeFileSync(path.join(dir, 'restart-request.flag'), 'ready');
      await until(() => fs.existsSync(path.join(dir, 'restarted.flag')), 'Owned API restart not confirmed');
      await button('Load / refresh incident-linked tasks').click();
      await until(() => editor(first).isVisible(), 'Tasks missing after backend restart');
      assert.ok(await editor(first).getByText('Saved: Completed', { exact: false }).isVisible());
      assert.ok(await editor(second).getByText('Saved: Cancelled', { exact: false }).isVisible());
      result.checks.push('actual backend restart persistence in Chrome');
    }
    await p.setViewportSize({ width: 390, height: 844 });
    await button('Open navigation').click();
    await p.getByRole('dialog').getByRole('button', { name: 'Fleet overview', exact: true }).click();
    assert.equal(await p.getByRole('dialog').isVisible(), false);
    await until(() => p.getByRole('heading', { name: 'Backend maintenance', exact: true }).count().then(n => n === 0), 'Previous view did not exit');
    assert.equal(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2), false);
    await p.screenshot({ path: path.join(dir, 'chrome-mobile.png'), fullPage: true });
    result.checks.push('mobile navigation drawer and no horizontal overflow');
    assert.deepEqual(result.pageErrors, []);
    result.status = 'PASS';
    console.log('PASS actual Chrome: ' + result.checks.length + ' workflow groups');
  } catch (e) {
    result.status = 'FAIL'; result.failure = e.message;
    await p.screenshot({ path: path.join(dir, 'chrome-failure.png'), fullPage: true }).catch(() => {});
    console.error(e.message); process.exitCode = 1;
  } finally {
    fs.writeFileSync(path.join(dir, 'chrome.json'), JSON.stringify(result, null, 2) + '\n');
    await browser.close();
  }
})();
