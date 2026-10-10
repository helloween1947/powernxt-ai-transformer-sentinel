# D genuine-maintenance dependency review and verification

10 October 2026. Fetched main `f52f56515c38fce55451fd499be81ef2508e6677`.
Primary main and prior D work were preserved; new D branch is based directly on
A's registry dependency `4bfe3ed4ca6798d4f1c3b836ffde6fe33e3b5420` without merging
A wholesale into any previously published D branch. No teammate branch modified.

Reviewed actual paths: docs/contracts/incident-api-contract.md,
backend/docs/incidents.md, docs/incident-worker-handover.md; models/services/API/
auth/migration/tests. A exposes canonical UUID+asset composite key, exact immutable
evidence/result references, authenticated server actor with revocation/expiry/roles,
versioned ack/error/idempotency contracts and explicit active/recovered/interrupted
handover semantics. Relevant A incident+contract tests independently passed32.
D's tests use real fenced-worker-created synthetic incidents, never relabel samples.
This is a D integration-boundary review, not approval of detector mathematics or
physical calibration. External SSO/tenant authorization and field accuracy remain
outside A's implementation. No blocking issue found in the boundary used here.

A's dependency remains unmerged at inspection. D draft is stacked against
feature/persona-incident-registry so its diff excludes A implementation. Human
review/CI for A, then D retarget to main, net-diff review and exact-head CI, then C
UI integration/deployment. No automatic merge or teammate messages.

## Implementation

See [draft API contract](contracts/incident-maintenance-contract.md). D adds the
sample/genuine union, canonical incident binding, server-derived opening context,
trusted mutations and protected genuine retrieval/list/history, original-intent
retry, separate task/incident versions and trusted audit IDs. D005 preserves sample
records and history with null genuine linkage; no competing incident table.
Historical migration checks were updated to expect the new head and seed old
schemas directly rather than run the current ORM before its columns exist.

Recovered/interrupted NEW creation remains gated with a documented409 pending
A/D/C policy review; equivalent existing task retry remains allowed. Completion
cannot acknowledge/recover incidents. C must implement the genuine authenticated
UI; no new UI or genuine browser flow is claimed here.

## Actual checks and isolated runtime

Native preserved PostgreSQL18 on loopback55432; Python3.13. No existing database or
volume was deleted or migrated. Test suites use newly allocated schemas/databases
and remove only those they themselves create. Live HTTP records retained in a new
persond_incident_*_test database. API port15441 is dedicated to this run. Private
test credential is outside Git, not printed. Revoke it after verification.

Executed commands (replace placeholders with isolated values; preserve prior env):

```powershell
$env:TEST_DATABASE_URL = '<isolated PostgreSQL *_test URL>'
python -m pytest backend/tests/test_incidents.py analytics/contracts -q --tb=short
python -m pytest backend/tests/test_incident_maintenance.py -q --tb=short
python -m pytest backend/tests analytics/contracts -q --tb=short
$env:DATABASE_URL = $env:TEST_DATABASE_URL
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini check
python -m backend.app.operators issue --name d-isolated-admin --role admin --token-file '<new private file>'
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 15441
python -m integration.verify_incident_maintenance --base-url http://127.0.0.1:15441 --database-url $env:TEST_DATABASE_URL --token-file '<private file>' --state-file '<ignored state JSON>'
# Stop/start only the same isolated API process, then:
python -m integration.verify_incident_maintenance --base-url http://127.0.0.1:15441 --database-url $env:TEST_DATABASE_URL --token-file '<private file>' --state-file '<same state JSON>' --resume
```

- A dependency subset before D modifications:32 passed.
- New genuine integration tests:14 passed (worker incidents, missing/expired/revoked
  auth, roles, read/list/history isolation, binding/strict input, concurrent creation,
  terminal retry, stale versions/atomic rollback, independent acknowledgement/
  recovery, recovered/interrupted gate, composite FK/deletion, fresh and existing
  D004/A001 upgrades, metadata and sample preservation).
- Existing sample task/workflow:38 passed.
- Updated historical upgrade/join checks:22 passed.
- Native fresh upgrade and Alembic metadata check passed; single D005 head.
- Live HTTP/worker verification passed create/list/auth boundary, assign/start/
  complete and sample cancellation, equivalent terminal retry, independent ack/
  recovery. Actual isolated API stop/start followed by resume passed exact task,
  incident and history snapshot persistence. This is not browser execution.
- Early attempts were interrupted/mislocated and raced PostgreSQL recovery;
  connection errors are not a passing baseline. Initial combined regression also
  exposed13 historical migration-test assumptions, corrected as described above.
- Existing Starlette/httpx and Alembic config deprecation warnings remain.

Full final suite: **269 passed**, 273 existing deprecation warnings, exit0.
Tested implementation commit: **329d0a40ddb2e48835695c5fe8380fc05cbdb498**. No Docker or genuine UI browser success claimed. No frontend
runtime code changed. A/B/C review and shared deployment are still required.

## Ready-to-send handover (not sent)

A: D's stacked backend uses your reviewed canonical registry/auth boundary and
adds D005 after A001; please review FK/source/audit constraints and the protected
legacy routes. Merge/review your registry first; D will retarget after main contains
it. B: worker-created evidence is used; this review does not certify physical
accuracy. A/D/C: decide whether recovered/interrupted NEW tasks require a dedicated
investigation reason before enabling them; existing retries are retained. C: use
source=analytics plus private bearer for genuine list/read/history/create/update,
parse the union and both error shapes, keep sample mode separate, and call A's ack
API independently with incident_version/idempotency key. Genuine UI verification
follows your integration; no automatic tasks or implicit ack/recovery are added.

## Final sample Chrome regression and hosted CI

Installed headless Chrome executed C's existing sample screen against the isolated
combined API: create/list, assignment, start/completion with notes, cancellation
with reason, page refresh persistence and terminal read-only checks passed;
zero page errors. Completed sample037f9205-4329-4d7a-b8c9-ad5f027ad1d0 and cancelled
sample39db3b8d-ea67-4132-8685-7e786f6abea0 are retained. Vite used API15441.
This is actual sample browser execution, not a genuine incident UI claim.
The optional smoke reused isolated Playwright and installed Chrome; logs/screenshots
are ignored local artifacts, not credentials or tracked datasets.

At inspection A's exact4bfe3ed commit has zero hosted check runs and no registry PR
was returned by the GitHub inventory. CI workflow only triggers push/PR to main
or chore/team-repository-setup, so a D draft stacked onto A's branch does not trigger
it. Local passing tests do not replace required human approval/hosted CI. After
A's dependency lands, retarget D to main and verify exact resulting CI head before
human merge. No workflow or teammates' branch was changed to bypass this.

Only task-owned test API/Vite are stopped after completion. The native isolated
cluster and all existing databases/records are preserved; test credential revoked.
Assignment owner remains an operator-entered display label, not an authenticated
principal or per-asset authorization rule. Trusted audit records the acting UUID.
