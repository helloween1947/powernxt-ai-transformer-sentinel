// Read-only Chrome pagination and historical evidence on the extended QA stream.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const dir = process.env.REVIEW_EVIDENCE;
const seed = JSON.parse(fs.readFileSync(path.join(dir, 'seed.json')));
const result = { scope: 'Actual Chrome, persisted synthetic worker stream', checks: [] };
const wait = ms => new Promise(r => setTimeout(r, ms));
async function until(fn) { for (let i = 0; i < 200; i++) { if (await fn()) return; await wait(100); } throw Error('Expected persisted page not displayed'); }
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const button = name => p.getByRole('button', { name, exact: true });
  try {
    await p.goto('http://127.0.0.1:15882');
    await until(() => p.locator('select[aria-label="Selected transformer"] option').count().then(n => n > 1));
    await p.locator('select[aria-label="Selected transformer"]').selectOption(seed.asset_id);
    await p.getByLabel('Telemetry source').selectOption('simulator');
    await p.getByLabel('Run ID', { exact: true }).fill(seed.run_id); await button('Apply run').click();
    await p.getByLabel('Operator Bearer Token').fill(fs.readFileSync(path.join(dir, 'private/admin.txt'), 'utf8').trim());
    await button('Authenticate').click(); await until(() => button('Disconnect').isVisible());
    await button('Trends & history').click();
    await until(() => p.locator('.evidence-records button').count().then(n => n === 20));
    await p.locator('.evidence-records button').last().click();
    await until(() => p.getByRole('heading', { name: /^Historical reading / }).isVisible());
    assert.ok(await p.getByRole('button', { name: /^Return to latest$/ }).isVisible());
    await button('Return to latest').click();
    await button('Next page').click();
    await until(() => p.locator('.evidence-records button').count().then(n => n === 5));
    await button('Previous').click();
    await until(() => p.locator('.evidence-records button').count().then(n => n === 20));
    result.checks.push('stored history pagination20/5 and exact historical reading inspection/return');
    await button('Alerts & incidents').click(); await button('Query stream incidents').click();
    await until(() => button('Inspect').first().isVisible());
    await p.locator('tr').filter({ hasText: seed.incident_ids[0].slice(0, 8) }).getByRole('button', { name: 'Inspect', exact: true }).click();
    for (const kind of ['events', 'evidence']) {
      await until(() => button(`Next ${kind} page`).isEnabled());
      const response = p.waitForResponse(r => r.url().includes('/' + kind + '?') && r.request().method() === 'GET');
      await button(`Next ${kind} page`).click();
      const r = await response; assert.equal(r.status(), 200);
      const body = await r.json(); assert.ok(body.items.length > 0);
      await until(() => button(`Previous ${kind} page`).isEnabled());
      await button(`Previous ${kind} page`).click();
      await until(() => button(`Previous ${kind} page`).isDisabled());
      result.checks.push(`actual ${kind} cursor pagination beyond20 persisted records`);
    }
    result.status = 'PASS'; console.log('PASS actual Chrome historical/event/evidence pagination');
  } catch (e) { result.status = 'FAIL'; result.failure = e.message; console.error(e.message); process.exitCode = 1; }
  finally { fs.writeFileSync(path.join(dir, 'chrome-pagination.json'), JSON.stringify(result, null, 2) + '\n'); await browser.close(); }
})();
