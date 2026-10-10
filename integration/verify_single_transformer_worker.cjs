// Actual API + durable Docker worker; only same transformer, separate QA runs.
const fs=require('node:fs');const path=require('node:path');const cp=require('node:child_process');const assert=require('node:assert/strict');const crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');const dir=path.join(root,'data/generated/single-transformer');
const prefix=['compose','--env-file',path.join(dir,'private.env'),'-f',path.join(root,'integration/compose.single-transformer.yaml')];
function docker(args,input){const r=cp.spawnSync('docker',[...prefix,...args],{cwd:root,encoding:'utf8',input,timeout:90000});assert.equal(r.status,0,`Isolated docker command failed (${args.slice(0,4).join(' ')}): ${r.stderr}`);return r.stdout;}
const config=JSON.parse(docker(['config','--format','json']));assert.match(config.name,/^powernxt_single_/);assert.equal(config.services.db.environment.POSTGRES_DB,'single_transformer_app_test');
const base='http://127.0.0.1:'+config.services.backend.ports[0].published;
async function api(route,payload,status=200){const r=await fetch(base+route,{method:payload?'POST':'GET',headers:{'Content-Type':'application/json','Connection':'close'},body:payload?JSON.stringify(payload):undefined,signal:AbortSignal.timeout(15000)});assert.equal(r.status,status,route+' '+await (r.status===status?Promise.resolve(''):r.text()));return r.json();}
function snapshot(name){docker(['exec','-T','backend','python','-m','integration.snapshot_single_transformer','--output','/evidence/'+name+'.json']);return JSON.parse(fs.readFileSync(path.join(dir,name+'.json')));}
async function done(id){const deadline=Date.now()+60000;while(Date.now()<deadline){const e=await api('/api/v1/telemetry/'+id+'/analytics');assert.equal(e.reading_id,id);if(['completed','unavailable','failed'].includes(e.status)){assert.equal(e.status,'completed');return e;}await new Promise(r=>setTimeout(r,250));}throw Error('Worker deadline exceeded');}
(async()=>{const seed=JSON.parse(fs.readFileSync(path.join(dir,'seed.json')));const packets=fs.readFileSync(path.join(dir,'packets.jsonl'),'utf8').trim().split('\n').map(JSON.parse);const baseline=snapshot('worker-baseline');const run='single-worker-qa-'+crypto.randomUUID().slice(0,8);const rows=packets.map((p,i)=>({...p,run_id:run,message_id:crypto.randomUUID(),timestamp:`2026-01-01T00:0${i}:00Z`}));let stopped=false;
try {
 docker(['stop','worker']);stopped=true;
 const readings=[];for(const p of rows)readings.push(await api('/api/v1/telemetry',p,201));
 const pending=snapshot('worker-pending');assert.equal(pending.tables.analytics_results.count,baseline.tables.analytics_results.count);
 docker(['start','worker']);stopped=false;
 const results=[];for(const r of readings)results.push(await done(r.id));assert.equal(results.length,6);assert.ok(results[0].result.payload.thermal_assessment.initial_condition);assert.equal(results[0].result.payload.thermal_assessment.predicted_top_oil_temperature_c,null);
 for(const result of results.slice(1))assert.equal(result.result.payload.thermal_assessment.elapsed_s,60);
 const before=snapshot('worker-before-retries');for(const p of rows)await api('/api/v1/telemetry',p,200);assert.deepEqual(snapshot('worker-after-retries'),before);
 docker(['restart','worker']);assert.deepEqual(snapshot('worker-after-worker-restart'),before);
 docker(['stop','worker']);stopped=true;
 const recovery={...rows[5],message_id:crypto.randomUUID(),timestamp:'2026-01-01T00:06:00Z'};const receipt=await api('/api/v1/telemetry',recovery,201);
 docker(['exec','-T','backend','python','-c',"from backend.app.db.session import SessionLocal,engine; from backend.app.services.analytics_worker import claim_next; assert engine.url.database == 'single_transformer_app_test'; claim = claim_next(SessionLocal,lease_seconds=2); assert claim is not None; print('Abandoned owned claim created')"]);
 docker(['start','worker']);stopped=false;const recovered=await done(receipt.id);assert.equal(recovered.attempts,2);
 const independent=await api('/api/v1/telemetry',{...rows[0],message_id:crypto.randomUUID(),run_id:run+'-other'},201);const other=await done(independent.id);assert.ok(other.result.payload.thermal_assessment.initial_condition);
 const final=snapshot('worker-final');const qaStreams=final.streams.filter(s=>s.run_key===run||s.run_key===run+'-other');assert.deepEqual(qaStreams.map(s=>s.advances).sort((a,b)=>a-b),[1,7]);
 for(const table of ['telemetry_readings','telemetry_processing_jobs','analytics_results'])assert.equal(final.tables[table].count,baseline.tables[table].count+8);
 assert.equal(final.tables.assets.count,1);assert.equal(final.tables.asset_configurations.sha256,baseline.tables.asset_configurations.sha256);
 for(const id of seed.reading_ids){const result=await api('/api/v1/telemetry/'+id+'/analytics');const original=JSON.parse(fs.readFileSync(path.join(dir,'results.json'))).find(r=>r.reading_id===id);assert.deepEqual(result,original);}
 const report={status:'PASS',timestamp:new Date().toISOString(),project:config.name,asset_id:seed.asset_id,qa_run:run,first_batch:6,identical_retries:6,qa_final_counts:{readings:8,jobs:8,results:8},database_counts:{readings:final.tables.telemetry_readings.count,jobs:final.tables.telemetry_processing_jobs.count,results:final.tables.analytics_results.count,assets:1},recovery_attempts:recovered.attempts,stream_advances:[1,7],worker_restart_persistence:true,demo_records_unchanged:true,windows_execution:process.platform==='win32'};
 fs.writeFileSync(path.join(dir,'worker-verification.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{if(stopped)docker(['start','worker']);}
})().catch(e=>{console.error(e.message, e.cause?.message || '');process.exitCode=1;});
