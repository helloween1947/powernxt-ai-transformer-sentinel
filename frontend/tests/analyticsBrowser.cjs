// Optional real-browser verification. Requires separately installed Playwright/Chrome.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const origin = process.env.FRONTEND_ORIGIN || 'http://localhost:3000';
  const api = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
  const asset = process.env.DEMO_ASSET_ID;
  const run = process.env.DEMO_RUN_ID;
  assert.ok(asset && run, 'Supply actual DEMO_ASSET_ID and DEMO_RUN_ID from this backend.');
  const output = process.env.BROWSER_ARTIFACT_DIR || path.join(process.cwd(), 'tests/browser-results/analytics');
  fs.mkdirSync(output, {recursive:true});
  const records = [];
  async function get(url) {const response=await fetch(url);assert.equal(response.status,200);return response.json();}
  const history=await get(`${api}/api/v1/assets/${encodeURIComponent(asset)}/telemetry?source=simulator&run_id=${encodeURIComponent(run)}&limit=20&offset=0`);
  const chronological=history.items.sort((a,b)=>Date.parse(a.measurement_time)-Date.parse(b.measurement_time)||a.id-b.id);
  assert.equal(chronological.length,6);
  const results=await Promise.all(chronological.map(r=>get(`${api}/api/v1/telemetry/${r.id}/analytics`)));
  const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const context=await browser.newContext();
  try {
    const page=await context.newPage();
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    const responses=[];page.on('response',response=>{if(response.url().startsWith(api)) responses.push({url:response.url(),status:response.status(),headers:response.headers()});});
    await page.goto(origin);
    await page.getByRole('button',{name:'Backend readings',exact:true}).click();
    await page.getByRole('button',{name:'Load registered transformers'}).click();
    await page.getByLabel('Registered transformer').selectOption(asset);
    const source=page.getByLabel('Telemetry source');
    await source.selectOption('simulator');
    const input=page.getByRole('textbox');await input.fill(run);
    const load=page.getByRole('button',{name:'Load latest reading and history'});
    async function loadAndWait() {
      await load.click();
      await page.getByRole('table',{name:'Thermal history values'}).waitFor();
      await load.waitFor({state:'visible'});
    }
    await loadAndWait();
    const table=page.getByRole('table',{name:'Thermal history values'});
    const rows=table.locator('tbody tr');
    assert.equal(await rows.count(),6);
    for (let i=0;i<6;i++) {
      const cells=await rows.nth(i).locator('td').allTextContents();
      const thermal=results[i].result.payload.thermal_assessment;
      assert.equal(cells[0],`${chronological[i].id} / ${chronological[i].configuration_version}`);
      assert.equal(cells[1],chronological[i].measurement_time);
      assert.equal(cells[2],results[i].result.created_at);
      assert.equal(cells[3],String(chronological[i].normalized_telemetry.measurements.oil_temperature_c));
      assert.equal(cells[4],thermal.predicted_top_oil_temperature_c==null?'Unavailable':String(thermal.predicted_top_oil_temperature_c));
      assert.equal(cells[5],thermal.thermal_residual_c==null?'Unavailable':`${thermal.thermal_residual_c>=0?'+':''}${thermal.thermal_residual_c}`);
      if(i===0) assert.ok(cells[7].includes('initialized_from_measurement_prediction_not_independent'));
      else assert.equal(cells[6],'60');
    }
    assert.equal(await page.locator('[data-series="measured"] circle').count(),6);
    assert.equal(await page.locator('[data-series="predicted"] circle').count(),5);
    assert.equal(await page.locator('[data-series="residual"] circle').count(),5);
    await page.getByText('Parameter provenance',{exact:true}).click();
    assert.ok((await page.locator('body').innerText()).includes('thermal_parameters.oil_time_constant_min: assumed'));
    const assessment=await page.getByRole('region',{name:'Stored analytics',exact:true}).first().innerText();
    assert.ok(assessment.includes('Health index: Unavailable (not_assessed)'));
    assert.ok(assessment.includes('Numerical confidence: Unavailable (not_estimated)'));
    assert.ok(assessment.includes('coverage count, not confidence percentage'));
    assert.ok(assessment.includes('Model measurement source: simulator'));
    assert.ok(responses.some(r=>r.headers['access-control-allow-origin']===origin));
    assert.equal(await page.locator('p[role="alert"]').count(),0);
    await page.screenshot({path:path.join(output,'thermal-desktop.png'),fullPage:true});
    records.push('real API/CORS: six chronological records joined by ID, bootstrap gap, five predictions/residuals, clocks/units/provenance');
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'Page must not overflow viewport; tables may scroll internally.');
    await page.screenshot({path:path.join(output,'thermal-mobile-emulation.png'),fullPage:true});
    records.push('390px responsive emulation; no page-level horizontal overflow (not physical phone)');
    await page.setViewportSize({width:1280,height:900});
    await source.selectOption('device');
    await load.click();await page.getByText('No latest reading exists for this selected stream.',{exact:true}).waitFor();
    assert.equal(await table.locator('tbody tr').count(),0);
    await source.selectOption('file_replay');await input.fill(run);await load.click();
    await page.getByText('No latest reading exists for this selected stream.',{exact:true}).waitFor();
    records.push('real device and file_replay isolation/empty streams; simulator data cleared');
    await source.selectOption('simulator');await input.fill('missing-labelled-demo-run');await load.click();
    await page.getByText('No latest reading exists for this selected stream.',{exact:true}).waitFor();
    records.push('real nonexistent simulator stream: empty, no fabricated results');
    await input.fill(run);
    await context.setOffline(true);await load.click();await page.locator('p[role="alert"]').first().waitFor();
    assert.equal(await page.locator('[data-series="predicted"] circle').count(),0);
    await context.setOffline(false);await loadAndWait();assert.equal(await rows.count(),6);
    records.push('browser network-offline failure and manual recovery against real backend');
    // Delayed actual API response, not an invented payload, exercises cancellation in the UI.
    let release, intercepted;
    const arrived=new Promise(resolve=>intercepted=resolve);
    const held=new Promise(resolve=>release=resolve);
    await page.route('**/api/v1/assets/*/telemetry?*',async route=>{
      const response=await route.fetch();intercepted();await held;
      try {await route.fulfill({response});} catch { /* Request may already be cancelled. */ }
    });
    await load.click();await arrived;await source.selectOption('device');release();
    await page.unroute('**/api/v1/assets/*/telemetry?*');
    await load.click();await page.getByText('No latest reading exists for this selected stream.',{exact:true}).waitFor();
    assert.equal(await page.locator('[data-series="predicted"] circle').count(),0);
    records.push('stream change during delayed real response: cancelled old data cannot populate device view');
    if (process.env.COEFFICIENT_FREE_RUN_ID) {
      await source.selectOption('simulator');await input.fill(process.env.COEFFICIENT_FREE_RUN_ID);await loadAndWait();
      assert.equal(await rows.count(),6);
      assert.equal(await page.locator('[data-series="predicted"] circle').count(),0);
      const text=await table.innerText();
      for (const parameter of ['rated_top_oil_rise_c','oil_time_constant_min','loss_ratio','oil_exponent']) assert.ok(text.includes(parameter));
      records.push('real completed coefficient-free configuration: electrical evidence retained, thermal gaps with four missing-parameter reasons');
      await page.screenshot({path:path.join(output,'coefficient-free.png'),fullPage:true});
    }
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(output,'verification.json'),JSON.stringify({timestamp:new Date().toISOString(),origin,api,asset,run,readings:chronological.map(r=>r.id),actualAPI:true,fixtureResponses:false,checks:records,pageErrors:errors,passed:true},null,2));
    console.log(JSON.stringify({passed:true,checks:records,evidence:output},null,2));
  } finally {await context.close();await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
