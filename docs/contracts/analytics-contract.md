# Durable analytics result contract

Implemented by the analytics-worker feature; review scope is the supplied Person B handoff at `637fbe810714d0d5c403728ddf7bcba746ea55a9`. This replaces the earlier proposed prototype contract whose forecasts, calibrated confidence, health index, winding model and standards-compliance claims are not supported here. Person A adopts B's capacity-loading interpretation, previous-sample hold, measurement dt and300s continuity policy for this version. Person C consumes the following committed read APIs; this does not claim frontend integration or cross-team PR approval.

## Deterministic computation boundary

`compute_analytics(normalized_telemetry, asset_config, quality_flags, reading_id, previous_state=None, *, state_policy='forward_only')` is the reviewed pure computation. It receives the immutable configuration referenced by the reading, never latest configuration or raw payload/ground truth. Model state/results have the versions and units described in [worker policy](../analytics-worker.md). Its exact typed output schema is [worker-output.schema.json](../../backend/app/analytics/person_b/worker-output.schema.json). Executed input/state/output examples are [worker-test-examples.json](../../backend/app/analytics/person_b/worker-test-examples.json). Module output has no wall-clock timestamp; persistence adds created_at.

## Reading result/status

`GET /api/v1/telemetry/{reading_id}/analytics`

Unknown reading:404. Otherwise200 with envelope schema_version `1.0.0`, reading/configuration references, asset/source/run, UTC measurement_time, persisted job status, attempts, bounded error_code and nullable result. Pending/processing/retry/failed have no fabricated analytical result. Completed/unavailable contain a StoredAnalytics object: ID, reading_id, model_id/version, parameter_version, computation schema_version, status, created_at and payload. OpenAPI defines these envelopes.

```json
{
  "schema_version": "1.0.0",
  "reading_id": 12,
  "configuration_version": 1,
  "asset_id": "illustrative-transformer",
  "source": "simulator",
  "run_id": "illustrative-run",
  "measurement_time": "2026-01-01T00:01:00Z",
  "status": "pending",
  "attempts": 0,
  "error_code": null,
  "result": null
}
```

This is an illustrative pending envelope, not a claimed database record. Full actual completed response from isolated verification is in `data/sample/analytics-worker-result.json` with its demonstration identity retained. A completed result may still be partial: bootstrap has no independent thermal prediction/residual, absent coefficients yield electrical evidence with unsupported_configuration, and every unsupported/missing metric includes null plus availability/reasons. An unavailable result may retain individual electrical metrics. A failed job has only its error code and no invented model output.

## Latest completed analytical result for one explicit stream

`GET /api/v1/assets/{asset_id}/analytics/latest?source=simulator&run_id=RUN`

`source` is required. Device requires absent/null run_id; simulator/file_replay require run_id. Unknown asset404; known empty stream200 with null telemetry/result fields. Never combines runs/sources. The envelope includes latest_telemetry_reading_id/time/status and latest_completed_reading_id/time/result, so consumers can detect lag or unavailable/failed newest telemetry. Latest completed sorts by measurement time descending, reading ID descending, then result ID descending; it excludes unavailable and failed jobs. It can therefore be older than latest telemetry. Completion is processing success, not an assurance all metrics are valid; inspect payload availability and limitations.

Telemetry endpoints retain fields, IDs, normalization, deduplication and history semantics. `analytics_status` and processing_job.status now reflect persisted pending/processing/retry/completed/unavailable/failed. An identical retry retains the original ingestion identity/data but reports the current processing status. Clients that assumed the status literal is permanently pending must accept the expanded enum.

Electrical loading/power, magnitude imbalance and simplified top-oil prediction/residual are the only supported calculations. Null PF, real/reactive power, sequences, winding hotspot, aging, health/confidence and forecasts are explicitly unavailable. Configured limit observations are instant comparisons, not delivered alerts. See the model schema/worker policy for units, input exclusions, 300s continuity and calibration limits.
