/* Optional integration check: requires Playwright and installed Chrome.
   Runs against the reachable demo backend; creates clearly labeled sample tasks.
   NODE_PATH can point to a separately installed Playwright package directory. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const origin = process.env.FRONTEND_ORIGIN || 'http://127.0.0.1:5173';
const base = process.env.BACKEND_ORIGIN || 'http://127.0.0.1:8000';
const assetId = process.env.DEMO_ASSET_ID;
const runId = process.env.DEMO_RUN_ID;
if (!assetId || !runId) throw new Error('Provide DEMO_ASSET_ID and DEMO_RUN_ID from the local verifier.');
const artifactDir = process.env.BROWSER_ARTIFACT_DIR || path.join(__dirname, 'browser-results');
fs.mkdirSync(artifactDir, { recursive: true });
const results = { origin, base, assetId, runId, checks: [], taskIds: [], consoleErrors: [], requests: [] };
async function api(route, method = 'GET', body, expected = 200) {
  const response = await fetch(base + route, { method,
    headers: body ? { 'Content-Type': 'application/json', 'X-Demo-Actor': 'Person C integration verifier' } : {},
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const value = await response.json();
  assert.equal(response.status, expected, JSON.stringify(value)); return value;
}
const expectText = async (locator, text) => { await locator.getByText(text, { exact: false }).first().waitFor(); };
async function main() {
  const browser = await chromium.launch({ executablePath: process.env.BROWSER_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on('pageerror', error => results.consoleErrors.push(error.message));
    page.on('request', request => { if (request.url().startsWith(base)) results.requests.push({ method: request.method(), url: request.url(), actor: request.headers()['x-demo-actor'] ?? null }); });
    await page.goto(origin); await page.getByRole('heading', { name: 'Fleet overview' }).waitFor();
    const nav = name => page.getByRole('navigation').getByRole('button', { name, exact: true }).click();
    await nav('Backend readings');
    await page.getByRole('button', { name: 'Load registered transformers', exact: true }).click();
    await page.getByLabel(/^Registered transformer/).selectOption(assetId);
    await page.getByRole('button', { name: 'Load latest reading and history', exact: true }).click();
    await expectText(page, 'No latest reading exists for this selected stream.'); await expectText(page, 'No history readings on this page.');
    results.checks.push('Actual browser: registered assets, detail, empty device latest 404 and empty history distinguished');
    await page.getByLabel(/^Telemetry source/).selectOption('simulator');
    await page.getByLabel('Run ID', { exact: true }).fill(runId);
    await page.getByRole('button', { name: 'Load latest reading and history', exact: true }).click();
    await expectText(page, 'Analytics status: pending'); await expectText(page, 'Processing job: pending');
    assert.equal(await page.locator('table').last().locator('tbody tr').count(), 6);
    await expectText(page, 'Current registry configuration: 1'); await expectText(page, 'Reading configuration: 1');
    await page.getByRole('button', { name: 'Load latest reading and history', exact: true }).click();
    await expectText(page, 'Analytics status: pending');
    results.checks.push('Actual browser: simulator latest/history, six rows, source/run, manual refresh, pending jobs and configuration distinctions');
    await page.getByLabel('Run ID', { exact: true }).fill('wrong-demo-run');
    await page.getByRole('button', { name: 'Load latest reading and history', exact: true }).click();
    await expectText(page, 'No latest reading exists for this selected stream.');
    await page.getByLabel(/^Telemetry source/).selectOption('file_replay');
    await page.getByLabel('Run ID', { exact: true }).fill(runId);
    await page.getByRole('button', { name: 'Load latest reading and history', exact: true }).click();
    await expectText(page, 'No latest reading exists for this selected stream.');
    results.checks.push('Actual browser: wrong run and wrong source do not leak simulator readings');

    await nav('Backend maintenance');
    async function selectMaintenance() {
      await page.getByRole('button', { name: 'Load registered assets', exact: true }).click();
      await page.getByLabel('Maintenance asset', { exact: true }).selectOption(assetId);
      await page.getByRole('button', { name: 'Load / refresh backend tasks', exact: true }).click();
    }
    await selectMaintenance();
    let sequence = 0;
    async function createTask(owner = '') {
      const title = `Sample C browser inspection ${Date.now()}-${sequence++}`;
      await page.getByLabel('Task action', { exact: true }).fill(title);
      await page.getByLabel('Initial assigned person', { exact: true }).fill(owner);
      await page.getByRole('button', { name: 'Create backend task', exact: true }).click();
      await page.getByRole('heading', { name: title, exact: true }).waitFor();
      const card = page.locator('.task').filter({ has: page.getByRole('heading', { name: title, exact: true }) });
      const id = await card.getAttribute('data-task-id'); results.taskIds.push(id);
      return { card, id, title };
    }
    const completed = await createTask();
    assert(!(await completed.card.getByLabel('Task status').locator('option').allTextContents()).includes('Completed'));
    await completed.card.getByLabel('Task status').selectOption('in_progress');
    await completed.card.getByRole('button', { name: 'Save task update' }).click();
    await expectText(completed.card, 'Assign an owner');
    await completed.card.getByLabel('Task status').selectOption('open');
    await completed.card.getByLabel('Assigned person', { exact: true }).fill('Person C sample maintainer');
    await completed.card.getByRole('button', { name: 'Save task update' }).click();
    await expectText(completed.card, 'Version: 2');
    await completed.card.getByLabel('Task status').selectOption('in_progress');
    await completed.card.getByRole('button', { name: 'Save task update' }).click();
    await expectText(completed.card, 'Version: 3');
    await completed.card.getByLabel('Task status').selectOption('completed');
    await completed.card.getByRole('button', { name: 'Save task update' }).click();
    await expectText(completed.card, 'nonblank notes');
    await completed.card.getByLabel('Task notes').fill('Sample browser inspection completed.');
    await completed.card.getByRole('button', { name: 'Save task update' }).click();
    await expectText(completed.card, 'Version: 4');
    assert(await completed.card.getByRole('button', { name: 'Save task update' }).isDisabled());
    await completed.card.getByRole('button', { name: 'View history' }).click();
    await expectText(page, 'Version 4: In progress → Completed'); await expectText(page, 'Identity source: demo_header');
    results.checks.push('Actual browser: create, unassigned-start rejection, assign, start, required completion notes, terminal read-only and history');

    const competing = await createTask('Person C sample maintainer');
    await competing.card.getByLabel('Task notes').fill('Retained browser draft for operator review.');
    await api(`/api/v1/maintenance/tasks/${competing.id}`, 'PATCH', { expected_version: 1, notes: 'Concurrent operator note.' });
    await competing.card.getByRole('button', { name: 'Save task update' }).click();
    await expectText(competing.card, 'Latest task loaded.');
    assert.equal(await competing.card.getByLabel('Task notes').inputValue(), 'Retained browser draft for operator review.');
    assert(await competing.card.getByRole('button', { name: 'Save task update' }).isDisabled());
    await expectText(competing.card, 'Saved notes: Concurrent operator note.');
    await competing.card.getByRole('button', { name: 'I reviewed the latest task; enable saving my draft', exact: true }).click();
    await competing.card.getByRole('button', { name: 'Save task update' }).click();
    await expectText(competing.card, 'Version: 3');
    results.checks.push('Actual browser: 409 retrieves latest, preserves draft, blocks automatic retry, requires explicit review and submits returned version');

    for (const initial of ['open', 'in_progress']) {
      const cancelled = await createTask('Person C sample maintainer');
      if (initial === 'in_progress') {
        await cancelled.card.getByLabel('Task status').selectOption('in_progress');
        await cancelled.card.getByRole('button', { name: 'Save task update' }).click(); await expectText(cancelled.card, 'Version: 2');
      }
      await cancelled.card.getByLabel('Task status').selectOption('cancelled');
      await cancelled.card.getByRole('button', { name: 'Save task update' }).click(); await expectText(cancelled.card, 'nonblank notes');
      await cancelled.card.getByLabel('Task notes').fill('Sample cancellation: testing workflow only.');
      await cancelled.card.getByRole('button', { name: 'Save task update' }).click(); await expectText(cancelled.card, 'read-only');
    }
    results.checks.push('Actual browser: cancellation from open/in-progress requires notes and produces read-only tasks');
    await api(`/api/v1/maintenance/tasks/${completed.id}`, 'PATCH', { expected_version: 4, notes: 'Terminal mutation must be rejected.' }, 409);
    await api(`/api/v1/maintenance/tasks/${competing.id}`, 'PATCH', { expected_version: 3, status: 'completed', notes: 'Illegal direct completion.' }, 409);
    results.checks.push('Actual API: terminal mutation and open-to-completed rejected');
    await page.reload(); await nav('Backend maintenance');
    await page.getByRole('button', { name: 'Load registered assets', exact: true }).click();
    await page.getByLabel('Maintenance asset', { exact: true }).selectOption(assetId);
    await page.getByRole('button', { name: 'Load / refresh backend tasks', exact: true }).click();
    await expectText(page.locator(`[data-task-id="${completed.id}"]`), 'Saved: Completed');
    results.checks.push('Actual browser refresh: PostgreSQL completed task persists');
    await page.screenshot({ path: path.join(artifactDir, 'backend-maintenance-desktop.png'), fullPage: true });

    // Clearly distinguished intercepted fixtures test UI pagination/missing values without fabricating backend verification.
    await nav('Backend readings');
    await page.route(`${base}/api/v1/assets?*`, route => route.fulfill({ json: { items: Array.from({ length: 20 }, (_, i) => ({ asset_id: `fixture-${i}`, name: 'Intercepted fixture' })), limit: 20, offset: Number(new URL(route.request().url()).searchParams.get('offset')) } }));
    await page.getByRole('button', { name: 'Load registered transformers', exact: true }).click();
    await page.getByRole('button', { name: 'Next asset page', exact: true }).click(); await expectText(page, 'Asset page: 2');
    await page.unroute(`${base}/api/v1/assets?*`);
    await page.getByRole('button', { name: 'Load registered transformers', exact: true }).click();
    await page.getByLabel(/^Registered transformer/).selectOption(assetId);
    const reading = await api(`/api/v1/assets/${assetId}/telemetry/latest?source=simulator&run_id=${runId}`);
    reading.normalized_telemetry.measurements.oil_temperature_c = null;
    reading.normalized_telemetry.measurements.current_r_a = 0;
    await page.route(`${base}/api/v1/assets/${assetId}/telemetry**`, route => {
      const url = new URL(route.request().url());
      return route.fulfill({ json: url.pathname.endsWith('/latest') ? reading : { items: Array.from({ length: 20 }, (_, i) => ({ ...reading, id: 10000 + i })), limit: 20, offset: Number(url.searchParams.get('offset')) } });
    });
    await page.getByRole('button', { name: 'Load latest reading and history', exact: true }).click();
    const oil = page.locator('table').first().locator('tbody tr').filter({ hasText: 'Oil temperature' });
    const current = page.locator('table').first().locator('tbody tr').filter({ hasText: 'R-phase current' });
    await expectText(oil, 'Unavailable'); assert.equal(await current.locator('td').nth(1).textContent(), '0');
    await page.getByRole('button', { name: 'Next history page', exact: true }).click(); await expectText(page, 'History page: 2');
    await page.unroute(`${base}/api/v1/assets/${assetId}/telemetry**`);
    results.checks.push('Intercepted browser fixtures only: telemetry asset/history pagination, null remains unavailable and explicit zero remains zero');
    await page.route(`${base}/**`, route => route.abort('connectionrefused'));
    await page.getByRole('button', { name: 'Load registered transformers', exact: true }).click();
    await page.locator('p.error').first().waitFor();
    await nav('Backend maintenance'); await page.getByRole('button', { name: 'Load registered assets', exact: true }).click();
    await expectText(page, 'Cannot reach the maintenance backend'); assert(await page.getByRole('button', { name: 'Create backend task' }).isDisabled());
    await page.unroute(`${base}/**`);
    results.checks.push('Intercepted browser network failure: visible telemetry/maintenance errors, no demo fallback and creation disabled without registered asset');
    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    await mobile.addInitScript(() => Object.defineProperty(globalThis.crypto, 'randomUUID', { value: undefined, configurable: true }));
    const phone = await mobile.newPage();
    await phone.goto(origin); await phone.getByRole('navigation').getByRole('button', { name: 'Maintenance', exact: true }).click();
    const demoTitle = `Sample browser-local persistence ${Date.now()}`;
    await phone.getByLabel('Task title', { exact: true }).fill(demoTitle);
    await phone.getByLabel('Assigned person', { exact: true }).first().fill('Sample phone operator');
    await phone.getByRole('button', { name: 'Save task', exact: true }).click(); await phone.getByRole('heading', { name: demoTitle, exact: true }).waitFor();
    await phone.reload(); await phone.getByRole('navigation').getByRole('button', { name: 'Maintenance', exact: true }).click();
    await phone.getByRole('heading', { name: demoTitle, exact: true }).waitFor();
    await phone.getByRole('navigation').getByRole('button', { name: 'Backend maintenance', exact: true }).click();
    await phone.getByRole('button', { name: 'Load registered assets', exact: true }).click();
    await phone.getByLabel('Maintenance asset', { exact: true }).selectOption(assetId);
    await phone.getByRole('button', { name: 'Load / refresh backend tasks', exact: true }).click();
    await expectText(phone.locator(`[data-task-id="${completed.id}"]`), 'Saved: Completed');
    assert(await phone.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await phone.screenshot({ path: path.join(artifactDir, 'backend-maintenance-mobile.png'), fullPage: true });
    results.checks.push('390px touch browser emulation: demo randomUUID fallback, saving/refresh persistence, backend records and no horizontal page overflow; physical phone not tested');
    await mobile.close();
    assert.deepEqual(results.consoleErrors, []);
    assert(results.requests.some(request => request.method === 'PATCH' && request.actor === 'Person C demo operator'));
    results.checks.push('Actual origin CORS: browser GET, POST and PATCH with X-Demo-Actor succeeded; no uncaught page errors');
    const secondary = await context.newPage(); await secondary.goto('http://localhost:5173');
    const health = await secondary.evaluate(async backend => { const response = await fetch(backend + '/health/ready'); return response.json(); }, base);
    assert.equal(health.status, 'ready'); results.checks.push('Secondary origin http://localhost:5173: browser CORS readiness request succeeds');
    await context.close();
  } finally {
    fs.writeFileSync(path.join(artifactDir, 'browser-verification.json'), JSON.stringify(results, null, 2));
    await browser.close();
  }
  console.log(JSON.stringify({ checks: results.checks, taskIds: results.taskIds, consoleErrors: results.consoleErrors }, null, 2));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
