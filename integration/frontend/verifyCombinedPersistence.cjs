// Real C-screen offline/restart checks. Requires Playwright and installed Chrome.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const mode = process.argv[2];
const origin = process.env.FRONTEND_ORIGIN || 'http://127.0.0.1:5173';
const base = process.env.BACKEND_ORIGIN || 'http://127.0.0.1:8000';
const dir = process.env.BROWSER_ARTIFACT_DIR;
const asset = process.env.DEMO_ASSET_ID;
if (!dir || !asset || !['--offline', '--saved'].includes(mode)) throw new Error('Set DEMO_ASSET_ID/BROWSER_ARTIFACT_DIR and choose --offline or --saved');
(async () => {
 if(mode==='--saved') {
  let ready=false;
  for(let attempt=0;attempt<20;attempt++) {
   try {const response=await fetch(`${base}/health/ready`,{signal:AbortSignal.timeout(2000)});if(response.ok){ready=true;break;}}catch{}
   await new Promise(resolve=>setTimeout(resolve,500));
  }
  assert(ready,'Restarted backend must become ready before browser assertions');
 } else {
  const reachable=await fetch(`${base}/health/ready`,{signal:AbortSignal.timeout(2000)}).then(()=>true,()=>false);
  assert.equal(reachable,false,'Offline mode requires a genuinely stopped backend');
 }
 const browser = await chromium.launch({ headless:true, executablePath: process.env.BROWSER_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
 try {
  const page = await browser.newPage(); const pageErrors=[]; page.on('pageerror', e=>pageErrors.push(e.message));
  await page.goto(origin);
  await page.getByRole('navigation').getByRole('button',{name:'Backend maintenance',exact:true}).click();
  await page.getByRole('button',{name:'Load registered assets',exact:true}).click();
  if(mode==='--offline') {
   await page.getByRole('alert').filter({hasText:'Cannot reach the maintenance backend'}).waitFor();
   assert(await page.getByRole('button',{name:'Create backend task',exact:true}).isDisabled());
   console.log('Actual stopped backend: visible API/network failure; no fixture fallback; creation disabled');
  } else {
   const previous=JSON.parse(fs.readFileSync(path.join(dir,'browser-verification.json'),'utf8'));
   await page.getByLabel('Maintenance asset',{exact:true}).selectOption(asset);
   await page.getByRole('button',{name:'Load / refresh backend tasks',exact:true}).click();
   const task=page.locator(`[data-task-id="${previous.taskIds[0]}"]`);
   await task.getByText('Saved: Completed',{exact:false}).waitFor();
   assert(await task.getByRole('button',{name:'Save task update'}).isDisabled());
   await task.getByRole('button',{name:'View history'}).click();
   await page.getByText('Version 4: In progress',{exact:false}).waitFor();
   const response=await fetch(`${base}/api/v1/maintenance/tasks/${previous.taskIds[0]}`);
   assert.equal(response.status,200);const value=await response.json();assert.equal(value.version,4);assert.equal(value.status,'completed');
   const states=['completed','open','cancelled','cancelled'];
   const versions=[4,3,2,3];
   for(let index=0;index<previous.taskIds.length;index++) {
    const id=previous.taskIds[index];const expected=states[index];
    const card=page.locator(`[data-task-id="${id}"]`);
    await card.getByText(`Saved: ${expected[0].toUpperCase()+expected.slice(1)}`,{exact:false}).waitFor();
    const saved=await fetch(`${base}/api/v1/maintenance/tasks/${id}`).then(r=>r.json());
    assert.equal(saved.status,expected);assert.equal(saved.version,versions[index]);
    if(expected!=='open') assert(await card.getByRole('button',{name:'Save task update'}).isDisabled());
    const history=await fetch(`${base}/api/v1/maintenance/tasks/${id}/history`).then(r=>r.json());
    assert.equal(history.items.length,versions[index]);
   }
   console.log(`Actual backend restart: all four workflow tasks/versions/history persist; completed/cancelled editors read-only (${value.id})`);
  }
  assert.deepEqual(pageErrors,[]);
  await page.screenshot({path:path.join(dir,mode.slice(2)+'.png'),fullPage:true});
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
