# Backend integration guide

## Inputs and durable state

Import `process_telemetry_response` from `analytics`. Supply the ingestion `TelemetryResponse` as a JSON dict and the exact `ConfigurationResponse` matching the normalized reading's `(asset_id, configuration_version)`. Configuration-create request bodies omit identity/version and are not sufficient. Fetch the bound immutable record through A's service/API; do not select latest silently.

`process_reading` accepts the normalized envelope and channel reason lists directly. It does not receive job policy or arrival time; its caller owns those checks. The response adapter enforces both admission `processing_job.state_policy` and the last-processed watermark, so a forward-eligible job executing late cannot rewind state. It verifies outer envelope/normalized stream and timestamp agreement and ignores `original_payload`.

Lock and store state independently for `(asset_id, source, run_id)`. Reusing another stream's state raises ValueError. Persist the opaque, JSON-safe `updated_state` and pass it back on the next call. Prior state and caller inputs are never mutated. Config changes require an explicit cold start (`previous_state=None`) or replay. Unknown current/ambient history remains invalid; do not reset automatically on each oil reading. Audit resets and retain prior incidents in D's store.

## Future worker transaction

1. Read pending job, normalized telemetry/flags and bound config.
2. Lock the stream's durable model-state record.
3. Recheck job idempotency and processed watermark while locked.
4. Call `process_telemetry_response(response_dict, configuration_dict, state_dict)`.
5. Atomically save result/state, idempotent alert transitions and completed job status.
6. Publish committed results/events through an outbox after commit.

The current backend supports only pending jobs and has no model-state or result tables. This module performs no storage/transport writes and does not fabricate completion. Compatibility tests call analytics after actual committed ingestion, rather than implementing this future worker.

## Freshness and gaps

Device responses compare measurement time to immutable first-arrival time: more than 300 s delay or a future measurement prevents advancement. Simulator/replay responses use event time and may legitimately replay historical dates. Freshness at worker execution/current dashboard time remains A/C's responsibility. Global `quality_flags.stale=true` also prevents advancement; `clamped=true` excludes all input measurements.

Bad/suspect/flagged measurements are unavailable. Missing data never resolves an incident. Non-advancing outputs retain old active observations with `evidence_available=false`, preserve their evidence timestamp, and return unchanged state. C must not replace live values with historical diagnostic metrics. Equal timestamps and retries cannot advance timers. No incoming samples means A/C must expose feed silence; the detector cannot advance when it receives no calls.

## D's alert/event handoff

`anomaly_observations` contains active incidents and opening/resolution transitions. Each has category, severity, incident ID, lifecycle, evidence/units, threshold, rationale, evidence availability and null normalized anomaly score. Residual evidence does not uniquely determine a fault's root cause.

IDs include asset/source/run/config-version/initial-measurement-epoch/type/sequence. A/D should persist transitions idempotently by ID and lifecycle. A deliberate cold start at a new measurement time creates a distinct epoch; replaying the same run from the same time intentionally recreates deterministic incident IDs. Use a new run ID for an independent simulator/replay experiment. Retain prior incidents across cold starts. The detector is not a globally unique event publisher. D adds the shared UUID `event_id`, publication time and event envelope, and owns acknowledgement, tasks and history.

## C's what-if handoff

```python
from analytics import compare_what_if

comparison = compare_what_if(saved_state, [
    {"name": "keep_load", "profile": [
        {"duration_s": 14400, "load_pu": 1.3, "ambient_temp_c": 30, "cooling_factor": 1.0}
    ]},
    {"name": "reduce_load", "profile": [
        {"duration_s": 14400, "load_pu": 0.7, "ambient_temp_c": 30, "cooling_factor": 1.0}
    ]},
])
```

Loading is thermal RMS current divided by rated current, not fleet-average capacity percentage. Scenarios have identical horizon and measured/simulated/replayed initial oil temperature. Predictions are estimated. Cooling factors are explicit sensitivity assumptions, not calibrated fan settings; a residual does not establish cooling efficiency. C displays source, initial temperature, assumptions, input profiles, final/peak/crossing outputs and baseline deltas.

Forecasts require configured top-oil coefficients, valid load history, usable oil and ambient. Unknown state/invalid profiles raise ValueError. A maps these to API errors and imposes request-size/horizon limits. Crossing time has up to 60 s resolution; no crossing within a horizon is not a permanent safety guarantee. No calibrated uncertainty intervals are available.
