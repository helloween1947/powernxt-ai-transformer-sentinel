# Person B -> Person A: stored-reading analytics handoff

## Implemented callable subset

```python
from analytics import process_stored_reading

result = process_stored_reading(
    stored_reading=telemetry_response.model_dump(mode="json"),
    asset_config=configuration_response.model_dump(mode="json"),
    previous_state=saved_state_or_none,
)
# A atomically persists result, result["updated_state"] and job completion.
```

Implementation: `analytics/worker.py`. Runtime Python3.11+ and standard library only. The function is deterministic for the same inputs, independent of I/O and wall-clock time, and does not mutate input/state. It extends the existing electrical/top-oil core; old `process_reading`, `process_telemetry_response`, heuristic alert/health and what-if APIs remain compatible but are **not** this conservative worker contract. Their old state is not accepted by this entrypoint.

Supported: current-based per-phase/max loading, RMS thermal loading, magnitude imbalance, apparent-power estimate and capacity loading; configured top-oil prediction; observed-minus-predicted residual; instant configured load/oil/voltage-limit evidence; explicit channel availability; version-bound serializable state.

Unavailable: active/reactive power, power factor, sequence components, winding hot-spot, aging/RUL, health index, confidence score, fault probability, forecasts and maintenance recommendations. These are null or explicitly listed, never guessed. Limit checks are not lifecycle alerts or automatic maintenance actions.

## Exact schemas and example files

- Request: `analytics/schemas/worker-input.schema.json`, JSON Schema2020-12.
- Result: `analytics/schemas/worker-output.schema.json`, JSON Schema2020-12.
- Person C: `analytics/examples/worker-test-examples.json`, **actual local module executions on sanitized numerical test inputs**, not backend-admitted readings or measured field data. Three cases: observed initialization, elapsed prediction/residual, missing thermal parameters. Each includes exact request and result.
- Regenerate: `python -m analytics.examples.generate_worker_examples` (backend dev dependencies needed for schema export only).

The request root contains stored_reading, asset_config and optional previous_state. Config uses A's existing ConfigurationResponse schema; normalized telemetry uses TelemetryCreate1.0.0. Runtime binding checks additionally enforce relationships JSON Schema alone cannot express.

### Stored-reading fields consumed

| Field | Type / semantics |
|---|---|
| id | Positive integer database reading identity |
| message_id | UUID4 string; must match normalized telemetry |
| asset_id, source, run_id | Stream identity; source device/simulator/file_replay; device run null |
| configuration_version | Positive integer; exact immutable config selection |
| measurement_time | Aware ISO time, normalized to UTC; must agree with normalized timestamp |
| normalized_telemetry | schema_version1.0.0, message/stream/config identity, timestamp, measurements and producer measurement_quality |
| quality_flags | Per-channel ingestion reason lists; optional explicit global stale/clamped booleans |
| processing_job.state_policy | forward_only or historical_only; respected independently of processed watermark |

A may supply the full TelemetryResponse; original_payload, arrival_time, status metadata and scenario/ground-truth data are not used by computation. Only an explicit whitelist of normalized fields enters calculations. No simulation metadata is used to select physical parameters. Config is supplied separately from the reading-bound immutable record, never latest config.

Channels: voltage_r/y/b_v (RMS configured convention/side volts); current_r/y/b_a (RMS **line** amps on the same side); oil_temperature_c and ambient_temperature_c (C); optional oil_level_pct (%). Missing/omitted values remain null. A real zero is usable. Any non-good producer flag, nonempty ingestion reason list, invalid number or documented analytics sanity violation makes that channel unavailable. No clamping/imputation occurs.

The inherited B sanity policy is current0..10x rating, voltage0..2x rating, oil-50..200C, ambient-50..80C, level0..100%. It is narrower than A's ingestion limits and is explicitly a model-usability policy, not protection settings. Unknown channel/quality names fail validation; unknown reason strings on a known channel conservatively exclude it. stale=true prohibits advancement; clamped=true excludes all measurements. A remains responsible for upstream validity and freshness decisions.

### Eight result partitions

| Partition | Concrete contents |
|---|---|
| electrical_metrics | phase_loading_pct (3 nullable values), max_phase_loading_pct, thermal_load_pu, current/voltage_magnitude_imbalance_pct, apparent_power_kva, capacity_loading_pct; method/convention/side; null unsupported power/sequence fields |
| thermal_assessment | predicted_top_oil_temperature_c, measured_top_oil_temperature_c, thermal_residual_c; initial_condition with source/units/time; elapsed_s; estimated prediction source, interval convention and reasons |
| condition_contributors | health_index null, not_assessed reason; aging fields null |
| data_confidence | score null, not_estimated reason; usable/required **counts**, per-channel usability and reason lists; counts are not confidence probabilities |
| anomaly_observations | Instant configured_limit_check records: quantity, value, threshold, unit, relation, breached boolean/null, status and reasons; no incident IDs/severity/lifecycle |
| updated_state | Opaque state object or null; unchanged prior state for non-advancing readings |
| metadata | Result/model/parameter versions, reading identity, UTC time, stream, configuration version, provenance and units |
| execution_status | computed/degraded/insufficient_data, state_advanced, state_policy, ordering reasons, per-quantity availability, missing measurements and unsupported outputs |

Use per-quantity availability rather than infer all fields from one overall status. Partial phase loading can exist when total apparent power/thermal K cannot. All-zero currents yield valid zero loading/power; magnitude imbalance is null because its denominator is zero. Missing evidence is never a false/zero threshold result. Historical diagnostics have their own measurement timestamp and must not replace newer dashboard data.

## Electrical and thermal assumptions

Per-phase current loading=100*I_line/I_rated. Thermal K=sqrt(mean((I_line/I_rated)^2)). Phase-neutral apparent sum=sum(V_LN*I_line)/1000; it is a sum of phase apparent magnitudes, not net complex power or kW. With line-line magnitudes only, use sqrt(3)*mean(V_LL)*mean(I_line)/1000 as a **balanced-system approximation**; do not claim exact unbalanced apparent power or reconstruct phase voltages. Capacity loading=100*that estimate/rated_kva. Magnitude imbalance=max absolute deviation from mean/mean*100, not negative-sequence unbalance.

Required thermal coefficients, all from bound config with provenance:

| Registry key | Unit |
|---|---|
| thermal_parameters.rated_top_oil_rise_c | C |
| thermal_parameters.oil_time_constant_min | min, converted to seconds |
| thermal_parameters.loss_ratio | Dimensionless rated-load/no-load loss ratio |
| thermal_parameters.oil_exponent | Dimensionless |

No fallback coefficient/profile is applied. Existing simulator snapshots leave them null, so prediction/residual remain unavailable with exact missing paths. The numerical example explicitly supplies the existing B demo assumptions40C/180min/R5/n0.8 with assumed provenance. These stay attached to its test configuration and hashed parameter version, not copied from generator metadata.

The existing B simplified equilibrium is ambient+rise*((1+R*K^2)/(1+R))^n. Exact first-order step: target+(previous_temperature-target)*exp(-dt/tau). This task reuses that physical core and versions the temporal convention as **previous-sample zero-order hold**. It assumes constant effective time constant and no adaptive oil assimilation, winding dynamics, cooling controller or voltage-driven core-loss changes; it is not certified IEEE compliance.

Technical applicability: the existing model documentation references [NREL transformer thermal modeling](https://docs.nrel.gov/docs/fy11osti/48827.pdf); [primary ONAN time-constant calibration research](https://research.manchester.ac.uk/en/publications/top-oil-temperature-modelling-by-calibrating-oil-time-constant-fo/) supports the need for asset-specific calibration rather than universal tau. [Eaton's three-phase handbook](https://www.eaton.com/content/dam/eaton/products/backup-power-ups-surge-it-power-distribution/backup-power-ups/eaton-ups-fundamentals-handbook-en-us-2025.pdf) gives the balanced three-phase VA convention. Formulas already present in the repository are retained; no new standards-compliance or field-accuracy claim is introduced.

## State and ordering

State schema stored-reading-state-1.0.0 contains binding (asset/source/run, configuration version, parameter version, model version), last_measurement_time, last_reading_identity, thermal initialization/validity/temperature/reason, and held_inputs (last thermal K and ambient). It contains no original payload, scenario labels or evaluation truth.

| Situation | Implemented rule |
|---|---|
| First usable frame | Require usable current triplet, ambient and oil plus all coefficients. Store observed initial oil; return prediction/residual null on bootstrap. |
| Initial evidence incomplete | Advance processed watermark if eligible; retain uninitialized state. A later eligible fully usable frame can explicitly establish the first observed initial condition. |
| Elapsed interval | UTC measurement-time difference only; hold **previous** usable load/ambient over it. Current sample prepares the next interval. |
| Missing current/ambient now | The preceding interval can still be predicted if its held inputs were known. Store null held input; the next unknown interval invalidates thermal continuity. |
| Missing oil | Continue load/ambient-driven prediction; residual unavailable. Do not assimilate oil when it returns. |
| Gap >300s | Invalidate thermal history; prediction remains unavailable on later frames until explicit replay/cold start. Exactly300s is allowed. |
| Equal/out-of-order time | No forward state advancement or thermal prediction; return unchanged prior state with reason. |
| historical_only | Never create/advance forward state, even if timestamp would otherwise advance. |
| Reused reading identity with changed time | ValueError; stored immutable identity is inconsistent. |
| Stream/config/model/parameter change | ValueError before state mutation; choose the corresponding state namespace or deliberately cold-start/replay. No automatic state migration. |
| Retry with current persisted state | Same/equal timestamp cannot advance twice. Repeating the same request with the same pre-call state returns an identical result. |

The pure function cannot prevent two concurrent workers from reading the same old state. **Person A must** lock/serialize the stream state; claim jobs idempotently; recheck the processed watermark under that lock; atomically commit result, returned state and job completion; and publish only committed results. After rollback, retry with the actual persisted state, never an uncommitted in-memory update. Store a unique result key using reading ID/model/parameter versions. Preserve committed results for duplicate job completion. This is not an exactly-once transaction implementation.

Scope state storage by asset/source/run/config/model/parameter version. Maintain a stream processing watermark across version transitions so choosing a new namespace does not accidentally permit historical jobs to move the live stream backward. Cold starts must be deliberate and audited; old incidents/results belong to D's history and must not be erased. This function neither claims jobs nor writes status/persistence/events.

## Actual tests

Python3.12, isolated temporary local PostgreSQL database sentinel_test, A's fresh-schema fixture and migrations. No .env, application database, Docker volumes or Person A's remote/local data were changed.

1. On exported simulator55a9c54 (no branch merge): `TEST_DATABASE_URL=<isolated _test URL> <analytics-venv-python> -m pytest backend/tests -q --tb=short --maxfail=3`: **115 passed**.
2. On analytics checkout: `SIMULATOR_REVIEW_ROOT=<exported 55a9c54 root> TEST_DATABASE_URL=<isolated _test URL> .venv/bin/python -m pytest backend/tests analytics/tests -q --tb=short --maxfail=3`: **161 passed**, no skipped tests. Breakdown87 backend +33 preserved B tests +30 worker +8 schema +3 simulator compatibility. Upstream Starlette/Alembic deprecation warnings did not fail checks.
3. Targeted worker/schema command: `.venv/bin/python -m pytest analytics/tests/test_worker.py analytics/tests/test_worker_schemas.py -q --tb=short --maxfail=3`: **38 passed**.
4. `.venv/bin/python -m analytics.examples.generate_worker_examples`: produced actual-execution test fixtures and schemas, which were validated and recomputed byte-for-value in the schema test.

Numerical cases cover units/conventions, partial/missing versus zero, bad/suspect/invalid channels, initialization, closed-form exponential response, partition equivalence, interval convention, residual signs, oil loss, unknown-history latch, gap boundary, UTC offsets, isolation, serialization, retries/equality/late times, historical jobs, configuration/parameter/model/state changes, null outputs and reason paths. Generator/API tests prove ingestion compatibility and deduplication, not physical prediction accuracy. Existing synthetic evaluation remains legacy consistency evidence and is not presented as independent validation. **No independent measured validation data is available.**

Install test-only dependencies with `python -m pip install -r analytics/requirements-test.txt`. Runtime has no new dependency. Without the simulator merged, the three simulator-specific tests require the explicitly reviewed snapshot path; otherwise they explicitly skip rather than fabricate integration.

## Supported behavior versus proposals requiring agreement

Supported now: exact callable above, A's implemented input schemas and channel quality mapping, eight output categories, null unsupported estimates, versioned state/ordering checks and numerical tests.

Still proposed: selecting this entrypoint as the worker default; concrete subfield types replacing proposed confidence/health numbers with unavailable results; max_load_pct meaning capacity loading versus phase current; previous-sample hold; continuity horizon300s and stricter model-usability ranges; immutable thermal coefficient/profile selection and provenance; version-transition replay/reset policy. Shared contracts were not silently rewritten as accepted agreements.

A/D still own job claiming, model-state/result tables, completion/error statuses, persistence/outbox, container copying of analytics and CI inclusion. C consumes explicit availability and provenance. No worker, job completion, alert publication, maintenance service, new forecast/what-if service or frontend integration is added here.
