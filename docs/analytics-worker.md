# Durable analytics worker

This branch adds a separately runnable PostgreSQL worker, committed result APIs and a narrow Person B computation adapter. It does not deploy the existing development stack. Ingestion remains transactional and never starts polling or computation inside API requests or FastAPI startup.

## Computation source and supported physics

Person B's unmerged `feature/personb-twin-analytics` was inspected at **637fbe810714d0d5c403728ddf7bcba746ea55a9**, rather than the older 35a8c64 prototype. Main base is **59f960432168dbe62e96ba6f107ce5ae92c323df**. Person B owns the electrical/top-oil computation. `backend/app/analytics/person_b/SOURCE.json` records attribution and source hashes. Only the stored-reading worker and its needed normalization/physical primitives were extracted; worker imports point to those primitives. No prototype APIs, health-score computation, anomaly lifecycle, forecasts or entire teammate branch were merged. Supplied executed examples are reproduced exactly by tests.

Model: `powernxt-electrical-top-oil`, version `stored-reading-top-oil-1.0.1`; computation result schema `stored-reading-result-1.1.0`, state schema `stored-reading-state-1.0.0`. The API envelope is separately versioned `1.0.0`. Inputs are normalized telemetry, ingestion channel reasons, durable reading ID, exact immutable reading-bound ConfigurationResponse, previous state and admission/worker state policy. Raw payload and simulation ground truth are excluded.

RMS line currents use the configured side. Voltages use configured LL or LN; there is no turns-ratio or delta winding-current inference. Capacity loading uses apparent power/rated kVA, and `max_load_pct` applies to that metric. Worst-phase loading is separately reported. An independent phase-current limit needs a future agreed configuration field. Thermal load is RMS per-unit current across the three phases, reflecting mean squared current loss. LL apparent power uses the balanced-system approximation `sqrt(3)*mean(V_LL)*mean(I_line)/1000`; LN uses `sum(V_phase*I_line)/1000`. Neither derives PF, real/reactive power or sequence components; those outputs remain null.

Top-oil evolution uses explicit positive finite rise, oil time constant, loss ratio and exponent from the bound configuration with exact provenance. Unknown parameters are not filled with simulator defaults. The separately named `asset-configuration-worker-assumed.json` is a demonstration containing **assumed**, uncalibrated coefficients (rise40C, tau180min, R5, n0.8). It does not change existing sample configurations.

Person A adopts B's supplied decisions for this version: previous-sample zero-order hold, **actual UTC measurement-time elapsed seconds**, and **0 < dt <= 300s** continuity policy. The 300-second horizon is an implementation refusal to bridge uncertain history, not a physical integration step or measured calibration. A first usable oil sample provides the initial condition; bootstrap prediction/residual are null. Later observations do not assimilate into predicted state. Missing oil permits propagation with a null residual. Missing held load/ambient invalidates the following interval; gaps over300s latch thermal state invalid. Later good samples do not repair that namespace. Reset requires an explicit new run/configuration/model transition or a future reviewed replay/reset workflow; no manual reset API is introduced.

These are simplified uncalibrated first-order predictions with fixed effective tau/constant-resistance loss scaling. They do not implement automatic cooling control, winding dynamics, calibrated accuracy, certified IEEE compliance or numerical confidence. Measurement usability checks and configured threshold comparisons are transparent diagnostics, not alerts or maintenance instructions. No scientific loading/cadence decision remains blocking after B's supplied handoff; asset calibration, independent transient validation and future phase-current limits remain open work.

## Jobs, claims and recovery

Jobs transition `pending -> processing -> completed|unavailable`, or `processing -> retry -> processing`, then `failed` at the configured attempt bound. Claims use PostgreSQL row locks with SKIP LOCKED in short transactions, persisted UUID tokens, attempt counts and database-clock leases. Defaults:60s lease,3 attempts,1s idle polling. Error retries delay1s then2s (general exponential cap300s). Worker processes one claim at a time; scale processes for concurrent independent streams. Every worker on a stack should use the same attempt/lease policy.

A durable stream row `(asset_id,source,run_key)` has one active lease. There is no concurrent state evolution within that stream, even across configuration/model namespaces. Computation runs outside database locks. Before persisting, the worker locks job and stream, checks both ownership tokens and unexpired leases, then atomically writes the result, returned model state, global watermark and terminal job status. It checks the database clock again after writes before commit. Unique `(reading_id,model_id,model_version,parameter_version)` result identity independently prevents duplicates. A rollback leaves state/result/job changes uncommitted, so retries reload committed state.

SIGTERM/SIGINT stop new claims after finishing the current bounded computation. Compose grants70s. A hard crash leaves a claim recoverable after its lease. There is **no lease heartbeat**: computations exceeding the configured lease cannot commit and eventually fail after bounded attempts. Increase the documented lease only if the workload requires it; do not run long computations under the default while expecting unlimited renewal.

Expired ownership cannot write successful results or release a newer owner's claim. Exhausted expired jobs become failed with `lease_expired_attempts_exhausted`; later jobs can proceed. Persisted errors are bounded machine codes (`invalid_computation_input`, `thermal_computation_error`, `worker_computation_error`), never arbitrary exception text or payload/credential dumps. B's `computation_error` causes rollback/retry; partial failed calculations/state are not committed. Terminal failed jobs have no fabricated result. Fixing a failure does not automatically requeue a terminal job; an administrative retry workflow is outside this task.

`completed` means deterministic computation was stored, not that every physical quantity is available. It covers bootstrap, partial results and unsupported thermal configuration with usable electrical channels; inspect `execution_status.outcome` and per-metric availability. `insufficient_input_or_state` maps to `unavailable` while preserving any electrical diagnostics. Missing/invalid/suspect input never becomes a fabricated zero. Actual zero current remains zero.

## Ordering, watermarks and transitions

Within currently visible nonterminal jobs in one stream, measurement time ascending then reading ID ascending chooses the earliest. A delayed retry blocks subsequent jobs **only in that stream**. Jobs from other streams can proceed. This is not strict event-time ordering: there is no holdback window or knowledge of future late arrivals.

Admission `historical_only` is never relaxed. The worker additionally requires measurement time strictly greater than the durable stream watermark. Equal/older readings may store frame-local electrical evidence but cannot predict forward temperature, advance state, or rewind the watermark. Equal-time latest completed results break ties by reading ID, then result ID; a nonadvancing equal-time result is unavailable and therefore excluded from latest completed analytics.

State namespaces include asset/source/run, model ID/version, configuration version and the fingerprint of the immutable bound ConfigurationResponse (excluding created_at; provenance included). A stream-global watermark survives namespace changes. Every configuration/model identity transition deliberately cold-starts thermal state, including returning to a previously used configuration. Existing namespace history remains stored; its counter counts advances, and the state snapshot records the most recent committed evolution/reset. Cold-starting never makes an older reading eligible. Device/replay/simulator runs never share state.

Existing pending backlog is retained and picked up when this opt-in worker starts. Each reading uses its attached configuration, not the latest one. Existing admission historical restrictions survive. Failed/completed jobs are not implicitly replayed on model upgrades. No backlog cutoff, wall-clock stale reclassification, resampling, deletion or fabricated history is introduced.

## Storage, migration and operations

Migration **d730a91b4c22**, parent **ce21c3b8140a**, adds stream/state/result tables plus claim/retry columns and index, and broadens the old pending-only job constraint. Existing records stay intact with pending status, zero attempts, null lease/error and immediate eligibility. PostgreSQL tests compare all pre-existing columns across populated upgrade and check schema consistency. Downgrade is permitted only before any worker history exists; otherwise it refuses rather than deleting analytical records. Roll back application images with the additive schema retained; do not remove results/state to make downgrade succeed.

After review, migrate **before** enabling worker or updated API. The old API cannot serialize new job states; stop old API writers, migrate, and start updated backend/worker together. Worker is opt-in under Compose profile `analytics`, preserving the existing ingestion-only workflow by default.

```bash
python -m backend.app.workers --lease-seconds 60 --max-attempts 3 --poll-seconds 1
# --once processes at most one eligible claim (useful for diagnosis).
docker compose --profile analytics up -d worker
# Multiple processes share the same database; no container_name prevents scaling.
docker compose --profile analytics up -d --scale worker=2 worker
docker compose --profile analytics logs --tail 100 worker
docker compose --profile analytics stop worker
```

Read job status/attempt/error through the reading result API; query processing-job lease fields for operations if needed. Failed analytics does not make database readiness false. Retain PostgreSQL volumes and evidence. See [API contract](contracts/analytics-contract.md), [Windows commands](analytics-worker-windows.md), [actual evidence](analytics-worker-verification.md), and [prepared PR](analytics-worker-pr.md).
