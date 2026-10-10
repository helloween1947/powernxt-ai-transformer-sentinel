# Person D final review handover — 10 October 2026

This supplements the dated [combined verification](persond-combined-alignment-verification.md).
Its historical counts remain historical. No teammate approval or deployment is inferred.

## Current GitHub reconciliation

Main fetched for this review: `cbdd7c47f8cf5aa66d0277f5fa96d69bfb01ddda`.
PR26 is merged into main; its `fa5f79c1eeb6c5a92c1d822bbfea9c29ea66cdbe`
CI/docs history is already shared with the combined branch. There is no second
copy of that change in the main-to-candidate net diff. The D branch normally
merged current main in `ec6268a3af4933ff808f89b24d85d74764a816be`; no files changed.

PR25 and PR27 are merged into A's registry branch, whose current head is
`2e934c85098453db7342ea6ade570759ef4b9161`. PR27's published head
`7b89f96f95ebf2962326f0a8c80a45efc4586efd` and that registry head have identical
trees. The registry/A002/D005/W001/D006 histories still **do not reach main**.
PR25/26/27 are closed/merged; their submitted review lists were empty when read.
That establishes merge state, not teammate approval. Do not retarget a closed PR.

Historical ancestry confirmed in the combined candidate (absent from main):

| Contribution | Full SHA |
| --- | --- |
| Registry plus PR25 | `22c34d00ba264975c905f0b13b56ba12968fd123` |
| D005 candidate | `e0a079ecb5e0d694e6a30e3dabec94bbe5469e7f` |
| A002 | `cf2eb252a5e405d4991e82b86db13c49822977fb` |
| W001 | `20ccaddcecd55695b79d257a02f25a68ec691462` |
| Earlier runtime source | `7f24e5293cfb7716d5d4f441c20bf56b8d8de924` |
| Concurrency coverage | `631dc103b685fe42ab30b39c0f09652f8ba900bc` |

The follow-up targets A's current registry branch and contains only D's verification
runner and handover plus the file-free main merge. It must not repeat the large
registry/outbox/What-if diff already merged there. Main adoption of that source is
A's separate reviewed PR. Retarget only after required histories reach main,
rechecking the graph, net diff and exact-head checks. Teammate branches are untouched.

## Migration graph and source review gate

```text
older audit/maintenance revisions -> D003 -> worker migration -> D004
 D004 -> A001 -> A002 ----\
               D005 -----+-> D006 (no DDL)
 D004 -> W001 -----------/
```

The actual revision names are `a001_incident_registry`, `a002_incident_outbox`,
`d005_incident_tasks`, `w001_what_if_snapshots`, `d006_combined_integration`.
D006 retains all three parents and remains the sole intended head. No published
revision is changed. Historical-data tests copy target columns explicitly;
concurrency tests preserve independent incident condition, acknowledgement and
task status while validating exact What-if snapshot bindings.

There is no **reviewed deployment target SHA** yet: A must approve the exact
candidate source and adopted main commit, including already-merged source work.
The final source SHA and exact CI links are recorded in the follow-up PR.
The deployer must pin that approved SHA/image digest, not a moving branch name.
B model1.0.2/full PR24 adoption remains a separate A/B decision; this candidate
retains model1.0.1 namespaces and does not relabel old state/results.

## Isolated Docker runner and current verification

`integration/verify-persond-docker.ps1` uses the normal backend Dockerfile for both
backend and worker, a standalone generated `persond_review_*` Compose project,
a unique retained PostgreSQL volume/database, and loopback ports 15447/15448.
It never invokes development Compose, Docker Desktop startup, down -v or pruning.

```powershell
# From this exact clean candidate; host Python needs requirements-dev installed.
./integration/verify-persond-docker.ps1 -Python '<absolute-venv-path>/Scripts/python.exe'
```

The runner seeds labelled sample/history/analytics fixtures at D004 into an empty
database, applies the populated upgrade using the normal backend image, checks
original fields/new nullable fields and Alembic consistency, runs both live HTTP
integration verifiers, boots the normal worker, restarts only its own backend/worker,
and compares retained sample/analytics/incident/evidence/task/snapshot records exactly.
It revokes its private temporary admin credential and stops only its generated
project while retaining containers, volume and ignored evidence. A worker process
being up alone is not detector correctness: the verifiers independently execute
actual fenced worker transactions using synthetic telemetry.

Docker execution is currently blocked: `docker version` reports no
`dockerDesktopLinuxEngine` pipe. CLI/Compose availability and successful Compose
configuration parsing are **not** image-build/runtime evidence. No Docker pass,
container restart pass or image digest is claimed until the runner actually completes.
Starting Desktop could also start development containers; it was not done.
An isolated engine must be made available before Docker verification can be closed.

The prior actual installed Chrome workflow tested C's **sample** maintenance screen,
including assignment, status/notes, cancellation, refresh, offline errors and API
restart. Genuine authenticated UI is not present; those checks cannot certify it.
No dashboard/API contract or frontend runtime changes are made by this follow-up.

## A-owned data-preserving deployment/recovery checklist (not executed)

1. Record intended environment URL, approved source SHA, image digests, current
   Alembic heads and database identity. Stop/fence writers and background workers
   only during a separately authorized window; verify no unexpired worker lease.
2. Take a consistent `pg_dump --format=custom` to a new private backup file; record
   checksum and restore it into a **new** validation database. Never restore over
   the only existing database. Include rows for samples/history, analytics, canonical
   incidents/evidence/events/receipts and What-if snapshots; protect operator hashes.
3. Inspect the restored graph. Run approved-image `alembic -c backend/alembic.ini
   upgrade head`, then `current`, `heads` and `check`. Expected sole head is D006;
   A001/D005, A002 and W001 parents must exist first. No revision stamping or manual
   competing incident tables. Confirm preserved old values/null sample links and
   immutable records, not just table counts. Rehearse the populated upgrade first.
4. Apply the same verified additive upgrade to the intended database during the
   approved window; start the pinned backend and worker, then C's reviewed UI.
   Confirm runtime hashes, readiness, authorized routes, conflicts, worker behavior,
   source/identity labels and post-restart record persistence against that environment.
5. On failure, fence writes and retain logs/data. Prefer a compatible approved
   application rollback or a forward fix with the additive schema retained. Do not
   downgrade populated genuine-task/snapshot/worker history or drop tables. D005
   explicitly refuses destructive populated downgrade. A DBA may recover the verified
   backup to a new database and switch deliberately; account for writes since backup
   with owners before any cutover. The original database/volumes remain available.

## A/C policy decision — proposed, not enabled

Current accepted implementation: a **new** task requires `active` condition and
`monitoring` status. Otherwise HTTP409 `incident_creation_policy_required`.
Equivalent creation intent is checked first: same canonical incident/asset/action/
original owner returns the current existing task with HTTP200, including terminal
tasks and later recovered/interrupted incidents. Conflicting intent returns409;
there is still at most one task per incident UUID. Acknowledgement is independent.

Decision for A/C (D implements only after acceptance): retain this restriction,
or permit explicit historical investigation for recovered/interrupted incidents?
If permitted, proposed requirements are authenticated operator/admin; canonical
asset/incident binding and immutable evidence; a nonblank investigation reason
recorded in creation intent/audit; visible incident condition/monitoring status and
synthetic provenance; ordinary independent task lifecycle; no implicit ack/recovery,
no restart of monitoring and no second task for the same UUID. Reason field, limits,
retention, authorization, response/error schema and C's confirmation UX need an
accepted contract before code/migration changes. Current strict schemas accept no
such new reason field. Decide whether interrupted evidence is sufficient and how
operators see that limitation. No policy approval is asserted.

## Exact C authenticated integration handoff

Use [A incident contract](contracts/incident-api-contract.md),
[D task contract](contracts/incident-maintenance-contract.md), the implemented
OpenAPI and [credential CLI](../backend/docs/incidents.md). Historical dependency
paragraphs in those contracts do not override the ancestry reconciliation above.

| Flow | Exact semantics |
| --- | --- |
| Identity | `GET /api/v1/operators/me`; Bearer credential, server UUID/role. No signup/login/SSO endpoint. Never treat X-Demo-Actor as genuine authority. |
| Incident selection | `GET /api/v1/incidents?asset_id=...&source=simulator&run_id=...`; query source is measurement source, response source is analytics. Device omits run; simulator/replay requires it. Use returned canonical UUID and asset. |
| Evidence | `GET /api/v1/incidents/{uuid}/evidence?cursor=0&limit=20`; follow exact persisted result_id, not latest analytics. Evidence/events use exclusive incident-version cursors, not offsets. Keep highest seen version even when next_cursor is null. |
| Create | `POST /api/v1/maintenance/tasks`: `{"alert":{"source":"analytics","incident_id":"<UUID>","asset_id":"<registered>"},"action":"Inspect evidence","owner":null}`. Operator/admin. Server resolves summary/evidence/actor. 201 new, 200 equivalent retry; both Location. No client actor/summary/condition/evidence override. |
| Browse | `GET /api/v1/maintenance/tasks?source=analytics&asset_id=...&limit=20&offset=0`. Reader/operator/admin. Default list is sample-only even with a token. No combined-source implicit list. |
| Task/history | `GET .../tasks/{uuid}` and `GET .../tasks/{uuid}/history?limit=20&offset=0`; genuine records require reader/operator/admin. Pages have items/limit/offset; no invented next_cursor or total. |
| Assignment/work | `PATCH .../tasks/{uuid}` with the **task** expected_version and owner/status/notes. `open -> in_progress/cancelled`; `in_progress -> completed/cancelled`; terminal tasks read-only. Owner required for start/complete; completion/cancellation require nonblank notes. |
| Ack | Separate `POST /api/v1/incidents/{uuid}/acknowledgements` with `schema_version=incident-acknowledgement-1.0.0`, **incident** expected_version and new UUID idempotency_key. Operator/admin. Exact retry with same actor/body/key returns200 original receipt; new success201. Task mutation never calls ack implicitly. |
| Conflict/error | Incident errors use incident-error-1.0.0/code/message/current_version. Maintenance validation/conflict/DB failures can use `detail` (422/409/503); auth/policy/binding errors use incident shape. Missing/invalid/expired/revoked401; insufficient role403; asset mismatch422; absent references404. Support both shapes. |

After task409, refetch task/history and retain unsaved input for human review;
there is no current_version field guaranteed in that maintenance detail response.
After incident409, refetch incident independently. Never silently replace an
expected_version and retry. Keep acknowledgement operation key for uncertain-network
retries; task creation uses stored equivalent intent, not that ack key. Never log
credentials or store them in fixtures; browser credential storage design is C/A's
review item. Surface offline/503 with retry controls and explicit uncertainty.

Isolated native startup is in the earlier report; Docker startup above supplies
the same contract on loopback15448. Obtain a private server-issued local credential,
set `VITE_API_BASE_URL` to the exact isolated API, and keep sample/local fixtures
visibly separate. Synthetic persisted incidents are runtime integration evidence,
not physical validation. Production SSO and shared transport remain unimplemented.

C's genuine UI completion should trigger a joint review of create/list/owner/start/
completion/cancellation, independent ack, exact evidence/history pagination,
401/403/409/422/503/offline, uncertain-request retries, refresh and backend restart.
D can then execute actual authenticated Chrome E2E; no such result is claimed now.

Ready-to-send (not sent): A, please review the pinned candidate and separate main
adoption/deployment order; no review approval is present in the API inventory.
C, please implement against the exact authenticated contracts above and review the
recovered/interrupted policy with A. Docker verification needs an isolated engine.
Model1.0.2 adoption remains with A/B. Development services and data were untouched.
