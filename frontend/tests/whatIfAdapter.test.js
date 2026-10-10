import test from 'node:test';
import assert from 'node:assert/strict';
import { adaptWhatIf, validateWhatIfRequest } from '../src/services/whatIfAdapter.js';
import { createWhatIfClient, WhatIfApiError } from '../src/services/whatIfApi.js';

const mockWhatIfResponse = {
  schema_version: 'what-if-response-1.0.0',
  state: {
    state_ref: 'f1a2b3c4-9999-8888-7777-666655554444',
    asset_id: 'tx-beta',
    source: 'device',
    run_id: null,
    reading_id: 42,
    result_id: 42,
    measurement_time: '2026-10-10T14:00:00Z',
    captured_at: '2026-10-10T14:00:05Z',
  },
  configuration: {
    asset_id: 'tx-beta',
    version: 1,
    created_at: '2026-10-10T00:00:00Z',
    parameter_version: 'param-v1',
  },
  model: {
    model_version: 'stored-reading-top-oil-1.0.2',
  },
  units: {
    temperature: 'C',
    elapsed_time: 's',
    thermal_load: 'pu',
  },
  parameter_provenance: {
    delta_oil_rated_k: 'assumed_uncalibrated',
  },
  assumptions: ['Conditional healthy-model estimates', 'Constant ambient temperature'],
  sampling: {
    step_s: 300,
    count: 2,
  },
  configured_top_oil_limit_c: 105.0,
  limit_reasons: [],
  baseline: {
    inputs: {
      duration_s: 300,
      thermal_load_pu: 1.0,
      ambient_temperature_c: 25.0,
    },
    points: [
      { elapsed_s: 0, estimated_top_oil_temperature_c: 60.0 },
      { elapsed_s: 300, estimated_top_oil_temperature_c: 65.0 },
    ],
    final_top_oil_temperature_c: 65.0,
    peak_top_oil_temperature_c: 65.0,
    limit_crossing: {
      status: 'no_crossing_within_horizon',
      time_s: null,
      reasons: [],
    },
  },
  reduced_load: {
    inputs: {
      duration_s: 300,
      thermal_load_pu: 0.8,
      ambient_temperature_c: 25.0,
    },
    points: [
      { elapsed_s: 0, estimated_top_oil_temperature_c: 60.0 },
      { elapsed_s: 300, estimated_top_oil_temperature_c: 62.0 },
    ],
    final_top_oil_temperature_c: 62.0,
    peak_top_oil_temperature_c: 62.0,
    limit_crossing: {
      status: 'no_crossing_within_horizon',
      time_s: null,
      reasons: [],
    },
  },
  final_temperature_difference_c: -3.0,
};

test('validateWhatIfRequest validates bounds, equal ambient, and load ordering', () => {
  const valid = validateWhatIfRequest({
    source: 'device',
    durationS: 7200,
    ambientC: 25,
    baselineLoadPu: 1.2,
    reducedLoadPu: 0.9,
  });
  assert.equal(valid.schema_version, 'what-if-request-1.0.0');
  assert.equal(valid.source, 'device');
  assert.equal(valid.baseline.thermal_load_pu, 1.2);
  assert.equal(valid.reduced_load.thermal_load_pu, 0.9);
  assert.equal(valid.baseline.duration_s, 7200);

  // Reduced load cannot exceed baseline
  assert.throws(() => validateWhatIfRequest({
    baselineLoadPu: 0.8,
    reducedLoadPu: 1.0,
  }), /cannot exceed baseline/);

  // Negative or excessive durations
  assert.throws(() => validateWhatIfRequest({ durationS: 0 }), /Duration/);
  assert.throws(() => validateWhatIfRequest({ durationS: 100000 }), /Duration/);

  // Simulator requires runId
  assert.throws(() => validateWhatIfRequest({ source: 'simulator', runId: '' }), /Run ID/);
});

test('adaptWhatIf converts points to trend chart format and retains crossing information', () => {
  const chartData = adaptWhatIf(mockWhatIfResponse);
  assert.equal(chartData.stateRef, mockWhatIfResponse.state.state_ref);
  assert.equal(chartData.points.length, 2);
  assert.equal(chartData.points[0].baseline, 60.0);
  assert.equal(chartData.points[0].alternative, 60.0);
  assert.equal(chartData.points[1].baseline, 65.0);
  assert.equal(chartData.points[1].alternative, 62.0);
  assert.equal(chartData.finalDifferenceC, -3.0);
  assert.equal(chartData.baselineCrossing.status, 'no_crossing_within_horizon');
});

test('whatIfClient handles 409 state_unavailable with code and reasons', async () => {
  const client = createWhatIfClient({
    baseUrl: 'http://test-what-if.local',
    fetchImpl: async () => new Response(JSON.stringify({
      detail: {
        schema_version: 'what-if-error-1.0.0',
        code: 'state_unavailable',
        message: 'No committed forward worker state found for stream',
        reasons: ['Worker has not processed initial reading'],
      },
    }), { status: 409 }),
  });

  await assert.rejects(
    client.compare('tx-beta', {
      source: 'device',
      durationS: 300,
      ambientC: 25,
      baselineLoadPu: 1.0,
      reducedLoadPu: 0.8,
    }),
    error => {
      assert(error instanceof WhatIfApiError);
      assert.equal(error.status, 409);
      assert.equal(error.code, 'state_unavailable');
      assert.equal(error.reasons[0], 'Worker has not processed initial reading');
      return true;
    }
  );
});
