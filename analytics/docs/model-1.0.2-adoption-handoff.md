# Model1.0.2 adoption handoff — 10 October 2026

This is Person B's technical recommendation for A, not A/D/C approval or an
implemented backend upgrade. No equations, coefficients, tuning or runtime code
changed during this alignment task. PR24 already includes PR17 lineage: adopt
one reviewed contribution, not two copies.

## Current sources, resolved after fetch

| Ref | Full SHA |
| --- | --- |
| main | cbdd7c47f8cf5aa66d0277f5fa96d69bfb01ddda |
| feature/personb-detector-orchestration before this review commit | f668a21dcf88605d7fcff4996282185bc796740c |
| feature/persona-incident-registry | 2e934c85098453db7342ea6ade570759ef4b9161 |
| feature/persona-detector-handoff-review | cf2eb252a5e405d4991e82b86db13c49822977fb |
| feature/persona-what-if-api | 20ccaddcecd55695b79d257a02f25a68ec691462 |

The registry branch has advanced since the historical audit: it now incorporates
What-if, D's genuine task work and a combined migration revision. Inspection
found no change to incidents.py, analytics_worker.py or the pinned handover
schema versus cf2eb25. This review does not deploy or independently certify the
combined migration graph. Main has adopted alignment CI/documentation; its
backend remains the conservative1.0.1 source. Do not interpret branch existence
as a running service. Current repository CONTRIBUTING was read; merge still
requires teammate review and passing CI.

## Exact computation source and adoption map

Executable source remains exactly
**f668a21dcf88605d7fcff4996282185bc796740c**. Every source/contract entry in
[model-1.0.2-adoption-manifest.json](model-1.0.2-adoption-manifest.json) was
checked against both that Git object and the current working file. The new
alignment commit adds tests/docs only. Its full SHA is supplied with PR24;
there is no circular self-SHA embedded in this file.

| B source | A reconciliation target / requirement |
| --- | --- |
| analytics/worker.py | backend/app/analytics/person_b/worker.py; adapt imports, preserve both callable signatures and new model version |
| analytics/normalization.py | vendored normalization.py; replace old AST extraction from legacy adapter with this reviewed quality policy |
| analytics/validation.py | vendored validation.py and scenario_validation.py as appropriate; preserve strict state/quality validation and compatible detector imports |
| analytics/transformer_twin/model.py | vendored core.py extraction of finite, AssetConfig, ThermalState, _advance; keep conservative worker independent of legacy scores/heuristics |
| analytics/transformer_twin/engine.py | reviewed _timestamp extraction in core.py; transplant guarded UTC conversion, not legacy live engine orchestration |
| analytics/transformer_twin/__init__.py | import dependency reference if retaining package layout; A currently extracts core definitions instead |
| analytics/persistence.py and incident_orchestration.py | preserve detector/planner compatibility and exact source provenance; no new incident identity allocation in B |
| analytics/scenarios.py plus worker._thermal_core | reconcile scenarios.py/scenario_core.py with version-specific worker/core; do not silently import global1.0.2 into historical1.0.1 execution |
| analytics/schemas/{worker-input,normalized-input,worker-output}.schema.json | retain conservative contract checks, state1.0.0/result1.1.0 and explicit model identity; A's worker-output.schema.json must match supported result validation |
| analytics/examples/worker-test-examples.json | exact1.0.2 fixture/provenance; retain separate historical1.0.1 examples |
| analytics/contracts/incident-proposal.schema.json | existing merged evidence shape; no silent shared-contract replacement |

A must reconcile adapter.py MODEL_ID/MODEL_VERSION selection, worker namespace
lookup, final result validators, schemas/incidents.py Control model whitelist,
What-if resolver/validators and SOURCE.json/INCIDENT_SOURCE.json/WHAT_IF_SOURCE.json
together. The planner's support for both model versions does not mean the
control whitelist or vendored computation supports1.0.2: current Control pins
stored-reading-top-oil-1.0.1. A should record original source hashes and adapted
file hashes/import/extraction differences, not pretend vendored files are byte
copies. Model version is stored-reading-top-oil-1.0.2; model ID remains
powernxt-electrical-top-oil. No result/state schema bump or coefficient change is
proposed. Parameter identity keeps the reviewed immutable-configuration hashing
algorithm; recompute from exact reading-bound config, never invent a fingerprint.

## Recommended handover: recorded cold start

1. A prepares a reviewed integration commit, explicit1.0.2 whitelist/support and
   historical What-if policy. Recheck actual deployment sources before switching.
2. Serialize per asset/source/run under A's stream fence/control protocol. An
   unexpired lease must complete or return stream_busy. Expired claims cannot
   commit after handover. Resolve the real immutable configuration and policy.
3. Record trusted admin actor, reason, expected control version/idempotency key,
   boundary measurement watermark, prior namespace and newly allocated durable
   UUID4 control epoch. New computational namespace is
   (asset,source,run,model ID,model1.0.2,configuration version,parameter version).
   Detector state is separately epoch/policy/detector-bound. Distinguish these
   namespaces from canonical incident IDs and result/reading IDs.
4. Archive previous cache/state, namespace, advance count and update time before
   replacing any same-key cache. Preserve old state rows, results, snapshots,
   evidence and original model/parameter/configuration/provenance labels. Do not
   edit old state's model_version to make it acceptable: that is not migration.
5. Preserve old active incidents as condition active / monitoring interrupted,
   with an auditable handover event. Preserve acknowledgements and tasks. Never
   infer physical recovery, acknowledge an incident or complete a task.
6. Set new twin/context to no prior state. Keep the boundary watermark: late/equal
   readings remain nonadvancing historical work, not a new bootstrap. First
   eligible later reading with usable currents/ambient/oil and explicit thermal
   coefficients initializes from observed oil. Prediction/residual are null with
   initialized_from_measurement_prediction_not_independent. Missing required
   channels/parameters remain explicitly unavailable; no default is supplied.
7. Next eligible forward reading within300s advances the healthy estimate using
   the preceding sample's held K/ambient and actual measurement-time dt. Residual
   equals current measured oil minus that independent estimate. At300s it is
   eligible; beyond300s continuity is invalid. Missing interval inputs or invalid
   history cannot be silently restored. Detector timers begin fresh; durable
   failed/skipped barriers preserve active identity without inferred recovery.
8. Atomically commit result/twin/context/incident evidence/event checkpoint/job
   completion under the final fence. Retry from the same prestate is deterministic;
   A's uniqueness/fencing prevents double advancement/publication. A supplies new
   canonical UUIDs for new episodes in the new epoch. Reprocessing terminal jobs,
   backfill and installing replay state need a separately approved A workflow.

Pure tests exercise old-binding refusal, preservation, bootstrap and the next
step. They do not implement admin handover, archives or database atomicity.

## Historical What-if: recommendation and alternative

**Recommend version dispatch** keyed by captured model ID/version, supported
state/result schemas and forecast version, with exact immutable config and
parameter fingerprint verification. Retain reviewed1.0.1 worker/core/validation/
scenario package and1.0.2 equivalents behind explicit server allowlisting.
Do not share a mutable global MODEL_VERSION between them or import a callable
path supplied by the client. Existing snapshots use1.0.1; new1.0.2 captures use
1.0.2. Return the executed version/forecast identity, original timestamp and
original provenance. Dispatch retains reproducibility and old references but
costs two audited implementations and test coverage. Preserve known1.0.1 finite
arithmetic failure behavior as an explicit error; do not patch old captures or
silently substitute1.0.2. All successful outputs must still pass strict JSON.

Alternative: support only1.0.2 execution and reject historical1.0.1 captures with
an explicit versioned unsupported-model response. Simpler maintenance, but old
What-if links stop computing after adoption. Captures must remain stored/readable
with their original labels. Proposed HTTP409/code unsupported_model_version is
**not currently in A's what-if-error-1.0.0 enum**: A must decide and document the
error-contract version/compatibility. Current code instead rejects mismatched
versions as incompatible_state_identity. Neither option rewrites immutable
captures, changes their state_ref or fabricates a new parameter fingerprint.

Required A tests before adoption (not implemented by B's pure tests):

- Exact old1.0.1 capture output reproduces after default worker switches to1.0.2,
  or returns the agreed unsupported error with no numeric substitution.
- New1.0.2 capture dispatches1.0.2; no response relabels1.0.1 computation as1.0.2.
- Unknown versions, model/schema/parameter mismatches fail closed with bounded
  errors; corrupted capture is not fixed by changing its version string.
- Old reference remains stable after state/config changes, retries and restarts;
  both scenarios share one snapshot/config; database captures cannot update/delete.
- Unsupported/arithmetic-failing requests do not commit a new capture or touch
  jobs/state/results/incidents/tasks. Assert finite JSON for every successful path.
- Handover archives old state, preserves incident/ack/task axes, rejects stale
  claims and never replays terminal jobs automatically. Test unmonitored streams'
  explicit namespace transition as well as opted-in detector controls.

## What-if semantics confirmed against current A code

POST /api/v1/assets/{asset_id}/what-if accepts two named constant scenarios,
baseline and reduced_load. Equal ambient and duration are required, reduced
K <= baseline K, duration in (0,86400]s, K in [0,10]pu, ambient in [-50,80]C.
HTTP ambient_temperature_c maps to Python ambient_temp_c. Reject unknown fields
and invalid/missing state rather than select older healthy-looking history.

Sampling: N=max(1,min(96,ceil(H/60))) intervals, N+1 <=97 points including origin
and exact horizon. Each point uses the same initial state with the analytical
constant-input evolution. Monotonic endpoints give continuous peak. Limit
crossing means >=; initial equality/exceedance gives0s; heating crossing is
analytical within the horizon, clamped only for floating endpoint spill. A limit
approached only asymptotically gives no finite crossing. Missing configured limit
is unavailable, distinct from no_crossing_within_horizon. Signed final delta is
reduced minus baseline in C. These computational bounds are not safe operating
limits or calibrated accuracy horizons. Restore cooling and health/RUL/confidence
remain illustrative/unsupported. No fault-aware action guarantee is provided.

## Fresh verification for this alignment commit

The model/core/normalization/validation/scenario runtime bytes are unchanged
from f668a21. Numerical hardening uses guarded finite arithmetic and null reasons;
equilibrium ambient+rise*((1+R*K²)/(1+R))^n and exponential time evolution remain
unchanged. Model-version/state-validation changes require the handover above.

Exact regressions now verify input preservation and availability as well as values:

| Input | Preserved results | Unrepresentable results |
| --- | --- | --- |
| All currents/rated current1e308 | phase loading [100,100,100]%, max100%, K1pu, current magnitude imbalance0% | apparent kVA and capacity loading null, electrical_arithmetic_unavailable |
| rated_kva5e-324, ordinary currents/voltages | same loading/K/imbalance, apparent1000.0688157821942kVA | capacity loading null, electrical_arithmetic_unavailable |

Strict json.dumps(..., allow_nan=False) passes. These extreme inputs are numerical
counterexamples, not acceptable physical asset specifications. Actual electrical
ratings must retain their registry provenance; A may separately propose validated
physical admission bounds, but none were invented here.

Fresh command from B's checkout, Python3.12:

```sh
.venv/bin/python -m pytest analytics/tests/test_audit_regressions.py analytics/tests/test_model_alignment.py analytics/tests/test_incident_orchestration.py analytics/tests/test_worker_scenarios.py analytics/tests/test_worker.py analytics/tests/test_worker_schemas.py analytics/tests/test_worker_handoff.py analytics/tests/test_persistence.py analytics/tests/test_twin.py -q --tb=short
```

**192 passed**. Includes independent analytical thermal expectations, quality/
units/nulls, model/config/run isolation, serialization, ordering/retries,
planner lifecycle/barriers and scenario crossing/invalid inputs. This is fresh
execution, not the earlier90-test count. Historical-dispatch tests above remain
A integration requirements; no dispatcher or backend adoption was implemented.

Current A branch checks and final publishing references are recorded in the
alignment report follow-up. Synthetic/analytical compatibility is not independent
measured predictive validation. Demonstration40C rise/180min/R5/n0.8 remain
assumed. No physical calibration, fault probabilities, scores or RUL claim.

## Concise checklist for A

- Confirm exact1.0.2 adoption commit/files/manifests and update all pinned validators.
- Confirm recorded cold-start epoch, archive/boundary/fencing behavior for each stream.
- Choose historical version dispatch (B recommendation) or explicit unsupported error.
- Preserve old captures/results/model/parameter/provenance and active interrupted incidents.
- Run the version-specific history/handover/error/no-write tests above and publish examples.

A owns final API/model-adoption/deployment decisions; no teammate messages or
review approvals are sent by this handoff.
