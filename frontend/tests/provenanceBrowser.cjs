/* Optional isolated GET-only Chrome check. Requires external Playwright and
   FRONTEND_ORIGIN, BACKEND_URL, DEMO_ASSET_ID, DEMO_RUN_ID, BROWSER_ARTIFACT_DIR.
   All mutated responses below are labelled fixtures, never backend defects. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { FRONTEND_ORIGIN: origin, BACKEND_URL: base, DEMO_ASSET_ID: asset, DEMO_RUN_ID: run, BROWSER_ARTIFACT_DIR: dir } = process.env;
if (![origin, base, asset, run, dir].every(Boolean)) throw new Error('Provide the isolated preview and existing thermal stream identifiers.');
const results = { origin, base, asset, run, realChecks: [], fixtureChecks: [], apiBodies: [] };

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_EXECUTABLE || 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
  try {
    const page = await browser.newPage();
    const pending = [];
    let captureReal = true;
    page.on('request', r => { if (r.url().includes('/api/v1/')) assert.equal(r.method(), 'GET'); });
    page.on('response', r => {
      if (captureReal && r.url().includes('/api/v1/') && r.ok()) pending.push((async () => {
        const body = await r.json();
        const file = `real-api-${results.apiBodies.length}.json`;
        results.apiBodies.push({ url: r.url(), file, body });
        fs.writeFileSync(path.join(dir, file), JSON.stringify(body, null, 2));
      })());
    });
    await page.goto(origin);
    await page.getByRole('button', { name: 'Backend readings', exact: true }).click();
    await page.getByRole('button', { name: 'Load registered transformers', exact: true }).click();
    await page.getByLabel('Registered transformer').selectOption(asset);
    await page.getByLabel('Telemetry source').selectOption('simulator');
    await page.getByRole('textbox').fill(run);
    const load = page.getByRole('button', { name: 'Load latest reading and history', exact: true });
    const table = page.getByRole('table', { name: 'Thermal history values' });
    async function reload() {
      await load.click();
      await table.waitFor();
      await page.getByText('Loading stored stream…', { exact: true }).waitFor({ state: 'hidden' });
    }
    await reload();
    await Promise.all(pending);
    assert.equal(await page.getByRole('alert').count(), 0);
    const readings = results.apiBodies.filter(x => /\/telemetry\/\d+\/analytics$/.test(new URL(x.url).pathname)).map(x => x.body).sort((a, b) => Date.parse(a.measurement_time) - Date.parse(b.measurement_time));
    assert.equal(readings.length, 6, 'Use the documented retained six-reading thermal stream.');
    const rows = table.locator('tbody tr');
    for (const [i, wire] of readings.entries()) {
      assert.equal(wire.asset_id, asset); assert.equal(wire.source, 'simulator'); assert.equal(wire.run_id, run);
      const meta = wire.result.payload.metadata;
      for (const field of ['model_id', 'model_version', 'parameter_version']) {
        assert.ok(wire.result[field]?.trim()); assert.equal(meta[field], wire.result[field]);
      }
      assert.equal(meta.reading_identity.reading_id, wire.reading_id);
      assert.equal(meta.configuration_version, wire.configuration_version);
      assert.equal(meta.measurement_time, wire.measurement_time);
      assert.equal(meta.units.oil_temperature, 'C'); assert.equal(meta.units.thermal_residual, 'C');
      const cells = await rows.nth(i).locator('td').allTextContents();
      const thermal = wire.result.payload.thermal_assessment;
      assert.equal(cells[0], `${wire.reading_id} / ${wire.configuration_version}`);
      assert.equal(cells[1], wire.measurement_time);
      assert.equal(Number(cells[3]), thermal.measured_top_oil_temperature_c);
      assert.equal(cells[4], thermal.predicted_top_oil_temperature_c == null ? 'Unavailable' : String(thermal.predicted_top_oil_temperature_c));
      assert.equal(cells[5], thermal.thermal_residual_c == null ? 'Unavailable' : `${thermal.thermal_residual_c >= 0 ? '+' : ''}${thermal.thermal_residual_c}`);
    }
    assert.equal(readings[0].result.payload.thermal_assessment.predicted_top_oil_temperature_c, null);
    assert.equal(readings[0].result.payload.thermal_assessment.thermal_residual_c, null);
    const latest = results.apiBodies.find(x => new URL(x.url).pathname.endsWith('/analytics/latest')).body;
    for (const field of ['model_id', 'model_version', 'parameter_version']) assert.equal(latest.result[field], latest.result.payload.metadata[field]);
    results.realChecks.push('Actual browser network responses: six ID-joined chronological rows, exact numeric values/sign, bootstrap nulls, C units and both endpoint provenance identities');
    await page.screenshot({ path: path.join(dir, 'valid-response.png'), fullPage: true });
    captureReal = false;
    const perReading = '**/api/v1/telemetry/*/analytics';
    const latestRoute = '**/api/v1/assets/*/analytics/latest?*';
    for (const endpoint of [perReading, latestRoute]) {
      for (const kind of ['contradictory', 'missing-metadata', 'blank-outer']) {
        await page.route(endpoint, async route => {
          const real = await route.fetch(); const wire = await real.json();
          if (kind === 'contradictory') wire.result.payload.metadata.model_version = 'labelled-contradictory-fixture';
          if (kind === 'missing-metadata') delete wire.result.payload.metadata.parameter_version;
          if (kind === 'blank-outer') wire.result.model_id = wire.result.payload.metadata.model_id = ' \t ';
          await route.fulfill({ response: real, json: wire });
        });
        await reload();
        await page.getByRole('alert').filter({ hasText: 'model or parameter identity' }).first().waitFor();
        await page.getByRole('heading', { name: 'Latest stored reading', exact: true }).waitFor();
        assert.equal(await rows.count(), 6);
        if (endpoint === perReading) {
          assert.equal(await page.getByLabel('Stored analytics').count(), 0);
          for (let i = 0; i < 6; i++) {
            const cells = await rows.nth(i).locator('td').allTextContents();
            assert.notEqual(cells[3], 'Unavailable'); assert.equal(cells[4], 'Unavailable'); assert.equal(cells[5], 'Unavailable');
          }
        } else {
          assert.equal(await page.getByText('Completed model:', { exact: false }).count(), 0);
          await page.getByText('Latest completed analytics could not be retrieved; see the request error.', { exact: true }).waitFor();
        }
        results.fixtureChecks.push(`${endpoint}: ${kind} fixture clears rejected/stale analytics; independent valid telemetry retained`);
        await page.screenshot({ path: path.join(dir, `fixture-${endpoint === perReading ? 'reading' : 'latest'}-${kind}.png`), fullPage: true });
        await page.unroute(endpoint);
        await reload(); assert.equal(await page.getByRole('alert').count(), 0);
      }
    }
    for (const endpoint of [perReading, latestRoute]) await page.route(endpoint, async route => {
      const real = await route.fetch(); const wire = await real.json();
      wire.result.model_version = wire.result.payload.metadata.model_version = 'labelled-matching-future-fixture';
      await route.fulfill({ response: real, json: wire });
    });
    await reload(); assert.equal(await page.getByRole('alert').count(), 0);
    await page.getByText('labelled-matching-future-fixture', { exact: false }).first().waitFor();
    results.fixtureChecks.push('Matching future-version fixture accepted on both endpoints without a 1.0.1 pin');
    for (const endpoint of [perReading, latestRoute]) await page.unroute(endpoint);
    for (const endpoint of [perReading, latestRoute]) await page.route(endpoint, async route => {
      const real = await route.fetch(); const wire = await real.json(); wire.result = null;
      if (endpoint === perReading) wire.status = 'pending';
      else Object.assign(wire, { latest_telemetry_status: 'pending', latest_completed_reading_id: null, latest_completed_measurement_time: null });
      await route.fulfill({ response: real, json: wire });
    });
    await reload(); assert.equal(await page.getByRole('alert').count(), 0);
    await page.getByText('No stored analytical result for this reading.', { exact: false }).waitFor();
    results.fixtureChecks.push('Labelled pending/null-result fixtures retain telemetry, show unavailable analytics and do not fabricate results');
    // Clear selection to stop the pending fixture's bounded polling before restoring real routes.
    await page.getByRole('textbox').fill(run + '-fixture-stop');
    for (const endpoint of [perReading, latestRoute]) await page.unroute(endpoint);
    await page.getByRole('textbox').fill(run); await reload();
    assert.equal(await page.getByRole('alert').count(), 0);
    results.realChecks.push('Returning to actual API after fixtures restores legitimate stored results');
    const manifest = { ...results, apiBodies: results.apiBodies.map(({ body, ...entry }) => entry), passed: true, recordedUtc: new Date().toISOString() };
    fs.writeFileSync(path.join(dir, 'provenance-browser.json'), JSON.stringify(manifest, null, 2));
    console.log(JSON.stringify({ passed: true, realChecks: results.realChecks, fixtureChecks: results.fixtureChecks }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
