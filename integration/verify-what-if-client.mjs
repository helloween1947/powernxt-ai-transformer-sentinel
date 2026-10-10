// Actual fetch + reference adapter + existing React chart consumption; no browser claim.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { adaptWhatIf, postWhatIf } from './what-if-client.mjs';
import React from '../frontend/node_modules/react/index.js';
import ReactDOMServer from '../frontend/node_modules/react-dom/server.node.js';
import { transformWithOxc } from '../frontend/node_modules/vite/dist/node/index.js';

const [baseUrl, evidencePath] = process.argv.slice(2);
if (!baseUrl || !evidencePath) throw new Error('Usage: node integration/verify-what-if-client.mjs <isolated-api-url> <verified-json>');
const target = new URL(baseUrl);
if (!['localhost', '127.0.0.1'].includes(target.hostname)
    || ['8000', '8001', '18001', '18002', ''].includes(target.port)) throw new Error('Dedicated test API required');
const evidence = JSON.parse(await readFile(evidencePath, 'utf8'));
const { response, chart } = await postWhatIf(baseUrl, evidence.asset_id,
  evidence.examples.explicit_reference_request, AbortSignal.timeout(10000));
assert.deepEqual(response, evidence.examples.success.response);
assert.equal(chart.points.length, 97);
assert.equal(chart.baselineCrossing.status, 'crossing');
assert.equal(chart.reducedLoadCrossing.status, 'no_crossing_within_horizon');
assert.equal(chart.reducedLoadCrossing.time_s, null);
assert.equal(chart.points[0].baseline, chart.points[0].alternative);
assert.equal(chart.finalDifferenceC, response.reduced_load.final_top_oil_temperature_c - response.baseline.final_top_oil_temperature_c);
const noLimit = await postWhatIf(baseUrl, evidence.asset_id, {
  ...evidence.examples.success.request, state_ref: evidence.examples.missing_limit.response.state.state_ref,
}, AbortSignal.timeout(10000));
assert.equal(noLimit.chart.baselineCrossing.status, 'unavailable');
assert.equal(noLimit.chart.baselineCrossing.time_s, null);
await assert.rejects(postWhatIf(baseUrl, evidence.asset_id, evidence.examples.success.request),
  error => error.status === 409 && error.code === 'ineligible_state');
assert.throws(() => adaptWhatIf({ ...response, units: { temperature: 'F' } }), /units/);

const source = new URL('../frontend/src/components/TrendChart.jsx', import.meta.url);
const cache = new URL('../frontend/node_modules/.cache/what-if-verification/', import.meta.url);
await mkdir(cache, { recursive: true });
const compiled = new URL('TrendChart.mjs', cache);
const transformed = await transformWithOxc(await readFile(source, 'utf8'), fileURLToPath(source), { jsx: { runtime: 'automatic' } });
await writeFile(compiled, transformed.code);
const { default: TrendChart } = await import(compiled.href);
const markup = ReactDOMServer.renderToStaticMarkup(React.createElement(TrendChart, {
  title: 'Conditional healthy-model top-oil comparison', points: chart.points,
  series: [{ key: 'baseline', label: 'Baseline estimate', color: '#a16207' },
    { key: 'alternative', label: 'Reduced load estimate', color: '#0e7490' }],
}));
assert.ok(markup.includes('data-series="baseline"') && markup.includes('data-series="alternative"'));
assert.ok(markup.includes(chart.points[0].timestamp) && markup.includes(chart.points.at(-1).timestamp));
assert.ok(!markup.includes('NaN'));
console.log('PASS: actual HTTP response, immutable reference, null limit states, error codes and existing React chart rendered through reference adapter');
