const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.BACKEND_ORIGIN || 'http://127.0.0.1:8000';
const assetId = process.env.DEMO_ASSET_ID;
if (!assetId) throw new Error('Provide DEMO_ASSET_ID from your local telemetry verifier.');
const directory = process.env.BROWSER_ARTIFACT_DIR || path.join(__dirname, 'browser-results');
fs.mkdirSync(directory, { recursive: true });
const checks = [];
async function api(route) { const response = await fetch(base + route); assert.equal(response.status, 200); return response.json(); }
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.BROWSER_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  try {
    const page = await browser.newPage();
    await page.goto(process.env.FRONTEND_ORIGIN || 'http://127.0.0.1:5173');
    await page.getByRole('navigation').getByRole('button', { name: 'Backend maintenance', exact: true }).click();
    await page.getByRole('button', { name: 'Load registered assets', exact: true }).click();
    await page.getByLabel('Maintenance asset').selectOption(assetId);
    const page0 = await api(`/api/v1/maintenance/tasks?asset_id=${assetId}&limit=2&offset=0`);
    const page1 = await api(`/api/v1/maintenance/tasks?asset_id=${assetId}&limit=2&offset=2`);
    assert.equal(page0.items.length, 2); assert.equal(page1.items.length, 2);
    assert(!page0.items.some(a => page1.items.some(b => a.id === b.id)));
    const completed = page0.items.find(task => task.status === 'completed');
    assert(completed);
    const history0 = await api(`/api/v1/maintenance/tasks/${completed.id}/history?limit=2&offset=0`);
    const history1 = await api(`/api/v1/maintenance/tasks/${completed.id}/history?limit=2&offset=2`);
    assert.deepEqual([...history0.items, ...history1.items].map(row => row.version), [1, 2, 3, 4]);
    checks.push('Actual HTTP pagination: maintenance task pages do not overlap; history offset retrieves versions 3/4');
    const fixture = { ...completed, id: 'fixture-task', status: 'open', owner: 'Fixture maintainer', notes: '', version: 1 };
    await page.route(`${base}/api/v1/maintenance/tasks?*`, route => {
      const offset = Number(new URL(route.request().url()).searchParams.get('offset'));
      return route.fulfill({ json: { items: offset === 0 ? Array.from({ length: 20 }, (_, index) => ({ ...fixture, id: `fixture-task-${index}` })) : [fixture], limit: 20, offset } });
    });
    await page.getByRole('button', { name: 'Load / refresh backend tasks' }).click();
    await page.getByRole('button', { name: 'Next task page', exact: true }).click();
    await page.getByLabel('task pagination').getByText('Page 2').waitFor();
    await page.route(`${base}/api/v1/maintenance/tasks/fixture-task/history?*`, route => route.fulfill({ json: {
      items: Array.from({ length: 20 }, (_, index) => ({ id: index, task_id: fixture.id, version: index + 1,
        previous_status: 'open', new_status: 'open', previous_owner: null, new_owner: 'Fixture maintainer', previous_notes: '', notes: 'Fixture history', actor: 'Fixture actor', identity_source: 'demo_header', created_at: '2026-01-01T00:00:00Z' })),
      limit: 20, offset: Number(new URL(route.request().url()).searchParams.get('offset')),
    } }));
    const card = page.locator('[data-task-id="fixture-task"]');
    await card.getByRole('button', { name: 'View history' }).click();
    await page.getByRole('button', { name: 'Next history page', exact: true }).click();
    await page.getByLabel('history pagination').getByText('Page 2').waitFor();
    checks.push('Intercepted browser fixtures only: task/history page controls issue offset=20 and render page 2');
    await page.route(`${base}/api/v1/maintenance/tasks/fixture-task`, route => {
      return route.request().method() === 'PATCH' ? route.fulfill({ status: 409, json: { detail: 'Fixture stale-version conflict' } }) : route.abort('connectionrefused');
    });
    await card.getByLabel('Task notes').fill('Keep this fixture draft while refresh is unavailable.');
    await card.getByRole('button', { name: 'Save task update' }).click();
    await card.getByText('Latest task could not be loaded', { exact: false }).waitFor();
    assert.equal(await card.getByLabel('Task notes').inputValue(), 'Keep this fixture draft while refresh is unavailable.');
    assert(await card.getByRole('button', { name: 'Save task update' }).isDisabled());
    await page.unroute(`${base}/api/v1/maintenance/tasks/fixture-task`);
    await page.route(`${base}/api/v1/maintenance/tasks/fixture-task`, route => route.fulfill({ json: { ...fixture, status: 'cancelled', notes: 'Cancelled by a competing fixture operator.', version: 2 } }));
    await card.getByRole('button', { name: 'Retrieve latest task for review' }).click();
    await card.getByText('This completed/cancelled task is read-only.', { exact: true }).waitFor();
    assert.equal(await card.getByLabel('Task notes').inputValue(), 'Keep this fixture draft while refresh is unavailable.');
    assert(await card.getByRole('button', { name: 'Save task update' }).isDisabled());
    assert.equal(await card.getByRole('button', { name: 'I reviewed the latest task; enable saving my draft' }).count(), 0);
    checks.push('Intercepted browser fixtures only: failed 409 refresh keeps draft and blocks save; retry loads terminal state and keeps it read-only');
    console.log(JSON.stringify(checks, null, 2));
    fs.writeFileSync(path.join(directory, 'additional-checks.json'), JSON.stringify(checks, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
