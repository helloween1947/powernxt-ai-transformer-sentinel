# Incident registry executed verification — 9 October 2026

Source base: main `f52f56515c38fce55451fd499be81ef2508e6677`; branch
`feature/persona-incident-registry`. Tested source hashes and actual HTTP responses
are recorded in [structured evidence](incident-registry-evidence.json). Publication
commit is supplied by Git history, without a self-referential invented test hash.

## Executed checks

- Linux cloud, Python 3.12, dedicated PostgreSQL 16 container on loopback15439.
  Development backend/database/worker and environment files were untouched.
- `TEST_DATABASE_URL=<isolated ..._test database> python -m pytest backend/tests -q --tb=short`:
  **246 passed**, 0 failed, 252 existing Starlette/Alembic deprecation warnings,
  80.54 seconds. No test exclusions or dependency/CI changes.
- Merged `analytics/contracts/test_incident_contract.py`: **9 passed** in0.30s.
  JSON Schema test dependency installed in a separate /tmp target, not the existing
  environment or runtime requirements. Proposal fixtures remain historical.
- After a trailing-blank-line cleanup, final incident regressions: **23 passed**,
  0 failed, 28 dependency warnings, 11.92 seconds; byte hashes reflect final files.
- Targeted Ruff checks on A's incident API/models/schemas/service/operator CLI,
  migration/tests and integration verifier: passed. git diff --check passed.
- Fresh full-chain migration upgrade to **a001_incident_registry** passed on an
  isolated database. Existing upgrade tests cover fresh/84/ce21/D001/D002/both
  prior audit-maintenance heads/D003/d730/D004. Existing asset/config/telemetry/
  job/result/state and sample-task history survive. A new check compares complete
  rows for open/completed/cancelled tasks and history before/after A001.
- Fresh unique-database test passed; Alembic metadata check reports no operations;
  offline upgrade SQL generated. Previous migration revisions are unchanged.
  Registry populated downgrade is refused and rows remain. Empty-only downgrade
  permits existing isolated migration regressions without deleting evidence.
- Atomic result/state/context/incident/evidence/event/job rollback, expired/stale
  fencing, concurrent same-claim opening and concurrent equivalent/conflicting
  acknowledgement tests passed. Unknown asset/config/result, authenticated roles,
  invalid/expired/revoked identity, schema/nonfinite input, stale versions,
  conflicting retries, source/run isolation, history cursors, historical/equal
  readings, unavailable evidence, gap/failure barrier and handover are tested.
- Trusted operator issue/rotate/revoke uses real private test files; tokens are
  never emitted in test reports. Role changes retain actor UUID and old tokens fail.

## Actual HTTP and worker execution

An API running the finalized source on127.0.0.1:15441 used a newly migrated
`incident_registry_final_test` database. Only our temporary API was started or
stopped; the original port8000 backend/database start times remain unchanged.

`python -m integration.verify_incident_registry --base-url http://127.0.0.1:15441
--database-url <isolated test URL> --token-file <private admin file> --output <new evidence path>`:
**PASS**. The repeatable script created one uniquely named synthetic asset/config/
run, enabled an explicitly assumed policy, processed four actual admitted readings
through the fenced worker, retrieved opening evidence and exact result IDs,
acknowledged through HTTP, then observed sustained recovery with the same canonical
UUID. Condition/ack remain separate. Exact acknowledgement/telemetry retries retain
one incident, three immutable evidence snapshots and four distinct events. Another
run returns no incidents. The example is genuine backend storage on synthetic inputs,
not a field fault or detector accuracy claim. All observed IDs/responses are in JSON.

The verifier was repeated on the finalized source. Earlier test API records were
retained in their isolated database; no development record/volume was deleted.
A/B thermal numerical model remains1.0.1 unchanged; coefficient-free demonstration
thermal quantities stay unavailable. Isolated unit/API tests separately cover
supported thermal initialization, measured-minus-predicted residuals and missing
measurements. No browser or Windows execution is claimed.

D's read-only dependency inspector now reports16 registered tables, one head
A001, declared IncidentBearer and incident/read/evidence/event/ack/control paths.
Those names alone are not treated as proof; the PostgreSQL/HTTP checks above
exercise actual behavior. Existing maintenance source/schema/routes and CI have
zero diff from main; D's sample workflow remains sample-only until D's FK/API work.

## Deployment/review limits

The preserved development API still runs the earlier telemetry-only source and
was not upgraded/rebuilt/restarted. This implementation is a reviewable branch,
not deployed dependencies or a claim of hosted CI. GitHub API availability is
reported at publication. Windows/API command examples are in
[backend usage](../backend/docs/incidents.md); they have not been run on Windows.
No queue/WebSocket delivery, automatic task creation, new GUI, SSO/MFA/tenant RBAC,
model1.0.2 adoption or calibrated health/confidence/fault accuracy is implemented.
D still owns the genuine task FK/union/auth integration; C still owns its UI.
