# Person B detector orchestration and configuration/model handover

Reviewed main `f2887902548212c4736ed69e9dd135c537c0d1c6`, merged PR15/21,
and D's PR22 head `0ee71b330a2ef2b7d272fd742e455b7b0e56f13a` on 9 October 2026.
This records B's concrete choices and supplies tested pure computation. A must
confirm/adopt the worker changes; no bilateral agreement, registry implementation,
trusted identity, acknowledgement endpoint or deployment is claimed.

## Selected orchestration

Use **A's existing fenced per-stream worker**, not an independent result consumer.
Compute analytics and detector decisions from one immutable reading/configuration
and a coherent committed state snapshot. A commits the result, twin state,
detector context/watermark, canonical mapping, evidence/history, outbox and job
completion atomically under the existing fencing checks. No publish-before-commit
callbacks, second independently ordered detector or automatic task creation.

The initial detector integration can retain A's deployed analytical model
`stored-reading-top-oil-1.0.1`; upgrading it to B's audited `1.0.2` is a separate,
recorded handover. The storage planner explicitly accepts either version with
model_id `powernxt-electrical-top-oil` and result schema
`stored-reading-result-1.1.0`. It does not convert results or silently upgrade the
thermal state. B's reviewed detector is `sustained-threshold-1.0.1`.
PR17 remains an adoption dependency for the reviewed detector/validation code;
this branch continues that work without changing A's vendored model.

Policy must be a persisted, explicit version/provenance/max_gap_s/rules snapshot
accepted by evaluate_persistent_rules. Hash its complete content. No default
thresholds or severity are inferred. The synthetic demo policy is assumed and
is not an approved asset-specific operating policy. If a deployment intentionally
uses it for a demonstration, record its assumed provenance and exact version.

## Callable planner and input contract

```python
from analytics import evaluate_incident_candidates
from analytics.incident_orchestration import IncidentPlanningError

try:
    plan = evaluate_incident_candidates(
        analytics_result=output,       # Actual conservative model output
        policy=immutable_policy,
        detector_epoch=saved_epoch,    # A's durably allocated UUID4
        result_id=reserved_result_id,  # A's allocated result identity, not incident ID
        previous_context=saved_context,
        continuity_break=unconsumed_failure_or_skip_barrier,
    )
except IncidentPlanningError as error:
    machine_code = error.code          # Bounded machine code; no raw payload logging
    # A rolls back/quarantines/retries according to the table below.
```

All arguments are explicit; previous_context defaults to null only for a newly
recorded epoch or an explicitly controlled replay. continuity_break defaults
false and accepts a boolean only. result_id must be a positive allocated integer;
do not pass a placeholder or a reading ID as a result/incident identity.
No database transaction, ORM object or original payload enters the computation.
No scenario or ground-truth label is inspected.

Previous context has exactly these semantic fields:

```json
{
  "schema_version": "incident-detector-context-1.0.0",
  "detector_epoch": "<durably allocated UUID4>",
  "detector_state": "<serialized evaluate_persistent_rules updated_state>"
}
```

The quoted detector_state above denotes an object, not a literal string value.
Its existing state schema is sustained-threshold-state-1.0.0. Binding includes
asset/source/run, configuration/model/parameter versions, detector version and
policy version/fingerprint. Epoch changes reject previous_context. Model/config/
parameter/policy changes reject a mismatched detector binding. A must independently
validate the context against its authoritative namespace and epoch record.

## Output contract and storage commands

Root fields:

| Field | Type and meaning |
|---|---|
| schema_version | incident-storage-commands-1.0.0 |
| detector_result | Existing pure sustained-detector output, including candidate events/current evidence |
| updated_context | Serialized context; null/unchanged for an ineligible sample |
| mutations | Ordered list of proposed canonical-registry operations; no canonical UUIDs allocated |
| continuity_break_consumed | Boolean; true only after eligible forward evaluation |

Each mutation contains kind, mapping_key, stream, category, severity and evidence.
mapping_key is `{asset_id, detector_epoch, detector_episode_key}`. B's internal
field named incident_id is renamed detector_episode_key here. A allocates the
canonical server UUIDv4 on an opening and binds it to the registered asset/stream.
Never substitute reading/result/message IDs, a detector key or event UUID.

| kind | A storage meaning |
|---|---|
| opened | Allocate-or-fetch the unique canonical mapping; persist opening evidence; condition active |
| updated | Look up the existing mapping; append current usable evidence; keep condition active |
| evidence_unavailable | Look up the existing mapping; append current null/reasons evidence; keep condition active |
| recovered | Look up the same mapping; append observed recovery evidence; condition recovered |

A missing mapping for update/recovery is an integrity error, not permission to
allocate another incident. The helper emits updates from active/evidence arrays;
the detector emits events only on opening/recovery. A must not wait for a
nonexistent detector update event. One evaluated snapshot per active/recovered
episode is planned per result. An opening does not also emit a duplicate update.

Evidence follows the merged PR15 $defs/evidence shape: immutable reading_id,
actual result_id, message_id and measurement UTC time; observed/predicted/residual
temperatures in C; selected rule value/unit/thresholds/timing/availability;
channel quality and null confidence; complete model/configuration/parameter/
detector/policy versions and provenance. Unavailable rule evidence uses the
current reading and null value, not a historical last-usable observation relabelled
as current. Opening and older evidence remain immutable in A's registry.

The first eligible thermal reading initializes from observed oil; prediction and
residual are null. Electrical rules may still evaluate if their channels are
available. Later predictions hold previous load/ambient over actual measurement
elapsed time. Thermal gaps above 300 seconds invalidate model history under the
existing model contract. Detector gap cutoff comes from explicit max_gap_s;
at the cutoff endpoints may accrue time, beyond it timers restart at zero.
No timestamp wall clock, missing channel or simulated label implies recovery.

## A's fenced transaction and retry guarantees

1. Claim under existing asset/source/run leases and fencing. Snapshot the immutable
   reading/config/policy, epoch, twin/detector state revisions and failure barrier.
   Reserve the real result identity for the intended write (for example PostgreSQL
   nextval). An unused reserved ID after rollback is harmless; no incident/result
   row is invented. A may choose a two-stage detector/snapshot builder instead,
   but must not attach commands to a guessed or different result ID.
2. Compute the existing analytic output and this plan without ORM/transaction I/O.
   A's current computation_error behavior already rolls back/retries; keep it.
3. Reacquire the fence; verify lease token/deadline, watermark, epoch/namespace,
   policy and state revisions, and reserved result/reading/configuration binding.
   Handover must invalidate outstanding claims. Roll back if any snapshot changed.
4. Insert/flush the real result using the reserved ID. Resolve canonical mappings
   and immutable evidence against that exact result. Persist result/state/context,
   incident version/history/outbox and job completion in the same transaction.
   Consume an applicable failure barrier only in that commit.
5. Publish durable outbox records after commit, retaining event UUID on redelivery.
   D consumes canonical incidents and remains responsible for separate task writes.

Required uniqueness: canonical mapping(asset_id, detector_epoch, episode_key);
evidence(incident_id, result_id, detector_version, policy_fingerprint);
outbox(incident_id, incident_version, event_type); durable result/job consumption.
Equivalent retries retain existing records; contradictory asset/stream references
must fail. Increment incident_version exactly once per accepted mutation; the
condition/acknowledgement record must participate in concurrency control with
acknowledgement writes. Database constraints/fencing, not pure deterministic
computation, provide exactly-once storage. A owns the final tables/error contracts.

Equal/late/historical/nonadvancing results emit no mutations and preserve context.
Retrying identical inputs/pre-context reproduces the plan. A retry against the
already committed context emits no duplicate transition. Do not apply diagnostic
replay commands to live incidents, roll their condition back or notify/create tasks.

## Failure continuity and explicit handover

While a retryable job is unresolved, do not process later detector samples as if
the failed endpoint was usable. On terminal failure or a deliberate skip, A must
durably record an unconsumed continuity barrier in the stream/epoch, or block the
stream pending operator resolution. On the next eligible forward sample, pass
continuity_break=true. It clears pending/recovery timers and previous endpoint
flags, preserves episode sequence/active keys and starts timing at the current
sample. No active incident is recovered. Late/historical samples do not consume
the barrier. A crash/rollback must leave the barrier unconsumed for the retry.
No packets means no new transitions; feed-silence monitoring remains separate.

Configuration, model, parameters, detector/policy versions, or trusted thermal
reinitialization require an explicit handover, not catch-ValueError-and-reset:

- Fence the stream and record old/new namespaces, durable epochs, exact versions/
  policy fingerprints, boundary watermark, reason, trusted actor/authority and
  control-operation idempotency key. Preserve old rows, evidence, config and results.
- B's default is a fresh operational epoch and cold start. Allocate the new epoch
  once and retain it over retries/restarts. Old active incidents remain active;
  mark their monitoring/evidence availability as interrupted by handover using an
  explicit A registry/audit representation. Do not generate recovered evidence.
- Begin new thermal initialization from the first eligible new-bound reading.
  New detector persistence starts at zero. Do not carry old timers/temperature or
  automatically correlate a new opening with an old physical cause. New episodes
  map to new canonical UUIDs. Task and acknowledgement history remain independent.
- An epoch reset with identical model/config/policy may restart the same B episode
  string; the asset/epoch/episode key still disambiguates it. Do not change real
  run IDs/configurations/policies just to manufacture identity.
- Controlled restoration from exact immutable history may reconstruct matching
  same-epoch state up to the recorded live watermark in isolation. Validate it
  before installation under the fence; diagnostic replay must not rewrite live
  incident state/evidence, publish duplicates or create tasks. An unverified or
  incomplete replay is not an automatic replacement for a cold-start handover.

These are B's conservative defaults. A must confirm the handover control-plane
representation and worker behavior. D must review identity/task consequences.

## B machine error contract

IncidentPlanningError subclasses ValueError and exposes .code. These are computation
codes, not invented HTTP status codes or a claim of existing incident endpoints.

| code | A handling requirement |
|---|---|
| incident_invalid_control | Reject invalid epoch/result identity/barrier controls; do not allocate incidents |
| incident_unsupported_contract | Reject unsupported model/result version, units or fabricated confidence |
| incident_handover_required | Epoch/context version differs; require recorded handover, never silently reset |
| incident_computation_rollback_required | Roll back analytics/detector/incident writes; use existing bounded retry policy |
| incident_invalid_input_or_state | Malformed state/input or incompatible binding; quarantine/inspect or perform recorded handover |

Persist bounded machine codes rather than raw exception/payload text. A must
publish the incident API's separate version/conflict/authorization/not-found/
idempotency contracts and examples. X-Demo-Actor is not trusted acknowledgement
identity. No registry/read/ack endpoint is implemented by this B module.

## Executed validation and remaining dependencies

26 new tests pass: mapping stability across open/update/unavailable/recovery,
reopen and fresh epochs; evidence schema; deterministic retries/nonmutation;
late/historical barriers; continuity interruption without false recovery;
configuration/model/parameter handover; explicit versions/errors; label exclusion.
The earlier targeted pure regression run passed 203 tests before the final six
additional cases; final integrated validation below covers all current cases.

Current main was exported to /private/tmp/personb-orchestration-main-f288790,
overlaid with B analytics and the existing thermal handoff only. A's deployed
model and D's maintenance code were unchanged. Against isolated PostgreSQL:

```sh
TEST_DATABASE_URL=postgresql+psycopg://sentinel@127.0.0.1:55432/sentinel_test \
  /Users/vgnxh/Code/Projects/powernext/teammates/.venv/bin/python -m pytest \
  backend/tests analytics/tests analytics/contracts integration/tests/test_thermal_demo.py -q --tb=short
```

**464 passed**, 232 existing dependency deprecation warnings. These verify existing
backend/worker/sample maintenance and B computation, not the unimplemented incident
transaction or trusted identity. One additional API/worker integration test stores four isolated readings, consumes
actual model1.0.1 results and verifies opening/update/recovery plans with exact
result/message references. Incident context/commands in that test remain pure,
not persisted canonical incidents. No real registry/browser incident success is claimed.

Generate the executed, explicitly synthetic storage examples:

```sh
python -m analytics.examples.incident_orchestration_demo
```

Output: analytics/examples/incident-storage-commands-test-example.json. Four commands
show an opening, two updates and recovery with stable mapping and separate result
references. Epoch/result IDs are illustrative, unpersisted values; this is not an
API response or a canonical incident. Missing evidence is tested separately.

D's PR22 inspector was run read-only against the main export: D004 is the single
migration head; nine existing tables, no incident registry or incident/ack routes,
and no declared security schemes. Inventory cannot prove trusted auth by itself.
No application database/.env/volumes, teammate code, shared API contract or existing
sample record was altered. No independent measured calibration data is available.

Next: A confirms worker-integrated adoption, implements registry/mapping/outbox,
handover/barrier persistence, trusted actor and exact read/ack APIs with examples.
D then adds the sample-preserving genuine task FK/union. C integrates those APIs.
Acknowledgement, observed recovery and task completion remain three separate axes.
