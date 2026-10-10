# A/B detector orchestration and D registry handover

A adopts B's concrete `f668a21dcf88605d7fcff4996282185bc796740c` handover,
reviewed against main `f52f56515c38fce55451fd499be81ef2508e6677` (PR22 already
merged). This implements the registry boundary left open by merged PR15/21.
It does not claim a new review by B/D or merge their branches wholesale.

## Adopted orchestration

Use A's existing fenced per-stream worker. No separate ordered result consumer.
The deployed model remains `powernxt-electrical-top-oil` /
`stored-reading-top-oil-1.0.1`, result `stored-reading-result-1.1.0`.
Adopt B's pure `sustained-threshold-1.0.1` detector and
`incident-storage-commands-1.0.0` planner; preserve exact source provenance in
backend/app/analytics/person_b/INCIDENT_SOURCE.json. Imports use the existing
vendored physical core; no prototype heuristic or model1.0.2 upgrade is included.

Model computation still runs outside locks. One explicit implementation choice:
after reacquiring the fence, flush the real analytics result and execute the
bounded one-to-six-rule pure planner in that final transaction. This binds exact
result IDs without a speculative reservation. The planner performs no database,
network or publication I/O. Persist result/twin state/detector context/header/
mapping/evidence/event journal/delivery checkpoint/job completion together, then recheck the lease
deadline before commit. Lost leases/failed writes roll back everything.

One stream's control changes share the worker's stream lock. An unexpired active
lease returns stream_busy rather than changing its binding mid-computation.
Expired outstanding tokens are cleared by handover and fail the existing fence.
Incident row locks serialize detector version updates with acknowledgements.
Database uniqueness protects mappings/evidence/event versions/operation receipts.
The separate `incident_outbox` dispatcher loads only committed events and invokes
a supplied transport after closing its snapshot transaction. Per-incident version
ordering, lease tokens, attempt counts and delivery receipts are durable. Delivery
is at least once: a crash/expired lease after sending but before receipt can repeat
an event. Consumers must deduplicate `event_id`; they must not use publication time
as incident order. No queue/WebSocket transport or automatic task creation is wired.

Policies are explicit immutable snapshots, including version, provenance,
max_gap_s and all named rules. Their complete finite JSON content is SHA256-bound.
No policy is enabled by default and there are no inferred thresholds/severities.
Before first monitored forward reading, an admin records the epoch/handover.
Unconfigured streams retain existing analytics behavior and create no incidents.

Equal/late/historical readings store analytics but do not advance detector state,
change incidents or consume failure barriers. Terminal failures (including expired
exhausted leases) and nonadvancing forward samples record a durable continuity
barrier. Next eligible evaluation resets endpoint/persistence/recovery timers,
preserving active episode identity. Historical failures do not change live
continuity. Missing evidence/gaps never recover incidents; no packets produces no
transitions. Persistent active candidates supply updates/unavailable evidence
even when B has emitted no opening/recovery event.

## Configuration/model/policy handover

POST `/api/v1/assets/{asset_id}/detector-handovers` requires trusted admin,
expected control version (0 for first enable), UUID idempotency key, exact
registered configuration version, source/run, model/detector versions, full policy
and reason. A resolves immutable parameters and allocates/persists a UUID4 epoch.
Current supported model/detector pair is pinned above; other versions are 422.
Upgrading to model1.0.2 requires a separate reviewed adoption and control change.

Every handover—even a reset with identical configuration/policy—creates a fresh
durable epoch once, records prior epoch/control version, boundary watermark,
reason and trusted actor receipt, and cold-starts both thermal and detector state.
The new epoch archives the exact previous twin-state cache, namespace, advance
count and update clock before a same-namespace cache can be replaced. Existing
results, detector contexts, epochs and snapshots are preserved. Existing active incidents
stay active and become monitoring_status=interrupted with an immutable event;
no recovered evidence or inferred physical-cause correlation is fabricated.
Acknowledgement remains unchanged. New openings map to new UUIDs.
Retries return the original receipt. Unrecorded model/config/parameter/detector/
policy mismatch rolls back with worker code incident_handover_required and uses
existing bounded retry/quarantine behavior. It does not catch-and-reset state.
An already terminal failed job is not automatically replayed by handover.
Backfill/diagnostic replay/live-state restoration is outside this control API.

## D's concrete dependency surface

- Migration `a001_incident_registry` extends D004; `a002_incident_outbox` extends
  A001 and is now the intended single head. A002 backfills a pending checkpoint
  for every existing journal event without changing any existing record. Apply
  this before any D task FK migration; do not rewrite prior revisions or fake a
  no-op join to supply tables. Empty-only registry downgrade refuses populated
  identity/incident/control tables rather than deleting audit evidence.
- Canonical target: `incidents.id UUID`, composite UNIQUE `(id, asset_id)` named
  uq_incident_asset; asset VARCHAR(100), deletion RESTRICT. Nullable genuine task
  reference must stay null for preserved sample rows. One task per canonical
  UUID uses a new unique FK constraint; no backfill from sample-* strings.
- Resolve authoritative incident/asset/source/run through this registry, never
  trust a supplied summary or B episode string. Read/evidence/event/ack APIs and
  versioned errors are implemented in the [API contract](contracts/incident-api-contract.md).
- Use server-authenticated actor UUID from the reusable incident auth dependencies
  for genuine mutations; the sample-only X-Demo-Actor remains untrusted. The new
  IncidentRoute demonstrates versioned auth/error handling. No user-provided
  actor field is accepted on acknowledgements.
- Default genuine task creation remains an explicit operator action, independent
  of detector/ack/recovery. Registry exposes both active and recovered incidents;
  D still owns the task request union, source/nullability migration, terminal-task
  retry behavior and any recovered/interrupted creation policy. Those are D's
  next reviewed implementation, not part of this PR. Do not automatically create
  another task for an update/ack on the same incident or relabel an incident sample.
- Task expected_version and incident_version are independent. Acknowledging a
  stale incident returns 409 and never changes task state. There is no distributed
  atomic task-create-plus-ack operation.

## Implemented versus remaining

Implemented: canonical PostgreSQL registry/mapping, immutable evidence, durable
per-incident event journal and fenced post-commit outbox dispatch interface,
authenticated read/ack/admin handover APIs, explicit
version/conflict/idempotency contracts, fenced detector state/barriers and
sample-preserving additive migration. Tests include actual persisted episodes.

Remaining: D's task FK/genuine API union and trusted identity integration; C's UI;
shared deployment; queue/WebSocket transport configuration; external SSO/tenant
authorization; field calibration/physical fault validation; separate model1.0.2
adoption and any replay/restoration workflow. B/D should review this PR's control
and identity choices before the registry becomes their deployed dependency.
