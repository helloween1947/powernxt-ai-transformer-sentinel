# Person B durable worker computation handoff

Reviewed 9 October 2026 against main `59f9604` (simulator plus correctness fixes), without merging it into `feature/personb-twin-analytics`. No applicable AGENTS.md was found. The initial analytics working tree was clean. A's stricter configuration validation and immutable-history migration were inspected; their JSON field layout remains compatible. Only B's analytics and handoff documentation are changed.

## Exact callable interface

Runtime is Python 3.11+ and standard library only, with no HTTP, database, polling, job claiming or clock dependency:

```python
from analytics import compute_analytics, process_stored_reading

def compute_analytics(
    normalized_telemetry: dict,
    asset_config: dict,
    quality_flags: dict,
    reading_id: int,
    previous_state: dict | None = None,
    *, state_policy: str = "forward_only",
) -> dict: ...

def process_stored_reading(
    stored_reading: dict,
    asset_config: dict,
    previous_state: dict | None = None,
) -> dict: ...
```

The normalized facade supplies the exact same computation as the existing stored-response adapter. `reading_id` is the persisted positive database ID; UUID4 delivery identity, asset/source/run, configuration version and timezone-aware measurement timestamp come from normalized telemetry. `asset_config` is the reading-bound immutable ConfigurationResponse, never a latest-config lookup. `quality_flags` is A's channel-to-reason-list mapping. `state_policy` is A's forward_only/historical_only restriction; the model independently checks its watermark.

```python
result = compute_analytics(
    normalized_telemetry=stored["normalized_telemetry"],
    asset_config=bound_configuration,
    quality_flags=stored["quality_flags"],
    reading_id=stored["id"],
    previous_state=saved_state,
    state_policy=stored["processing_job"]["state_policy"],
)
next_state = result["updated_state"]
```

Exact typed wire contracts: `analytics/schemas/normalized-input.schema.json`, `worker-input.schema.json` for the stored facade, and `worker-output.schema.json`. Both request schemas include the nullable state definition. Runtime also checks cross-field bindings not expressible by ordinary JSON Schema. Additional full TelemetryResponse metadata is ignored; raw payload and simulation labels never enter computation.

## Confirmed electrical decisions

Voltage means RMS line-line or phase-neutral volts according to bound configuration; current means RMS **line** amps. Both are on the configured primary or secondary side. No turns-ratio conversion or delta winding-current inference occurs.

| Output | Equation and required usable channels | Units |
|---|---|---|
| phase_loading_pct | Each 100 I_phase/I_rated independently | %; R,Y,B order |
| max_phase_loading_pct | Maximum of all three phase loadings; all currents required | % |
| thermal_load_pu | sqrt(mean((I_phase/I_rated)^2)); all currents required | pu |
| apparent_power_kva | LN: sum(V_phase I_line)/1000; LL: sqrt(3) mean(V_LL) mean(I_line)/1000; all voltages/currents required | kVA |
| capacity_loading_pct | 100 apparent_power_kva/rated_kva | % |
| magnitude imbalance | 100 max(abs(value-mean))/mean; all three values and nonzero mean | % |

LN is a sum of phase apparent magnitudes. LL is explicitly a balanced-system approximation under imbalance, not exact complex power. Neither establishes real power, reactive power, PF or sequence components. Those remain null.

**Decision for this interface:** max_load_pct checks **capacity_loading_pct**, matching A's simulator envelope interpretation. Worst-phase current loading is separately reported and must not silently use that same limit. Independent phase-current limits require a new agreed configuration field. Thermal heating uses **thermal_load_pu**, because constant-resistance copper losses scale with mean squared phase current; maximum current or apparent capacity would misrepresent that loss driver. Voltage-dependent core losses are not modeled.

Hand-calculated imbalanced case: LN230V, currents50/100/150A, rated100A/69kVA yields capacity100%, worst phase150%, K=sqrt(7/6), magnitude imbalance50%.

## Thermal and cadence decisions

Required positive finite registry parameters with exact dotted-path provenance:

- rated_kva (three-phase kVA), rated_voltage_v (configured RMS V), rated_current_a (line A), voltage_convention, measurement_side, cooling_type.
- thermal_parameters.rated_top_oil_rise_c (C), oil_time_constant_min (min), loss_ratio (rated-load/no-load loss ratio), oil_exponent (dimensionless).
- Every supplied parameter has assumed/simulated/nameplate/measured provenance. Unknown coefficients remain null; no demo fallback is applied. Operational limits are optional.

The retained simplified model is `target = ambient + rise*((1+R*K^2)/(1+R))^n` and `T_next = target + (T_previous-target)*exp(-dt/tau)`, with tau converted to seconds. Applicability and primary references are in `docs/person-b-analytics-handoff.md`. It assumes fixed effective tau and constant-resistance loss scaling, without winding dynamics, automatic cooling control or certified standards compliance. Coefficients need asset-specific measured calibration.

**300 seconds is an implementation continuity policy**, not an integration step, physical requirement or measured calibration result. The exact first-order solution correctly handles irregular dt for held inputs. The unverified assumption is that the preceding load/ambient sample represents the interval. This version permits 0<dt<=300s and refuses to bridge longer unknown histories. Changing that horizon requires a versioned policy change; do not resample or pretend every packet represents300s.

For A's one-minute simulator, differences in UTC measurement timestamps are60s. Previous load and ambient are held over that interval; current load/ambient become the next interval's inputs. Subsequent measured oil is **not** assimilated. Residual is current observed oil minus the independently propagated temperature, so the observation cannot fit away its own residual.

| Situation | Implemented behavior |
|---|---|
| First valid reading / no prior state | With all currents, ambient, oil and thermal parameters usable, store observed oil as initial condition; prediction and residual null on bootstrap. A deliberate cold start cannot establish pre-existing offsets. |
| Incomplete first reading | Advance eligible processed watermark, retain uninitialized thermal state; later complete evidence may initialize. |
| Missing/invalid/suspect oil later | Propagate prediction from known inputs; residual unavailable. Returning oil does not re-fit state. |
| Missing current/ambient now | Previous known interval can still propagate; store null held inputs. The next unknown interval latches thermal state invalid. |
| dt>300s | Latch thermal state invalid; later good readings do not silently repair missing history. A must explicitly cold-start or replay with justified evidence. |
| Equal/late timestamp, historical_only, explicit upstream stale | No forward advancement or thermal prediction; return unchanged prior state. Current-frame electrical evidence can still be available. |
| Configuration/parameter/model/state-schema change | Reject incompatible prior state with ValueError. A selects the correct namespace or deliberately resets/replays; no silent migration. |

## Quality and worker outcomes

Missing stays null; actual zeros remain valid. Producer suspect/bad/missing, any nonempty per-channel ingestion reason list, invalid numbers and model sanity violations exclude the channel. Inherited model-usability ranges are voltage0..2x rating, current0..10x rating, oil-50..200C, ambient-50..80C, level0..100%. These are transparent implementation assumptions, not protection limits. Unknown flags/channels fail validation. Explicit clamped excludes all channels; explicit stale stops state advancement. A's current API emits per-channel lists, not those optional global booleans.

Every metric has availability/reasons; individual phase loading can exist without complete total-power inputs. All-zero currents mean zero loading/power, with imbalance unavailable due to zero denominator. Missing thresholds yield null breached, not false. There are no numerical health/confidence assurances; counts describe coverage only.

`execution_status.status` retains computed/degraded/insufficient_data for older consumers. New `execution_status.outcome` gives A an explicit mapping basis:

| Outcome | Meaning / precedence |
|---|---|
| computation_error | Thermal arithmetic failed; finite null prediction/residual, invalidated thermal state and explicit reason. Highest precedence. A must decide whether to persist diagnostics or roll back/retry; it is not a successful thermal result. |
| insufficient_input_or_state | Non-advancing reading or missing current triplet; individual electrical diagnostics may remain available. |
| unsupported_configuration | Required thermal coefficients absent, with usable current triplet and advancing frame. Electrical results remain available. |
| completed | Electrical, prediction and residual results available; unsupported advanced quantities still remain null. |
| partially_available | Initialization, unavailable oil/voltage, thermal continuity loss, or another incomplete supported result. |

These are computation outcomes, not persisted job statuses. Structural/binding/state validation failures raise ValueError and return no result/state. Unexpected exceptions must also become worker computation failures, never job success. A must preserve transactions and record errors outside deterministic output. Strict finite JSON output is enforced; non-finite previous state is rejected. Identical inputs/config/state give identical outputs without mutation or processing-time timestamps.

## Versions, references and state

- Model ID: powernxt-electrical-top-oil; model version: stored-reading-top-oil-1.0.1.
- Result schema version: stored-reading-result-1.1.0 (adds model_id and outcome).
- State schema version: stored-reading-state-1.0.0; binding includes model version, so1.0.0 model state requires explicit reset/replay for1.0.1.
- Parameter identifier: asset-config-VERSION:SHA256 over the bound JSON config excluding created_at, including provenance. It is not a measured calibration score.

Result references durable reading ID/message UUID, asset/source/run, UTC measurement time, configuration version, parameter fingerprint and model identity. Explicit units and method/convention accompany outputs. State includes schema/binding, last_measurement_time, last_reading_identity, thermal initialized/valid/oil/reason and held thermal K/ambient. It contains no payload labels or wall-clock processing time. Serialize with strict JSON and restore exactly; do not reinterpret it as legacy adapter state.

## Executed example input, previous state, result and next state

`analytics/examples/worker-test-examples.json` contains actual sanitized module executions. Each case has exact input (including previous_state), bound configuration, full result and updated_state. These are numerical tests, not admitted telemetry or measured physical evidence.

```python
import json
from pathlib import Path
from analytics import compute_analytics

case = json.loads(Path("analytics/examples/worker-test-examples.json").read_text())["examples"][1]
request = case["input"]
stored = request["stored_reading"]
previous_state = request["previous_state"]  # Observed bootstrap oil55C at00:00Z.
result = compute_analytics(stored["normalized_telemetry"], request["asset_config"],
                           stored["quality_flags"], stored["id"], previous_state)
assert result == case["output"]
next_state = result["updated_state"]
```

The example uses LL11000V/52.49A, ambient30C, initial oil55C, observed next oil60C at00:01Z; assumed rise40C/tau180min/R5/n0.8. Expected prediction is `70-15*exp(-60/10800)` C; residual is `60-prediction` C. Next state stores predicted oil and current held inputs, not observed60C. The third example explicitly shows absent thermal parameters.

## Actual validation and remaining limits

Commands run with Python3.12 and preserved isolated PostgreSQL sentinel_test; no .env, app database, volumes or A's Windows instance was touched:

1. `.venv/bin/python -m pytest analytics/tests/test_worker.py analytics/tests/test_worker_schemas.py analytics/tests/test_worker_handoff.py -q --tb=short`: **57 passed**.
2. On analytics feature branch, `SIMULATOR_REVIEW_ROOT=/private/tmp/personb-worker-main-59f9604 TEST_DATABASE_URL=<isolated URL> .venv/bin/python -m pytest backend/tests analytics/tests -q --tb=short --maxfail=3`: **180 passed**, none skipped.
3. On exported current main59f9604 with only B's analytics copied into the temporary export, `TEST_DATABASE_URL=<isolated URL> <feature-venv-python> -m pytest backend/tests analytics/tests -q --tb=short --maxfail=3`: **221 passed**, none skipped. This proves tested compatibility without a Git merge. Upstream Starlette/Alembic deprecation warnings remain.
4. Example/schema generator executed successfully; schema tests validate and reproduce examples.

Additional19 tests cover both sides/conventions, hand-calculated imbalanced drivers, dt1/59/60/61/137/299/300, the five outcomes including overflow, direct facade/schema equivalence, immutability and non-finite state rejection. Previous tests retain gaps, quality/zeros, residuals, bootstrap, serialization, run isolation, duplicate/late/historical policy and configuration/model transitions. Simulator/API cases establish six-reading ingestion/retry compatibility, not model accuracy. No independent measured temperature/load dataset or asset calibration is available; no accuracy/RMSE claim is made.

## Person A responsibilities and remaining agreement

A must implement job claiming/leases/polling, input/config loading, ordered per-stream state locks, durable result/state storage, retries and atomic result/state/job completion; persist processing time outside model output; and publish only committed results. A must honor admission state_policy and recheck a stream watermark under lock. Unique reading/model/parameter result keys plus atomic persistence prevent double advancement. Rollback retries reload committed state; duplicate completed jobs return committed results. Preserve a stream watermark across config/model namespaces so cold-starting a version does not resurrect historical jobs. A/D own migration, deployment copying and CI discovery. No scheduler, API or UI is added here.

B confirms channel/side/convention, separate loading metrics, capacity-limit interpretation, previous-sample hold and actual measurement dt for this version. Shared contract documents remain proposed; this handoff does not silently assert cross-team agreement. A must acknowledge the phase-current limit need, the300s policy and reset/error-persistence choices. Scientific work still needed: measured asset coefficients and independent transient validation, uncertainty calibration and applicability to cooling regimes. Forecasts, what-if services and additional fault models are deferred.
