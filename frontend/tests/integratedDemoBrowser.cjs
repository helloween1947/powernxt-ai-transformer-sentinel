// Optional Windows Chrome checks. Every altered response is labelled injection evidence.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const origin = process.env.FRONTEND_ORIGIN || 'http://localhost:3000';
  const api = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
  const asset = process.env.DEMO_ASSET_ID;
  const run = process.env.DEMO_RUN_ID;
  assert.ok(asset && run, 'Set DEMO_ASSET_ID and DEMO_RUN_ID from this backend.');
  const output = process.env.BROWSER_ARTIFACT_DIR || path.join(__dirname, 'browser-results/integrated');
  fs.mkdirSync(output, {recursive:true});
  const get = async route => {
    const response = await fetch(api + route);
    assert.equal(response.status, 200);
    return response.json();
  };
  const history = await get(`/api/v1/assets/${asset}/telemetry?source=simulator&run_id=${run}&limit=100`);
  const readings = history.items.sort((a,b) => Date.parse(a.measurement_time)-Date.parse(b.measurement_time)||a.id-b.id);
  assert.equal(readings.length, 6);
  const last = readings.at(-1);
  const previous = readings.at(-2);
  const lastAnalytics = await get(`/api/v1/telemetry/${last.id}/analytics`);
  const previousAnalytics = await get(`/api/v1/telemetry/${previous.id}/analytics`);
  const browser = await chromium.launch({executablePath:process.env.BROWSER_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const context = await browser.newContext({viewport:{width:1440,height:1000}});
  const checks = [];
  try {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin);
    await page.getByRole('button',{name:'Backend readings',exact:true}).click();
    await page.getByRole('button',{name:'Load registered transformers'}).click();
    await page.getByLabel('Registered transformer').selectOption(asset);
    const source = page.getByLabel('Telemetry source');
    const runInput = page.getByLabel('Run ID', {exact:true});
    const load = page.getByRole('button',{name:'Load latest reading and history'});
    const table = page.getByRole('table',{name:'Thermal history values'});
    await source.selectOption('simulator');
    await runInput.fill(run);
    async function loadAndWait() {
      await load.click();
      await table.locator('tbody tr').nth(5).waitFor();
      await page.getByText('Last successful API retrieval (UTC):', {exact:false}).waitFor();
    }
    await loadAndWait();
    const electrical = page.getByRole('region',{name:'Stored analytics'});
    for (const [label,key] of [['Capacity loading','capacity_loading_pct'],['Worst-phase loading','max_phase_loading_pct'],['Apparent power','apparent_power_kva'],['Thermal load','thermal_load_pu']]) {
      const row = electrical.getByRole('row').filter({has:page.getByRole('cell',{name:label,exact:true})});
      assert.equal(await row.locator('td').nth(1).innerText(), String(lastAnalytics.result.payload.electrical_metrics[key]));
    }
    assert.ok((await electrical.innerText()).includes(lastAnalytics.result.model_version));
    assert.ok((await page.locator('body').innerText()).includes('Connectivity and processing status do not make historical measurement timestamps current.'));
    assert.equal(await page.getByRole('button',{name:'Next history page',exact:true}).isDisabled(),true);
    await page.getByRole('region',{name:'Stored thermal comparison'}).screenshot({path:path.join(output,'thermal-comparison-detail.png')});
    checks.push('real backend: exact electrical values/model, January historical label, six-reading page controls and thermal charts');
    await page.reload();
    await page.getByRole('button',{name:'Backend readings',exact:true}).click();
    await page.getByRole('button',{name:'Load registered transformers'}).click();
    await page.getByLabel('Registered transformer').selectOption(asset);
    await source.selectOption('simulator'); await runInput.fill(run); await loadAndWait();
    checks.push('real backend: reload and reselect preserves the same six stored records');

    // Inject an HTTP 503 for analytics only; other responses still come from the real API.
    await page.route(`${api}/api/v1/telemetry/*/analytics`, route => route.fulfill({status:503,json:{detail:'Labelled browser-verification failure injection'}}));
    await loadAndWait();
    await page.getByRole('alert').filter({hasText:'503'}).first().waitFor();
    assert.equal(await table.locator('tbody tr').count(),6);
    assert.equal(await page.locator('[data-series="predicted"] circle').count(),0);
    assert.ok((await page.locator('body').innerText()).includes('Latest stored reading'));
    await page.unroute(`${api}/api/v1/telemetry/*/analytics`);
    await loadAndWait();
    assert.equal(await page.locator('[data-series="predicted"] circle').count(),5);
    checks.push('labelled HTTP503 injection: real telemetry remains visible, predictions unavailable; manual recovery restores actual results');

    // Labelled processing-state injection changes presentation only, never the DB/worker.
    let polls=0;
    await page.route(`${api}/api/v1/assets/${asset}/analytics/latest?*`, async route => {
      polls++;
      const response=await route.fetch();
      const body=await response.json();
      body.latest_telemetry_status='pending';
      body.latest_completed_reading_id=previous.id;
      body.latest_completed_measurement_time=previous.measurement_time;
      body.result=previousAnalytics.result;
      await route.fulfill({response,json:body});
    });
    await page.route(`${api}/api/v1/telemetry/${last.id}/analytics`, async route => {
      const response=await route.fetch();
      const body=await response.json();
      body.status='pending'; body.result=null;
      await route.fulfill({response,json:body});
    });
    await loadAndWait();
    await page.getByText('Processing lag or unavailable newest result:',{exact:false}).waitFor();
    await page.getByText('Latest completed analytics — separate stored reading',{exact:true}).waitFor();
    assert.equal(await table.locator('tbody tr').last().locator('td').nth(4).innerText(),'Unavailable');
    await page.getByText('Polling limit reached.',{exact:false}).waitFor({timeout:45000});
    assert.equal(polls,7,'One initial request plus exactly six bounded refreshes');
    await page.waitForTimeout(5500);
    assert.equal(polls,7,'No further polling after exhaustion');
    await page.screenshot({path:path.join(output,'injected-processing-lag-limit.png'),fullPage:true});
    checks.push('labelled pending/lag injection: latest telemetry separate from older completed result; exactly six 5-second refreshes, then stops');
    await source.selectOption('device');
    await page.unroute(`${api}/api/v1/assets/${asset}/analytics/latest?*`);
    await page.unroute(`${api}/api/v1/telemetry/${last.id}/analytics`);
    await source.selectOption('simulator'); await runInput.fill(run); await loadAndWait();
    assert.equal(await page.locator('[data-series="predicted"] circle').count(),5);
    assert.equal(await page.getByText('Processing lag or unavailable newest result:',{exact:false}).count(),0);
    checks.push('real backend restored after injection; terminal completed data does not poll');
    assert.deepEqual(errors,[]);
    const evidence={passed:true,timestamp:new Date().toISOString(),origin,api,asset,run,readings:readings.map(r=>r.id),checks,injectionUsed:true,processingInjectionPollRequests:polls,pageErrors:errors};
    fs.writeFileSync(path.join(output,'extended-browser-verification.json'),JSON.stringify(evidence,null,2));
    console.log(JSON.stringify(evidence,null,2));
  } finally {await context.close();await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
