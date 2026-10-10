# A's review of B's detector handoff — 10 October 2026

Reviewed B PR24 source `f668a21dcf88605d7fcff4996282185bc796740c` on
`feature/personb-detector-orchestration`, fetched main
`f52f56515c38fce55451fd499be81ef2508e6677`, and A's previously published registry
`4bfe3ed4ca6798d4f1c3b836ffde6fe33e3b5420`. New delivery branch:
`feature/persona-detector-handoff-review`. The earlier A and all teammate branches
are unchanged. Main contains the merges of contracts PR15/21 and dependency checks
PR22. PR22's historical absence report is accurate for its tested commit; this
branch supplies those dependencies rather than rewriting that report.

No applicable AGENTS.md was found. CONTRIBUTING.md requires a teammate approval
and passing CI before merge. This review does not establish B/D agreement or
authorize deployment. The reviewed SHA still matches B's remote branch; hosted
PR metadata/reviews/checks could not be fetched (proxy CONNECT 403).

## Review outcome and accepted A implementation choices

B's callable planner is suitable for integration. Its tests, example and handoff
correctly distinguish storage commands from persisted canonical incidents. The
example's synthetic result IDs, policy and model1.0.2 outputs are illustrative;
they do not demonstrate storage or authorize a model upgrade. No correction to
B's pure detector was necessary in this review.

A's branch implements the durable storage handoff, with these explicit choices:

- Keep the existing fenced, measurement-ordered per-stream worker and deployed
  model1.0.1. B's planner supports both 1.0.1/1.0.2, but adopting the latter still
  requires separate review and a recorded handover. The physical core and model
  worker have no changes against main.
- Compute the twin outside locks. After reacquiring the same stream/job fence,
  flush the actual result and run the bounded pure detector inside the final
  transaction. This gives evidence its exact stored result ID. The detector
  context cannot change between twin computation and final planning: handover
  shares the stream lock, rejects live leases and invalidates expired tokens.
  Acknowledgement locks only the incident and does not alter detector/twin state.
- Commit result, twin state, detector context, canonical mapping, evidence,
  versioned history, delivery checkpoint and job completion together. Recheck the
  database lease deadline before commit. No publication occurs in this transaction.
- One UUIDv4 per asset/epoch/episode mapping; updates, unavailable evidence and
  recovery retain it. Reopened episodes and fresh epochs allocate a new UUID.
  The original reading/result/message IDs remain immutable evidence references.
- Terminal failure/skip barriers are durable and consumed with context updates
  only by eligible forward results. Late/equal/historical samples cannot advance
  detector state, change active incidents or consume a barrier. Missing evidence
  and gaps interrupt timers and never count as observed recovery.
- Explicit handover records actor/reason/boundary, preserves the previous twin
  snapshot, old contexts, active incidents, acknowledgements and sample tasks,
  and cold-starts a fresh epoch. Incompatible state is rejected, never silently reset.
- Opaque random bearer credentials are verified against server-held hashes,
  expiry/active state and server-assigned reader/operator/admin roles. Demo headers
  have no authority on genuine incident routes. This is trusted deployment-level
  identity, not SSO/MFA or tenant/asset authorization.

## Corrections made on A's new branch

The earlier A001 registry had an immutable event journal but no delivery receipts
or dispatcher. A002 adds one checkpoint per event and backfills existing journal
entries as pending without rewriting history. `incident_outbox` claims with
SKIP LOCKED, database leases and unique tokens. Earlier undelivered versions block
later versions of that incident. It reloads only committed snapshots, invokes a
supplied transport after closing the transaction, then fences receipt writes.

Delivery is **at least once**, with stable event UUIDs. A crash or lease expiry
after sending can repeat an event, including a stale attempt finishing later;
consumers must deduplicate event_id and apply incident_version monotonically.
Lease fencing prevents stale receipt writes; it cannot retract a network send.
Failed transport attempts remain pending and become reclaimable on lease expiry.
There is no configured queue/WebSocket endpoint, automatic event daemon, task
creation or teammate message. This review tested a local in-memory receiver,
not delivery to C/D or a broker.

Worker output binding validation now applies to all results, even without
detector opt-in or forward state advancement. Contradictory asset/source/run,
reading/message, measurement time or configuration references roll back. Planner
commands are also checked against authoritative asset/epoch/stream and exact
reading/result/message IDs before canonical mapping/persistence.

## Actual execution

Linux cloud environment, Python3.12, PostgreSQL16-alpine in new container
`persona_detector_handoff_db` at loopback15442, database `detector_handoff_test`.
Existing development database/API containers, volumes and environment files were
untouched. Their start times remain 2026-10-08T07:27:47.986857197Z (database) and
2026-10-08T07:27:48.120634273Z (backend).

| Check | Executed result |
| --- | --- |
| Entire A backend suite, including sample maintenance | 265 passed, 274 existing dependency warnings, 90.28 seconds |
| B's exact exported analytics/tests plus analytics/contracts | 214 passed, 3 skipped, 10 dependency warnings, 5.59 seconds |
| B real stored-worker-result planner test | Passed as part of the preceding export suite, using A's model1.0.1 worker and isolated PostgreSQL |
| Fresh database plus nine schema start cases (fresh/eight existing) | Passed in backend suite; existing asset/configuration/telemetry/maintenance records preserved |
| Populated A001 -> A002 | Passed; copied real stored records unchanged and two journal entries backfilled pending |
| Sample open/completed/cancelled tasks and their history across registry upgrade | Passed in backend suite |
| Alembic graph/model drift | Single a002_incident_outbox head; alembic check reports no new upgrade operations |
| Dedicated HTTP API15443 + fenced worker verifier | Passed: one UUID, three evidence records, four history events; exact result binding, ack/recovery independence, equivalent retries and run isolation |
| Actual outbox dispatch to local test receiver | Four versions1–4 in order, stable distinct event UUIDs and four PostgreSQL delivery receipts |
| Targeted Ruff and git diff --check | Passed |

The three B skips are the simulator compatibility cases requiring its separate
55a9c54 branch export. No browser, Windows or fresh development deployment check
was executed. B's reported 473 tests are not reused as proof: the counts above
are independently executed, distinct source selections.

Initial export attempts lacked the separately installed jsonschema search path
and data fixtures; these were corrected without modifying repository dependencies.
The first new migration fixture copied child state before its stream and was
corrected. The first full backend pass exposed ten old expected-head assertions;
the final suite uses A002 and passes without weakening preservation assertions.

New tests cover uncommitted outbox invisibility/rollback, concurrent ordered
claims, transport failure/retry, expired receipt rejection, contradictory worker
results/planner commands, one-time ack/handover enqueuing and populated upgrade.
Existing incident tests independently cover leases/stale worker commits,
concurrent processing/acknowledgements, retries, equal/late results, unavailable
evidence, recovery/reopening, run/epoch isolation and handover continuity.

Structured results, actual sanitized API responses and source SHA256 hashes are
in [new evidence](persona-detector-handoff-evidence.json). Earlier
[registry evidence](incident-registry-evidence.json) remains historical and intact.

## D's integration dependency and examples

Apply reviewed A001 then A002; base D's future additive task migration on the
actual final head A002. Do not edit old revisions or manufacture a join to hide
schema conflicts. Physical registry: `incidents.id UUID`, `asset_id VARCHAR(100)`,
UNIQUE `uq_incident_asset(id, asset_id)`. D should use a composite FK
`(incident_id, asset_id) -> incidents(id, asset_id) ON DELETE RESTRICT` and a unique
genuine incident task reference. Preserve sample rows with null genuine FK; do
not derive a UUID from sample alert strings. The registry's epoch/stream/config
FKs and evidence trigger enforce the authoritative transformer binding.

Implemented read surface (all require verified Bearer identity):

```http
GET /api/v1/operators/me
GET /api/v1/incidents?asset_id=<registered-id>&source=simulator&run_id=<actual-run>&limit=20
GET /api/v1/incidents/<canonical-uuid>
GET /api/v1/incidents/<canonical-uuid>/evidence?cursor=0&limit=20
GET /api/v1/incidents/<canonical-uuid>/events?cursor=0&limit=20
GET /api/v1/analytics/results/<exact-evidence-result-id>
POST /api/v1/incidents/<canonical-uuid>/acknowledgements
```

Sanitized request shape (replace the example key and use the fetched version):

```json
{"schema_version":"incident-acknowledgement-1.0.0","expected_version":1,"idempotency_key":"50000000-0000-4000-8000-000000000002"}
```

New ack201; equivalent same actor/content/key retry200 with original persisted
response; conflicting key409; stale version409 with current_version. Ack cannot
recover a condition or complete/create a task. Evidence/events use exclusive
incident-version cursors, ascending order and limit1–100. Incident list uses an
exclusive UUID cursor and exact measurement source/run isolation. Full versioned
responses, error codes and credential provisioning/PowerShell commands:
[API contract](contracts/incident-api-contract.md) and
[backend API examples](../backend/docs/incidents.md).

Still unavailable: D's genuine-task union/FK/auth integration and terminal-task
retry policy, C's genuine incident UI, deployment, configured transport, SSO/tenant
scope, model1.0.2 adoption, field calibration and retrospective replay/restoration.
B/D need to review the explicit cold-start handover and identity choices; thresholds
in examples remain assumed, not team-agreed operating limits. Recovered/interrupted
task eligibility and operator-only task creation still require D/team agreement.

## Publication and human gates

The branch includes the prior unmerged A registry plus these focused corrections;
it supersedes that branch's proposed main delivery without changing its history.
Prepared draft PR description: [PR body](persona-detector-handoff-pr.md).
GitHub API CONNECT403 prevents creating a draft or inspecting hosted CI/review
status; Git push/remote equality are checked separately at publication. Do not
interpret local passing tests as hosted CI or merge approval. Human teammate
review, passing exact-head CI and coordinated deployment remain prerequisites.
