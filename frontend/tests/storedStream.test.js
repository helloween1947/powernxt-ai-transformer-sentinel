import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { adaptReadingAnalytics, adaptLatestAnalytics } from '../src/services/analyticsAdapter.js';
import { createTelemetryClient } from '../src/services/telemetryClient.js';
import { boundedMap, thermalPoints, loadStreamSnapshot, createStreamLoader } from '../src/services/storedStream.js';

const sample = JSON.parse(readFileSync(new URL('./fixtures/analytics-worker-result.json', import.meta.url)));
const selection = {assetId:'test', source:'simulator', runId:'run', offset:0};
function analytics(id, status = 'completed') {
  const wire = structuredClone(sample);
  Object.assign(wire,{reading_id:id, asset_id:'test', source:'simulator', run_id:'run', status});
  wire.configuration_version=2; wire.measurement_time=reading(id).measurementTime;
  wire.result.reading_id = id;
  Object.assign(wire.result.payload.metadata,{configuration_version:2,measurement_time:wire.measurement_time,reading_identity:{reading_id:id},stream:{asset_id:'test',source:'simulator',run_id:'run'}});
  if (['pending','processing','retry','failed'].includes(status)) wire.result = null;
  return adaptReadingAnalytics(wire);
}
function reading(id) {
  return { readingId:id, assetId:'test', source:'simulator', runId:'run', measurementTime:`2026-01-01T00:0${id}:00Z`, configurationVersion:2, measurements:{oil_temperature_c:40+id} };
}
function client(status = 'completed') {
  return {
    getAssetDetails: async assetId => ({asset_id:assetId}),
    getLatestTelemetry: async () => reading(2),
    getTelemetryHistory: async () => ({items:[reading(2),reading(1)],limit:20,offset:0}),
    getLatestAnalytics: async () => adaptLatestAnalytics({schema_version:'1.0.0',asset_id:'test',source:'simulator',run_id:'run',latest_telemetry_reading_id:2,latest_completed_reading_id:status==='completed'?2:1,latest_telemetry_status:status,result:null}),
    getReadingAnalytics: async id => analytics(id,id===2?status:'completed'),
  };
}

test('chart joins by reading ID, sorts UTC measurement time, preserves bootstrap gap and signed zero/residual', () => {
  const first = analytics(1);
  first.result.payload.thermal_assessment.measured_top_oil_temperature_c = 0;
  for (const metric of first.metrics.filter(m=>m.path.startsWith('thermal_assessment.'))) {
    metric.value=null; metric.reasons=['initialized_from_measurement_prediction_not_independent'];
  }
  const second = analytics(2);
  second.metrics.find(m=>m.path.endsWith('thermal_residual_c')).value=0;
  const points=thermalPoints([reading(2),{...reading(1),measurements:{oil_temperature_c:0}}],[second,first]);
  assert.deepEqual(points.map(p=>p.readingId),[1,2]);
  assert.equal(points[0].measured,0);
  assert.equal(points[0].predicted,null);
  assert.equal(points[0].residual,null);
  assert.deepEqual(points[0].reasons,['initialized_from_measurement_prediction_not_independent']);
  assert.equal(points[1].residual,0);
  assert.equal(points[1].processedAt,second.result.created_at);
});

test('latest completed remains separate from pending latest telemetry and analytics IDs are deduplicated', async () => {
  const c=client('pending');
  const called=[];
  const fetch=c.getReadingAnalytics;
  c.getReadingAnalytics=async id=>{called.push(id);return fetch(id);};
  const data=await loadStreamSnapshot(c,selection,new AbortController().signal);
  assert.equal(data.latestEnvelope.lagging,true);
  assert.equal(data.latest.readingId,2);
  assert.equal(data.completedAnalytics.reading_id,1);
  assert.equal(data.analytics.result,null);
  assert.equal(data.points[1].predicted,null);
  assert.equal(data.pending,true);
  assert.deepEqual(called.sort(),[1,2]);
});

test('wrong stream is rejected rather than joined into selected data', async () => {
  const c=client(); c.getReadingAnalytics=async id=>({...analytics(id),run_id:'other'});
  const snapshot = await loadStreamSnapshot(c,selection,new AbortController().signal);
  assert.equal(snapshot.latest.assetId, selection.assetId);
  assert.equal(snapshot.analytics, null);
  assert.ok(snapshot.errors.every(error => error.includes('different selected stream')));
});

test('four concurrent analytics requests maximum; individual failures remain recoverable', async () => {
  let active=0,peak=0;
  const result=await boundedMap([1,2,3,4,5,6,7], async id=>{
    peak=Math.max(peak,++active);
    await new Promise(resolve=>setTimeout(resolve,2)); active--;
    if (id===3) throw new Error('503'); return id;
  },new AbortController().signal);
  assert.equal(peak,4);
  assert.equal(result[2].ok,false);
  assert.equal(result[6].value,7);
});

test('HTTP client consistently encodes stream filters and page controls; cancellation and failures propagate', async () => {
  const calls=[];
  const controller=new AbortController();
  const c=createTelemetryClient('http://example.test/',async (url,options)=>{
    calls.push({url,signal:options.signal});
    return {ok:true,json:async()=>url.pathname.endsWith('/analytics/latest')?{schema_version:'1.0.0',result:null}:{items:[],limit:20,offset:20}};
  });
  await c.getTelemetryHistory('asset /',{source:'simulator',runId:'run /',offset:20,signal:controller.signal});
  await c.getLatestAnalytics('asset /','simulator','run /',controller.signal);
  assert.ok(calls.every(c=>c.url.searchParams.get('source')==='simulator' && c.url.searchParams.get('run_id')==='run /'));
  assert.equal(calls[0].url.searchParams.get('offset'),'20');
  controller.abort(); assert.ok(calls.every(c=>c.signal.aborted));
  const fail=createTelemetryClient('http://example.test',async()=>({ok:false,status:503}));
  await assert.rejects(fail.getReadingAnalytics(1),error=>error.status===503);
  await assert.rejects(createTelemetryClient('').getAssetPage(),/not been configured/);
  await assert.rejects(c.getLatestAnalytics('a','device','run'),/do not use/);
});

test('empty known stream and partial analytics failure do not fabricate results', async () => {
  const c=client();
  c.getLatestTelemetry=async()=>{const error=new Error('404');error.status=404;throw error;};
  c.getTelemetryHistory=async()=>({items:[],limit:20,offset:0});
  c.getLatestAnalytics=async()=>({schema_version:'1.0.0',asset_id:'test',source:'simulator',run_id:'run',latest_completed_reading_id:null});
  const empty=await loadStreamSnapshot(c,selection,new AbortController().signal);
  assert.deepEqual(empty.points,[]);assert.equal(empty.latest,null);assert.deepEqual(empty.errors,[]);
  const failing=client(); failing.getReadingAnalytics=async()=>{throw new Error('unreachable');};
  const partial=await loadStreamSnapshot(failing,selection,new AbortController().signal);
  assert.equal(partial.errors.length,2); assert.ok(partial.points.every(p=>p.predicted===null));
});

test('changing streams aborts and invalidates late responses even when a request ignores cancellation', async () => {
  let release;
  const c=client();
  c.getAssetDetails=assetId=>assetId==='old'?new Promise(resolve=>{release=()=>resolve({asset_id:assetId});}):Promise.resolve({asset_id:assetId});
  const states=[];
  const loader=createStreamLoader(c,state=>states.push(state));
  const old=loader.start({...selection,assetId:'old'});
  await loader.start(selection);
  const count=states.length;
  release(); await old;
  assert.equal(states.length,count);
  assert.equal(states.at(-1).snapshot.details.asset_id,'test');
  loader.cancel();
});

test('polling is bounded, stops on completion, and cancels scheduled work on unmount', async () => {
  const queue=[];const states=[];const removed=[];
  const c=client('pending');
  const loader=createStreamLoader(c,s=>states.push(s),{maxPolls:2,schedule:fn=>{queue.push(fn);return queue.length;},unschedule:id=>removed.push(id)});
  await loader.start(selection);
  await queue.shift()(); await queue.shift()();
  assert.equal(states.at(-1).exhausted,true);assert.equal(queue.length,0);
  await loader.start(selection);loader.cancel();assert.ok(removed.length);
  const terminal=[];
  await createStreamLoader(client(),s=>terminal.push(s),{schedule:()=>assert.fail('terminal data must not poll')}).start(selection);
  assert.equal(terminal.at(-1).polling,false);
});

test('failed load stops polling and a manual reload recovers', async () => {
  const c=client(); const details=c.getAssetDetails;
  c.getAssetDetails=async()=>{throw new Error('offline');};
  const states=[];
  const loader=createStreamLoader(c,s=>states.push(s));
  await loader.start(selection);assert.equal(states.at(-1).phase,'error');
  c.getAssetDetails=details;await loader.start(selection);assert.equal(states.at(-1).phase,'ready');
  loader.cancel();
});

test('history page offset is preserved and only that bounded page enters the comparison', async () => {
  const c = client();
  c.getTelemetryHistory = async (assetId, options) => {
    assert.equal(assetId,selection.assetId);
    assert.equal(options.offset,20);assert.equal(options.limit,20);
    assert.equal(options.source,'simulator');assert.equal(options.runId,'run');
    return {items:[reading(1)],offset:20,limit:20};
  };
  const snapshot=await loadStreamSnapshot(c,{...selection,offset:20},new AbortController().signal);
  assert.equal(snapshot.page.offset,20);assert.deepEqual(snapshot.points.map(p=>p.readingId),[1]);
  assert.equal(snapshot.analytics.reading_id,2); // Latest remains separate from historical page.
});

test('a result cannot be labelled with another telemetry configuration or measurement time', async () => {
  for (const change of [{configuration_version:99},{measurement_time:'2028-01-01T00:00:00Z'}]) {
    const c=client(); c.getReadingAnalytics=async id=>({...analytics(id),...change});
    const snapshot = await loadStreamSnapshot(c,selection,new AbortController().signal);
    assert.equal(snapshot.latest.readingId, 2);
    assert.equal(snapshot.analytics, null);
    assert.ok(snapshot.errors.every(error => error.includes('differs from telemetry')));
  }
});

test('unsupported thermal units stay gaps through the complete chart join', () => {
  const result = analytics(1);
  result.result.payload.metadata.units.oil_temperature = 'F';
  result.result.payload.metadata.units.thermal_residual = 'F';
  const point = thermalPoints([reading(1)], [adaptReadingAnalytics(result)])[0];
  assert.equal(point.measured, null);
  assert.equal(point.predicted, null);
  assert.equal(point.residual, null);
  assert.ok(point.reasons.includes('unsupported_metric_unit'));
});
