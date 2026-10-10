# Initial backend what-if contract 1.0.0

Model adoption follow-up: [A’s version dispatch and handover contract](person-a-model-102-adoption.md) supports immutable 1.0.1 and 1.0.2 states. Earlier verification below remains tied to its original tested source; see the separate adoption evidence for fresh checks.

Reviewed against main f52f56515c38fce55451fd499be81ef2508e6677. This is A's
reviewable implementation contract for C/B, not a claim of teammate approval or
deployment. Existing main has no supported what-if endpoint. No existing shared
contract is redefined. The old frontend prototype `/what-if` request using assetId
and alternative is incompatible and must not be silently reused.

## Model and supported scope

POST `/api/v1/assets/{asset_id}/what-if`, conditional simplified healthy-model
top-oil estimates only. No cooling interventions, unresolved-fault continuation,
diagnosis, health/confidence or physical-accuracy claim. Preserve deployed model
`powernxt-electrical-top-oil` / `stored-reading-top-oil-1.0.1`.

Reuse B's `forecast_from_worker_state` from f668a21, forecast
`healthy-top-oil-scenarios-1.0.1`, with imports adapted to the existing physical
core/model constants. The constructor is extracted from B's code with explicit
four thermal coefficients. No model1.0.2 worker adoption occurs. Provenance and
original file hashes are in backend/app/analytics/person_b/WHAT_IF_SOURCE.json.
This function explicitly supports constant-input durations up to 24 hours using
the pure exponential thermal evolution; the worker's 300-second admission gap
does not govern a deliberate future constant-input scenario.

Bounds established by B's pure code: `thermal_load_pu` inclusive0–10;
`ambient_temperature_c` inclusive−50–80 C. These are computational admissibility
bounds, not proven safe operating ranges or calibrated load capability.

## Exact request

```json
{
  "schema_version": "what-if-request-1.0.0",
  "source": "simulator",
  "run_id": "<actual-run>",
  "state_ref": null,
  "baseline": {"duration_s":3600,"thermal_load_pu":1.5,"ambient_temperature_c":30},
  "reduced_load": {"duration_s":3600,"thermal_load_pu":0.75,"ambient_temperature_c":30}
}
```

Both named scenarios are required, exactly one constant segment each. Durations
must be equal, greater than zero and at most86400 seconds. Reduced load must be
less than or equal to baseline. Ambient must be equal between scenarios: this
initial API isolates load effects and rejects confounded ambient comparisons.
Numbers must be finite JSON numbers, never booleans or numeric strings. Unknown
fields are rejected at every level, including worker state, model parameters,
cooling factor, measured future oil, sampling options or fault labels.

`source` is device/simulator/file_replay. Device requires absent/null run_id;
simulator/replay require nonblank run_id of at most100 characters. Optional
state_ref is a server-issued opaque UUIDv4, returned in prior responses. It is
not a reading/result/message ID. Omit/null it to select/capture current state.

## State selection and immutable snapshots

The existing analytics_states cache changes on worker advancement. Result
payloads contain updated_state, but existing result storage has no database
append-only protection. A reading/latest result endpoint is therefore not
advertised as an immutable historical state API.

With no reference, the server takes the worker's stream row lock in shared mode
and resolves its current namespace and committed watermark reading. The worker
claims readings by ascending (measurement_time, reading_id), and advances only
when measurement_time exceeds the stream watermark. Equal/late readings do not
replace that state; there is no second historical sort or fallback to an older
apparently healthy state. The exact model/parameter result for that reading must
match the cached state's JSON content. Asset/source/run, reading/message,
configuration/model/parameter identities and measurement timestamps are checked.
The same immutable reading-bound configuration is used for both scenarios,
even when a newer configuration was registered but has not produced this state.

Eligibility requires compatible state schema, explicit complete thermal
parameters, valid initialized finite thermal state, completed forward analytics
and matching identities. Observed bootstrap is eligible but identified as an
initial condition, not an independent prediction. Missing parameters or an
invalid latest state reject the request; no earlier state is silently substituted.
The origin timestamp is the latest committed forward state measurement time.
A claim computing outside locks may exist: the API uses its preceding committed
state. Pending telemetry, arrival time and wall-clock freshness do not redefine
the origin. Clients must display the origin and avoid implying freshness.

The server inserts an immutable `what_if_snapshots` capture, UUIDv4 and unique
per exact result ID. Concurrent captures reuse the same reference. Its insertion
guard binds full state and stream/config/model/time to the actual stored result;
UPDATE/DELETE are rejected in PostgreSQL. No historical reconstruction or backfill
is performed. Existing initialized caches can be captured immediately after
migration, provided the stored result matches. Capture commits only on successful
calculation/response validation; failures roll it back.

An explicit reference selects only its immutable captured state/configuration,
with authoritative asset/source/run/model identity checks. It remains reproducible
after future worker advancement or configuration changes and does not reread a
mutable cached state/result payload for calculation. Explicit historical captures
are allowed; their original timestamp stays visible. Each comparison uses one
snapshot and one configuration for both scenarios. The sole API write is that
optional capture: no jobs, worker changes or result/configuration rewrites.

## Sampling, peaks and configured limit

For horizon H, N=max(1,min(96,ceil(H/60))) intervals (the minimum also guards
floating-point division underflow for very small positive durations). Emit N+1 points, initially t=0 and
then uniform t=iH/N, with the final time explicitly H. Maximum97 points per
scenario. Every point is evaluated from the same initial state with B's pure
constant-segment function, avoiding accumulated stepping/cadence errors.

`peak_top_oil_temperature_c` includes the initial state and final endpoint. The
constant-segment exponential is monotonic (or constant), so this is the continuous
segment maximum rather than an undersampled interior maximum.

Only the bound configuration's `operational_limits.max_top_oil_temp_c` applies.
Never use B's legacy default warning temperature or a client-supplied limit.
Limit provenance is retained. Crossing means estimated temperature >= limit;
initial equality/exceedance yields0. Heating crossing is computed analytically
by B's exponential solution, independent of chart sampling, including equality
at the final endpoint. A limit at the exact equilibrium approached from below
has no finite crossing. Clamp floating endpoint spill to [0,H]; no rounding is
applied before comparison. IEEE754 double precision and configured parameter
precision apply; these are not physical precision guarantees.

- `crossing`: time_s is calculated seconds, possibly0.
- `no_crossing_within_horizon`: applicable limit exists; time_s null, no reasons.
- `unavailable`: limit null; time_s null; reason configured_top_oil_limit_missing.

Missing limit does not prevent supported temperature estimates. Missing model
parameters or unsupported state does prevent computation and returns an error,
never a successful fabricated numeric forecast. Final difference is exactly
reduced_load_final_c minus baseline_final_c; a negative value means lower
estimated final top-oil under the same conditional assumptions.

## Response and errors

Response schema `what-if-response-1.0.0` contains named baseline/reduced_load,
their explicit inputs, elapsed_s/estimated_top_oil_temperature_c points, final,
peak and limit_crossing. It includes final_temperature_difference_c, state_ref,
reading/result identities, UTC measurement/capture timestamps, immutable asset
configuration version/created_at/parameter reference, model/forecast versions,
units, full parameter provenance and assumptions. Serialized worker state and
thermal coefficient values are not returned or accepted.

Errors retain FastAPI's existing `detail` envelope, adding versioned bounded codes:

```json
{"detail":{"schema_version":"what-if-error-1.0.0","code":"state_unavailable","message":"No committed forward state exists for this stream","reasons":[]}}
```

| HTTP | Code | Meaning |
| --- | --- | --- |
| 422 | invalid_request | Malformed/nonfinite JSON, booleans/numeric strings, extra fields, unsupported request version, invalid bounds/scenario relationships/source/run/UUID |
| 404 | asset_not_found | Unregistered asset |
| 404 | state_not_found | Unknown explicit opaque reference |
| 409 | state_unavailable | No current committed forward state |
| 409 | incompatible_state_identity | Wrong asset/stream/config/model, corrupt namespace/state or mismatched cache/result |
| 409 | ineligible_state | Uninitialized/invalid thermal state or unavailable result origin |
| 409 | missing_model_parameters | Missing required thermal coefficient keys listed in reasons |
| 422 | computation_unavailable | B's supported arithmetic cannot produce finite output; no numeric response/capture committed |
| 503 | database_unavailable | Database operation failed; pending capture rolls back |

Raw request, state, exception or driver details are never echoed. This route uses
the existing main API's deployment access policy; it does not treat demo actor
headers as identity or add authentication capabilities absent from main.

Migration w001_what_if_snapshots extends current main's D004 without editing old
revisions or data. A populated snapshot table refuses downgrade. A's separate
unmerged incident A001/A002 branch has an independent migration path; if both
are incorporated, inspect the actual graph/schema and add an explicit reviewed
join rather than silently rewriting either parent.

Verified execution examples and C's JavaScript consumption instructions are
provided in docs/person-c-what-if-handoff.md and data/sample/what-if-verified.json.
These are synthetic isolated test evidence, not field validation or deployment.
