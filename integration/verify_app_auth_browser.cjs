const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const dir = process.env.REVIEW_EVIDENCE;
const seed = JSON.parse(fs.readFileSync(path.join(dir, 'seed.json')));
const result = { scope: 'Actual Chrome; isolated API responses and owned credentials only', checks: [] };
const delay = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, message) { for (let n = 0; n < 200; n++) { if (await fn()) return; await delay(100); } throw Error(message); }
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const btn = name => p.getByRole('button', { name, exact: true });
  const change = action => {
    const r = spawnSync(process.env.REVIEW_PYTHON, ['-m', 'integration.review_credential_state', '--database-url', process.env.DATABASE_URL, '--action', action], { encoding: 'utf8' });
    assert.equal(r.status, 0, r.stderr);
  };
  const login = async role => {
    if (await btn('Disconnect').isVisible().catch(() => false)) await btn('Disconnect').click();
    await p.getByLabel('Operator Bearer Token').fill(fs.readFileSync(path.join(dir, 'private', role + '.txt'), 'utf8').trim());
    await btn('Authenticate').click(); await until(() => btn('Disconnect').isVisible(), 'Login failed');
  };
  try {
    await p.goto('http://127.0.0.1:15882');
    await until(() => p.locator('select[aria-label="Selected transformer"] option').count().then(n => n > 1), 'Registry missing');
    await p.locator('select[aria-label="Selected transformer"]').selectOption(seed.asset_id);
    await p.getByLabel('Telemetry source').selectOption('simulator');
    await p.getByLabel('Run ID', { exact: true }).fill(seed.run_id); await btn('Apply run').click();
    await p.getByLabel('Operator Bearer Token').fill('invalid-labelled-qa-credential');
    await btn('Authenticate').click();
    await until(() => p.locator('[role="alert"]').count().then(n => n > 0), 'Invalid authentication error missing');
    assert.equal(await btn('Disconnect').isVisible(), false);
    result.checks.push('invalid credential rejected by actual operators/me API');
    await login('operator');
    await btn('What-if analysis').click();
    await p.getByLabel('Initial state reference (UUID)').fill(crypto.randomUUID());
    await btn('Compute What-if forecast').click();
    await until(() => p.getByText('state_not_found', { exact: true }).isVisible().catch(() => false), 'Actual unknown-snapshot API error missing');
    assert.equal(await p.getByText('Captured state reference', { exact: false }).isVisible(), false);
    result.checks.push('actual404 snapshot error visible; prior forecast absent');
    change('reader-expires-soon'); await login('reader');
    await until(() => p.getByText('Credential expired or was revoked.', { exact: false }).isVisible(), 'Expiry did not clear session');
    assert.equal(await btn('Disconnect').isVisible(), false);
    result.checks.push('actual server expiry timestamp clears local session and requires reauthentication');
    await login('operator'); await btn('Alerts & incidents').click(); await btn('Query stream incidents').click();
    await until(() => btn('Inspect').first().isVisible(), 'Incidents missing');
    change('operator-revoke'); await btn('Query stream incidents').click();
    await until(() => p.getByText('Credential expired or was revoked.', { exact: false }).isVisible(), 'Revocation401 not handled');
    assert.equal(await btn('Disconnect').isVisible(), false);
    assert.ok(await btn('Query stream incidents').isDisabled());
    result.checks.push('actual revoked-credential401 clears session and disables incident query');
    result.status = 'PASS'; console.log('PASS actual Chrome credential/error checks');
  } catch (e) { result.status = 'FAIL'; result.failure = e.message; result.alerts = await p.locator('[role="alert"]').allTextContents(); console.error(e.message); process.exitCode = 1; }
  finally { fs.writeFileSync(path.join(dir, 'chrome-auth.json'), JSON.stringify(result, null, 2) + '\n'); await browser.close(); }
})();
