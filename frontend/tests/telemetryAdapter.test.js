import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { adaptTelemetryReading } from '../src/services/telemetryAdapter.js';

const sample = JSON.parse(
  readFileSync(
    new URL('../src/data/telemetryResponseSample.json', import.meta.url),
    'utf8',
  ),
);

test('preserves asset, stream, timestamps and configuration', () => {
  const result = adaptTelemetryReading(sample);

  assert.equal(result.readingId, sample.id);
  assert.equal(result.assetId, sample.asset_id);
  assert.equal(result.source, 'device');
  assert.equal(result.runId, null);
  assert.equal(result.measurementTime, sample.measurement_time);
  assert.equal(result.arrivalTime, sample.arrival_time);
  assert.equal(result.configurationVersion, 1);
  assert.equal(result.outOfOrder, false);
});

test('uses normalized readings rather than the original payload', () => {
  const input = structuredClone(sample);
  input.original_payload.measurements.voltage_r_v = 999;

  const result = adaptTelemetryReading(input);

  assert.equal(result.measurements.voltage_r_v, 11000);
});

test('preserves every missing channel as null', () => {
  const result = adaptTelemetryReading(sample);

  const missingChannels = [
    'voltage_y_v',
    'voltage_b_v',
    'current_r_a',
    'current_y_a',
    'current_b_a',
    'oil_temperature_c',
    'ambient_temperature_c',
    'oil_level_pct',
  ];

  for (const channel of missingChannels) {
    assert.equal(result.measurements[channel], null, channel);
  }
});

test('preserves quality information and pending status', () => {
  const result = adaptTelemetryReading(sample);

  assert.deepEqual(result.qualityFlags, sample.quality_flags);
  assert.equal(result.measurementQuality.voltage_r_v, 'good');
  assert.equal(result.measurementQuality.current_r_a, 'missing');
  assert.equal(result.analyticsStatus, 'pending');
  assert.equal(result.processingJobStatus, 'pending');
});

test('preserves a genuine zero reading', () => {
  const input = structuredClone(sample);
  input.normalized_telemetry.measurements.current_r_a = 0;

  const result = adaptTelemetryReading(input);

  assert.equal(result.measurements.current_r_a, 0);
});

test('handles absent readings and unknown processing status', () => {
  assert.equal(adaptTelemetryReading(null), null);

  const input = structuredClone(sample);
  delete input.analytics_status;
  delete input.processing_job;

  const result = adaptTelemetryReading(input);

  assert.equal(result.analyticsStatus, 'unavailable');
  assert.equal(result.processingJobStatus, 'unavailable');
});