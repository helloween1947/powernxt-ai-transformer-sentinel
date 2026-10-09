const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.BACKEND_ORIGIN || 'http://127.0.0.1:8000';
const origin = process.env.FRONTEND_ORIGIN || 'http://127.0.0.1:5173';
const token = Date.now();
const assetId = `sample-c-pagination-${token}`;
async function api(route, method = 'GET', body) {
  const response = await fetch(base + route, { method,
    headers: body ? { 'Content-Type': 'application/json', 'X-Demo-Actor': 'Person C pagination verifier' } : {},
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  assert(response.ok, await response.clone().text()); return response.json();
}
(async () => {
  await api('/api/v1/assets', 'POST', { asset_id: assetId, name: 'SAMPLE C pagination integration only', location: 'Isolated demo lab', timezone: 'UTC' });
  let historyTask;
  for (let index = 0; index < 21; index++) {
    const task = await api('/api/v1/maintenance/tasks', 'POST', { alert: {
      source: 'sample', alert_id: `sample-pagination-${token}-${index}`, asset_id: assetId, summary: 'Sample pagination check; not a detector result.',
    }, action: `Sample pagination task ${index}`, owner: 'Sample pagination maintainer' });
    if (index === 0) historyTask = task;
  }
  for (let index = 0; index < 21; index++) historyTask = await api(`/api/v1/maintenance/tasks/${historyTask.id}`, 'PATCH', { expected_version: historyTask.version, notes: `Sample history event ${index}` });
  const browser = await chromium.launch({ executablePath: process.env.BROWSER_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const checks = [];
  try {
    const page = await browser.newPage(); await page.goto(origin);
    await page.getByRole('navigation').getByRole('button', { name: 'Backend maintenance', exact: true }).click();
    await page.getByRole('button', { name: 'Load registered assets', exact: true }).click();
    await page.getByLabel('Maintenance asset').selectOption(assetId);
    await page.getByRole('button', { name: 'Load / refresh backend tasks' }).click();
    await page.getByLabel('task pagination').getByText('20 item(s)').waitFor();
    await page.getByLabel('Sample task action', { exact: true }).fill('Sample creation after first task page fills');
    await page.getByRole('button', { name: 'Create backend task', exact: true }).click();
    await page.getByRole('heading', { name: 'Sample creation after first task page fills', exact: true }).waitFor();
    await page.getByText('Recently created task', { exact: false }).waitFor();
    checks.push('Actual backend/browser: task created after a full 20-item page remains visible in its own editor');
    await page.getByRole('button', { name: 'Next task page', exact: true }).click();
    await page.getByLabel('task pagination').getByText('Page 2 · 2 item(s)').waitFor();
    await page.getByRole('heading', { name: 'Sample creation after first task page fills', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Previous task page', exact: true }).click();
    const card = page.locator(`[data-task-id="${historyTask.id}"]`);
    await card.getByRole('button', { name: 'View history' }).click();
    await page.getByLabel('history pagination').getByText('Page 1 · 20 item(s)').waitFor();
    await page.getByRole('button', { name: 'Next history page', exact: true }).click();
    await page.getByLabel('history pagination').getByText('Page 2 · 2 item(s)').waitFor();
    await page.getByText('Version 22: Open → Open', { exact: false }).waitFor();
    checks.push('Actual backend/browser: 22 tasks paginate 20/2 and 22 history events paginate 20/2 without fixtures');
    const result = { assetId, historyTaskId: historyTask.id, checks };
    const directory = process.env.BROWSER_ARTIFACT_DIR || path.join(__dirname, 'browser-results'); fs.mkdirSync(directory, { recursive: true });
    fs.writeFileSync(path.join(directory, 'pagination-checks.json'), JSON.stringify(result, null, 2)); console.log(JSON.stringify(result, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
