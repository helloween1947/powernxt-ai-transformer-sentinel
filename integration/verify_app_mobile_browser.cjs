// Read-only settled mobile screenshot; no credentials or task mutations.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const dir = process.env.REVIEW_EVIDENCE;
const seed = JSON.parse(fs.readFileSync(path.join(dir, 'final-browser/seed.json')));
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  try {
    await p.goto('http://127.0.0.1:15882/#maintenance');
    await p.locator('select[aria-label="Selected transformer"] option').nth(1).waitFor({ state: 'attached' });
    await p.locator('select[aria-label="Selected transformer"]').selectOption(seed.asset_id);
    await p.getByLabel('Telemetry source').selectOption('simulator');
    await p.getByLabel('Run ID', { exact: true }).fill(seed.run_id);
    await p.getByRole('button', { name: 'Apply run', exact: true }).click();
    await p.getByRole('button', { name: 'Load / refresh sample tasks', exact: true }).click();
    await p.locator('[data-task-id]').first().waitFor();
    await p.getByRole('button', { name: 'Open navigation', exact: true }).click();
    await p.getByRole('dialog').getByRole('button', { name: 'Fleet overview', exact: true }).click();
    await p.getByRole('heading', { name: 'Backend maintenance', exact: true }).waitFor({ state: 'detached' });
    await p.waitForTimeout(500);
    assert.equal(await p.getByRole('dialog').count(), 0);
    assert.equal(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2), false);
    await p.screenshot({ path: path.join(dir, 'final-browser/chrome-mobile.png'), fullPage: true });
    fs.writeFileSync(path.join(dir, 'chrome-mobile.json'), JSON.stringify({ status: 'PASS', scope: 'Actual anonymous Chrome390x844; read-only persisted sample tasks to fleet navigation', checks: ['previous view fully detached before screenshot', 'drawer closed', 'no horizontal overflow including authentication form'] }, null, 2) + '\n');
    console.log('PASS settled actual mobile Chrome navigation and anonymous auth layout');
  } finally { await browser.close(); }
})().catch(e => { console.error(e.message); process.exitCode = 1; });
