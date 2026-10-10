/* Optional isolated Chrome verification. Actual responses and injected fixtures
   are recorded separately. MODEL_STREAMS_FILE supplies real asset/run/reading IDs. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { FRONTEND_ORIGIN: origin, BROWSER_ARTIFACT_DIR: dir, MODEL_STREAMS_FILE: streamFile } = process.env;
const streams = JSON.parse(fs.readFileSync(streamFile)).streams;

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_EXECUTABLE || 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
  const evidence = { actual: [], fixtures: [] };
  try {
    const page = await browser.newPage();
    let capture = true; const bodies = []; const pending = [];
    page.on('response', response => {
      if (capture && response.url().includes('/api/v1/') && response.ok()) pending.push((async () => {
        const body = await response.json(); const file = `actual-network-${bodies.length}.json`;
        bodies.push({ url: response.url(), body, file });
        fs.writeFileSync(path.join(dir, file), JSON.stringify(body, null, 2));
      })());
    });
    await page.goto(origin);
    await page.getByRole('button', {name:'Backend readings',exact:true}).click();
    const load = page.getByRole('button', {name:'Load latest reading and history',exact:true});
    const table = page.getByRole('table', {name:'Thermal history values'});
    async function reload() {
      await load.click(); await table.waitFor();
      await page.getByText('Loading backend data… Stream controls remain available; changing a filter cancels this request.',{exact:true}).waitFor({state:'hidden'});
    }
    for (const [kind, stream] of Object.entries(streams)) {
      await Promise.all([
        page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/assets' && new URL(r.url()).searchParams.get('offset')==='0'),
        page.getByRole('button',{name:'Load registered transformers',exact:true}).click(),
      ]);
      await page.getByText('Loading asset registry…',{exact:true}).waitFor({state:'hidden'});
      await page.getByText('Asset page: 1.',{exact:false}).waitFor();
      let assetPage=1;
      while (!await page.getByLabel('Registered transformer').locator(`option[value="${stream.asset}"]`).count()) {
        await page.getByRole('button',{name:'Next asset page',exact:true}).click();
        await page.getByText('Loading asset registry…',{exact:true}).waitFor({state:'hidden'});
        await page.getByText(`Asset page: ${++assetPage}.`,{exact:false}).waitFor();
      }
      await page.getByLabel('Registered transformer').selectOption(stream.asset);
      await page.getByLabel('Telemetry source').selectOption('simulator');
      await page.getByRole('textbox').fill(stream.run); await reload(); await Promise.all(pending);
      assert.equal(await page.getByRole('alert').count(),0);
      const wires=stream.readings.map(id=>bodies.find(x=>new URL(x.url).pathname===`/api/v1/telemetry/${id}/analytics`).body);
      const rows=table.locator('tbody tr'); assert.equal(await rows.count(),wires.length);
      for (const [i,wire] of wires.entries()) {
        for (const field of ['model_id','model_version','parameter_version']) {
          assert.ok(wire.result[field]?.trim()); assert.equal(wire.result[field],wire.result.payload.metadata[field]);
        }
        assert.equal(wire.result.model_version,stream.modelVersion);
        const thermal=wire.result.payload.thermal_assessment; const cells=await rows.nth(i).locator('td').allTextContents();
        assert.equal(cells[0],`${wire.reading_id} / ${wire.configuration_version}`);
        assert.equal(cells[1],wire.measurement_time);
        assert.equal(Number(cells[3]),thermal.measured_top_oil_temperature_c);
        assert.equal(cells[4],thermal.predicted_top_oil_temperature_c==null?'Unavailable':String(thermal.predicted_top_oil_temperature_c));
        assert.equal(cells[5],thermal.thermal_residual_c==null?'Unavailable':`${thermal.thermal_residual_c>=0?'+':''}${thermal.thermal_residual_c}`);
      }
      const section=page.getByLabel('Stored analytics').first();
      const current=wires.at(-1).result;
      const latest=bodies.find(x=>new URL(x.url).pathname===`/api/v1/assets/${stream.asset}/analytics/latest` && new URL(x.url).searchParams.get('run_id')===stream.run).body;
      if(latest.result) {
        for(const field of ['model_id','model_version','parameter_version']) assert.equal(latest.result[field],latest.result.payload.metadata[field]);
        assert.equal(latest.result.model_version,stream.modelVersion);
        assert.equal(latest.result.reading_id,wires.at(-1).reading_id);
      } else {
        assert.equal(kind,'extreme-current'); assert.equal(latest.latest_completed_reading_id,null);
        assert.equal(latest.latest_telemetry_status,'unavailable');
      }
      assert.ok((await section.textContent()).includes(current.model_version));
      assert.ok((await section.textContent()).includes(current.parameter_version));
      if(kind==='normal'||kind==='historical') {
        assert.equal(wires[0].result.payload.thermal_assessment.predicted_top_oil_temperature_c,null);
        assert.ok(Number.isFinite(wires.at(-1).result.payload.thermal_assessment.predicted_top_oil_temperature_c));
      }
      if(kind==='tiny-rating'||kind==='extreme-current') {
        const row=section.getByRole('row').filter({hasText:'Capacity loading'});
        assert.equal(await row.getByRole('cell').nth(1).textContent(),'Unavailable');
        for (const reason of current.payload.execution_status.availability['electrical_metrics.capacity_loading_pct'].reasons) assert.ok((await row.textContent()).includes(reason));
        if(kind==='tiny-rating') assert.ok((await row.textContent()).includes('electrical_arithmetic_unavailable'));
        if(kind==='tiny-rating') assert.ok(Number.isFinite(Number(await section.getByRole('row').filter({hasText:'Apparent power'}).getByRole('cell').nth(1).textContent())));
        await page.getByRole('heading',{name:'Latest stored reading',exact:true}).waitFor();
      }
      evidence.actual.push({kind,...stream,checked:'Actual API identities, provenance display, chronological ID/value joins and metric availability'});
      await page.screenshot({path:path.join(dir,`actual-${kind}.png`),fullPage:true});
    }
    // Fixtures below modify browser responses only; they are not backend defects.
    capture=false;
    const route='**/api/v1/assets/*/analytics/latest?*';
    await page.route(route,async r=>{const real=await r.fetch();const wire=await real.json();wire.latest_telemetry_status='pending';await r.fulfill({response:real,json:wire});});
    await reload(); assert.ok(await page.getByLabel('Stored analytics').count());
    await page.route('**/api/v1/assets/*',r=>r.fulfill({status:503,json:{detail:'labelled offline fixture'}}));
    await page.getByRole('alert').filter({hasText:'503'}).waitFor({timeout:15000});
    assert.equal(await page.getByLabel('Stored analytics').count(),0);
    assert.equal(await page.getByText('Completed model:',{exact:false}).count(),0);
    await page.getByRole('heading',{name:'Latest stored reading',exact:true}).waitFor();
    const cells=await table.locator('tbody tr').first().locator('td').allTextContents();
    assert.notEqual(cells[3],'Unavailable');assert.equal(cells[4],'Unavailable');assert.equal(cells[5],'Unavailable');
    evidence.fixtures.push('Pending poll followed by labelled fatal 503: retained analytics cleared; telemetry retained');
    await page.screenshot({path:path.join(dir,'fixture-failed-poll.png'),fullPage:true});
    await page.unroute('**/api/v1/assets/*');await page.unroute(route);await reload();
    await page.route('**/api/v1/telemetry/*/analytics',async r=>{const real=await r.fetch();const wire=await real.json();wire.result.schema_version='labelled-unsupported-fixture';await r.fulfill({response:real,json:wire});});
    await reload();await page.getByRole('alert').filter({hasText:'Unsupported analytics result version'}).first().waitFor();
    assert.equal(await page.getByLabel('Stored analytics').count(),0);
    evidence.fixtures.push('Unsupported stored-result schema fixture rejected visibly; metrics cleared');
    await page.screenshot({path:path.join(dir,'fixture-unsupported.png'),fullPage:true});
    await page.unroute('**/api/v1/telemetry/*/analytics');await reload();
    for(const endpoint of ['**/api/v1/telemetry/*/analytics',route]) {
      await page.route(endpoint,async r=>{const real=await r.fetch();const wire=await real.json();wire.result.payload.metadata.parameter_version='labelled-contradictory-fixture';await r.fulfill({response:real,json:wire});});
      await reload();await page.getByRole('alert').filter({hasText:'model or parameter identity'}).first().waitFor();
      if(endpoint===route) assert.equal(await page.getByText('Completed model:',{exact:false}).count(),0);
      else assert.equal(await page.getByLabel('Stored analytics').count(),0);
      evidence.fixtures.push(`${endpoint}: labelled contradictory parameter identity rejected visibly`);
      await page.screenshot({path:path.join(dir,endpoint===route?'fixture-contradictory-latest.png':'fixture-contradictory-reading.png'),fullPage:true});
      await page.unroute(endpoint);await reload();assert.equal(await page.getByRole('alert').count(),0);
    }
    evidence.passed=true; evidence.actualNetwork=bodies.map(({body,...x})=>x);
    fs.writeFileSync(path.join(dir,'model-browser.json'),JSON.stringify(evidence,null,2));
    console.log(JSON.stringify({passed:true,actual:evidence.actual,fixtures:evidence.fixtures}));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
