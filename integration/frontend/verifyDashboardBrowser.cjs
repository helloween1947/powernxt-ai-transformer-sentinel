// Development browser check. Requires Playwright plus a reachable combined C+D dashboard.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs');

const dashboard = process.env.MAINTENANCE_DASHBOARD_URL || 'http://127.0.0.1:5173';
const api = process.env.MAINTENANCE_API_URL || 'http://127.0.0.1:8000';
const resultPath = process.env.MAINTENANCE_RESULT_PATH || '.venv/dashboard-browser-result.json';
const mode = process.argv[2] || '--workflow';
const cardFor = (page, title) => page.locator('article.task').filter({ has: page.getByRole('heading', { name: title, exact: true }) });

async function taskApi(id, body) {
  const response = await fetch(`${api}/api/v1/maintenance/tasks/${id}`, body ? {
    method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-Demo-Actor': 'Competing demo operator' },
    body: JSON.stringify(body),
  } : undefined);
  assert.equal(response.status, 200);
  return response.json();
}

async function openTasks(page) {
  await page.goto(dashboard);
  await page.getByRole('button', { name: 'Backend maintenance', exact: true }).click();
  await page.getByRole('button', { name: 'Load registered assets', exact: true }).click();
  await page.getByLabel('Maintenance asset', { exact: true }).selectOption('sample-transformer-d');
  await page.getByRole('button', { name: 'Load backend tasks', exact: true }).click();
}

async function waitSaved(card, text) {
  await card.getByText(text, { exact: true }).waitFor();
}

(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.MAINTENANCE_BROWSER_PATH ? { executablePath: process.env.MAINTENANCE_BROWSER_PATH } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    if (mode === '--offline') {
      await page.goto(dashboard);
      await page.getByRole('button', { name: 'Backend maintenance', exact: true }).click();
      await page.getByRole('button', { name: 'Load registered assets', exact: true }).click();
      await page.getByRole('alert').filter({ hasText: /fetch|network/i }).waitFor();
      assert.equal(await page.getByRole('button', { name: 'Create backend task' }).isDisabled(), true);
      console.log('PASS: actual stopped-backend failure is visible; no fallback fixture task is created.');
    } else if (mode === '--saved') {
      const saved = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
      await openTasks(page);
      const card = cardFor(page, saved.title);
      await waitSaved(card, 'Saved: Completed · Owner: Browser maintainer · Version: 4');
      assert.equal(await card.getByRole('button', { name: 'Save task update' }).isDisabled(), true);
      await card.getByRole('button', { name: 'View history' }).click();
      await page.getByRole('heading', { name: `History for ${saved.taskId}`, exact: true }).waitFor();
      await page.getByText('Version 4: in_progress → completed', { exact: true }).waitFor();
      console.log('PASS: browser retrieved completed task and history after backend restart.');
    } else {
      await openTasks(page);
      await page.getByLabel('Demo actor', { exact: true }).fill('Browser check demo operator');
      const title = `Browser sample inspection ${randomUUID().slice(0, 8)}`;
      await page.getByLabel('Sample task action', { exact: true }).fill(title);
      await page.getByRole('button', { name: 'Create backend task' }).click();
      const card = cardFor(page, title);
      await waitSaved(card, 'Saved: Open · Owner: Unassigned · Version: 1');
      const taskId = await card.getAttribute('data-task-id');
      await card.getByLabel('Assigned person', { exact: true }).fill('Browser maintainer');
      await card.getByRole('button', { name: 'Save task update' }).click();
      await waitSaved(card, 'Saved: Open · Owner: Browser maintainer · Version: 2');
      await card.getByLabel('Task status', { exact: true }).selectOption('In progress');
      await card.getByLabel('Task notes', { exact: true }).fill('Browser inspection started');
      await card.getByRole('button', { name: 'Save task update' }).click();
      await waitSaved(card, 'Saved: In progress · Owner: Browser maintainer · Version: 3');
      await card.getByLabel('Task status', { exact: true }).selectOption('Completed');
      await card.getByLabel('Task notes', { exact: true }).fill('');
      await card.getByRole('button', { name: 'Save task update' }).click();
      await card.getByRole('alert').filter({ hasText: 'Completion requires notes' }).waitFor();
      assert.equal((await taskApi(taskId)).version, 3);
      await card.getByLabel('Task notes', { exact: true }).fill('Browser inspection completed');
      await card.getByRole('button', { name: 'Save task update' }).click();
      await waitSaved(card, 'Saved: Completed · Owner: Browser maintainer · Version: 4');
      assert.equal(await card.getByRole('button', { name: 'Save task update' }).isDisabled(), true);
      await card.getByRole('button', { name: 'View history' }).click();
      await page.getByText('Version 4: in_progress → completed', { exact: true }).waitFor();
      await openTasks(page); // A full navigation proves browser-refresh persistence.
      await waitSaved(cardFor(page, title), 'Saved: Completed · Owner: Browser maintainer · Version: 4');

      const conflictTitle = `Browser conflict inspection ${randomUUID().slice(0, 8)}`;
      await page.getByLabel('Sample task action', { exact: true }).fill(conflictTitle);
      await page.getByLabel('Initial assigned person', { exact: true }).fill('Original demo owner');
      await page.getByRole('button', { name: 'Create backend task' }).click();
      const conflictCard = cardFor(page, conflictTitle);
      await waitSaved(conflictCard, 'Saved: Open · Owner: Original demo owner · Version: 1');
      const conflictId = await conflictCard.getAttribute('data-task-id');
      await conflictCard.getByLabel('Task notes', { exact: true }).fill('Operator draft retained');
      await taskApi(conflictId, { expected_version: 1, owner: 'Competing demo owner', notes: 'Competing server note' });
      await conflictCard.getByRole('button', { name: 'Save task update' }).click();
      await conflictCard.getByRole('alert').filter({ hasText: 'Latest task loaded' }).waitFor();
      await waitSaved(conflictCard, 'Saved: Open · Owner: Competing demo owner · Version: 2');
      assert.equal(await conflictCard.getByLabel('Task notes', { exact: true }).inputValue(), 'Operator draft retained');
      assert.equal(await conflictCard.getByRole('button', { name: 'Save task update' }).isDisabled(), true);
      assert.equal((await taskApi(conflictId)).notes, 'Competing server note');
      await conflictCard.getByRole('button', { name: 'I reviewed the latest task; enable saving my draft' }).click();
      await conflictCard.getByRole('button', { name: 'Save task update' }).click();
      await waitSaved(conflictCard, 'Saved: Open · Owner: Original demo owner · Version: 3');
      assert.equal((await taskApi(conflictId)).notes, 'Operator draft retained');
      fs.writeFileSync(resultPath, JSON.stringify({ taskId, title, conflictId }, null, 2));
      console.log('PASS: actual browser creation, assignment, start, required completion notes, history, refresh and reviewed conflict recovery.');
      console.log(JSON.stringify({ taskId, title, conflictId }));
    }
    assert.deepEqual(pageErrors, []);
    await page.screenshot({ path: '.venv/dashboard-browser.png', fullPage: true });
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });

