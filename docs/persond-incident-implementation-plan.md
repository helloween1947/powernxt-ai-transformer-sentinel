# Person D incident-linked maintenance implementation plan

> Current follow-up: PR15 and PR21 are now merged. See
> [post-merge dependency verification](persond-incident-dependency-verification.md)
> for current decisions/runtime evidence. The inspection below is the historical
> pre-merge baseline; its PR status statements are not current.
Status: implementation gated on explicit decisions and runtime dependencies; documentation only.
Inspected 9 October 2026. The sample/demo maintenance handover stays closed.
No shared contract was revised, incident feature implemented or teammate message sent.

## Baseline and evidence

Local main safely fast-forwarded to `6289ed1819d35003e902f66ff3864607203d9c71`.
GitHub confirms PR20 merged into main; `docs/integration-verification.md` contains
its maintenance closeout. Both checkouts were clean before synchronization; all
branches and existing databases were preserved. The earlier Chrome verification
was against 7b19626, not a new incident workflow or a rerun on 6289ed1.

| Inspected ref | Exact SHA | Meaning |
|---|---|---|
| main | 6289ed1819d35003e902f66ff3864607203d9c71 | Integrated sample maintenance and published closeout |
| feature/personb-incident-contract | 912c9fee7c96c9d73ae01c5c6aa8006b95855d73 | PR15: proposed incident identity, evidence, API and task boundary |
| feature/personb-analytics-audit | 5813c64f014026fbbe6e7e64b28cb8845c09ecec | PR17: B model1.0.2 and optional detector; includes proposal |
| feature/analytics-worker | b3f8f286e1f67c18c0157ceccadbff516ca4845a | A's stored analytics worker lineage |
| feature/integrated-demo-windows | fcfb21393df6d2712fec3089321ca9010a72694b | PR19: frontend/Windows verification; no incident backend adoption |

PR15, PR17 and PR19 are open. GitHub returned zero reviews and zero issue
comments on each at inspection. No eligible acceptance or approval is inferred.
B's `analytics/docs/genuine-incident-integration-contract.md` explicitly says
"reviewed B proposal, awaiting A/D acceptance." It is not an accepted API.

Primary implementation evidence: `backend/app/models/maintenance.py`,
`schemas/maintenance.py`, `services/maintenance.py`, `services/analytics_worker.py`,
`models/analytics.py`, `api/__init__.py`, and Alembic revisions. A's main worker
persists analytics/state with ordered/fenced execution; it does not invoke B's
sustained detector. Adopted analytical results use model1.0.1; B's audited1.0.2
requires an explicit version/state adoption. Configured-limit observations are
not persisted incidents. The baseline event contract proposes catch-up and event
types; it does not establish implemented publication or an incident registry.

## Readiness and unresolved decisions

| Boundary | Implemented now | Missing decision/deliverable | Owners |
|---|---|---|---|
| Assets and telemetry | Registered assets, immutable configurations, stream-bound readings and results | Reuse authoritative asset/source/run binding; decide incident schema references | A with D review |
| Analytics | Durable results/state, leases, fencing, reading/latest APIs | Adopt detector/model/policy versions; cold-start/replay and configuration handover policy | A + B; D reviews identity consequences |
| Detector | Optional pure sustained detector on B's unmerged branch | Invocation and durable namespace/watermark; verify update evidence as well as opened/resolved events | B logic, A orchestration |
| Incident registry | Absent | Accept UUID/epoch mapping, immutable evidence, version/history and outbox schema; implement persistence | A + B + D acceptance; A implementation |
| Incident retrieval | Absent | Exact accepted read/evidence/history routes, pagination, errors and version semantics | A contract/API; B evidence; C + D consumers |
| Maintenance | Persisted sample tasks/history, versions and terminal notes; C authoritative screen | Accept genuine reference, one-task-per-incident policy and retry/conflict semantics | D backend + A review; C UI |
| Acknowledgement | No backend route; fixture frontend preview is not persisted acknowledgement | Accept authenticated actor/authorization, version/idempotency, audit and error semantics | A + D; C UI |
| Delivery | No incident outbox/publisher/cursor API | Choose worker-integrated transaction or ordered result consumer; durable catch-up if event-driven | A; B/D review |

Questions ready for team decision (not sent):
1. A/B/D: accept PR15's canonical UUIDv4 and unique asset/epoch/episode mapping?
   What recorded handover occurs when model, configuration or policy changes?
2. A/B: choose fenced worker integration or a separately ordered durable result
   consumer, and which detector/model/policy version will be deployed?
3. A/D: publish the exact registry table/FK type, asset-bound read model, incident
   version and read/evidence/ack APIs, including errors and pagination. Which
   acknowledgement actor/authorization mechanism is trusted?
4. A/D/C: is task creation explicitly operator-only (B's proposal default)?
   Confirm one retained task per canonical incident, including terminal tasks,
   conflicting-create behavior, and independent acknowledgement controls.

## D implementation sequence after acceptance

### 1. Canonical incident-to-asset mapping

Consume A's persisted canonical incident, not a reading/result/message/event ID
or B's detector episode string. PR15 proposes A allocates UUIDv4 once and maps
`(asset_id, detector_epoch, detector_episode_key)` uniquely. Epoch survives retry
and restart; a reset uses the agreed new namespace/handover policy. D must not
mint these IDs, truncate detector keys into the existing sample alert field or
relabel analytical observations as samples.

Resolve the incident server-side; derive/check its registered asset, measurement
source/run and exact immutable evidence references. Reject unknown IDs and
mismatched client assets/streams using agreed error codes. Never use latest
analytics as opening evidence. A provides registry schema and stable references;
B confirms evidence/version semantics; D enforces the task relationship. A
reopened episode gets a new canonical identity per the adopted policy.

### 2. Additive migration preserving sample records

Wait for A's incident registry revision/type before writing an executable FK
migration. Inspect the actual graph then; current single head is
`d004_worker_maintenance`. Preserve all D001-D004 and A revisions. If parallel
revisions create heads, add an explicit reviewed join only after checking DDL
and data dependencies; a no-op join alone cannot supply an absent registry.

Proposed shape for review: retain existing sample identity/summary/action,
versions, owners, timestamps and task history unchanged; add a nullable genuine
incident reference with RESTRICT deletion and an asset-binding FK if A exposes
the required composite unique key. Retain the sample uniqueness constraint;
add unique canonical incident linkage for one task per incident. Replace the
sample-only source check with reviewed mutually exclusive sample/genuine checks.
The genuine path requires a canonical FK; the sample path requires null incident
reference and its original sample identity. Do not invent placeholder incidents
or backfill genuine IDs from sample identifiers. Agree legacy alert-column
nullability and response shape before DDL; these are not settled schema names.

Deploy registry first, then D's additive schema, then API support, then C's UI.
Define safe downgrade behavior before release: fail clearly if genuine rows
prevent rollback to a sample-only schema; never silently delete or relabel them.
Use new disposable test databases; preserve existing development databases and
volumes. Verify metadata and a single intended final head on the actual graph.

### 3. Incident-linked task service/API

Extend the sample/genuine request union only after its shape is accepted. B's
proposed reference `{source: analytics, incident_id: UUID, asset_id: bound asset}`
is a review input, not an endpoint contract. Keep existing sample clients working.
Derive authoritative incident summary/evidence server-side and preserve opening
provenance according to the accepted schema; client summaries are not proof.

Use transactions/unique constraints for concurrent one-task-per-incident creation;
return the existing task on an agreed equivalent retry and surface conflicts
without overwriting. Keep task expected_version and atomic history updates.
Assignment, start, completion and cancellation do not acknowledge or recover an
incident. Decide policy for recovered incidents and existing terminal tasks
before implementation. C owns the UI/client changes; retain one maintenance mount.

### 4. Explicit acknowledgement integration

Wait for A's implemented, accepted acknowledgement operation. PR15 proposes
`POST /api/v1/incidents/{incident_id}/acknowledgements` with incident version,
idempotency key and trusted actor; no such route exists on main. Do not call
that speculative path or treat X-Demo-Actor as authenticated identity.

Present acknowledgement separately from task status. Send the reviewed incident
version/idempotency token, surface stale conflicts and preserve the operator's
draft pending explicit review; do not automatically retry a stale mutation.
Show the server's persisted acknowledgement/history after success. Recovery,
acknowledgement and maintenance status remain independent. Avoid a distributed
"create task plus ack" operation unless A supplies an explicit atomic contract.

## Required verification when implementation becomes possible

- PostgreSQL fresh upgrade and upgrades from D004, A's registry-only revision,
  and relevant supported branch states. Seed pre-upgrade open/completed/cancelled
  sample tasks and history; compare every identity/version/status/note/timestamp
  afterward. Validate FKs, uniqueness, source checks, metadata and final head.
  Exercise rollback policy without destroying records.
- Canonical mapping: same episode across update/recovery/retry/restart stays one
  UUID; reopened episodes separate; source/run/rule isolation; mismatched assets
  and evidence rejected; reset/handover follows accepted policy. A/B tests cover
  ordered/fenced processing, late readings, unavailable/gap behavior and rollback.
- Task API: backward-compatible sample requests/responses; genuine unknown and
  wrong-asset rejection; concurrent equivalent retries create one task/history;
  conflicting creates and stale versions remain visible; notes, assignment,
  read-only terminal status, history and pagination remain correct.
- Acknowledgement: trusted identity/authorization, incident-version conflicts,
  duplicate idempotency retries, atomic history and failure rollback; task actions
  do not change condition/ack and acknowledgement does not complete a task.
- Actual Chrome against real persisted incident APIs: create/list/assign/start/
  complete/cancel, evidence/history pages, independent acknowledgement, conflicts,
  API/offline errors, refresh and backend restart persistence. Keep synthetic
  incident fixtures labelled; no substituted response is genuine backend evidence.
- Run relevant backend/audit/worker and C frontend tests, lint/build plus exact-head
  CI. Event-driven consumers additionally require redelivery deduplication and
  durable cursor catch-up tests. Keep unit/API/browser results distinct.

## Checks actually run for this planning task

- Safe fetch/fast-forward and clean working-tree inspection; verified PR20 merge
  and report presence through GitHub and tracked source.
- In-memory Alembic ScriptDirectory: exactly `d004_worker_maintenance`.
- SQLAlchemy registered metadata: asset/configuration, telemetry/jobs,
  analytics stream/state/results, maintenance task/history only; no incident table.
- FastAPI OpenAPI inventory: assets, telemetry/analytics, maintenance and health;
  no incident, acknowledgement or event recovery routes.
- Pydantic validation rejects a proposed analytics incident reference as expected.
- Reviewed exact branch source and GitHub review/comment status; no inferred approval.

No database was started, migrated or deleted; no new browser workflow or full
regression suite was run for this documentation-only plan. No accepted incident
contract/API currently supports a safe genuine-task or acknowledgement code change.
The implementation gate is explicit; sample maintenance remains available.
