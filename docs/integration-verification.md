# Combined integration verification — 9 October 2026

## Maintenance integration handover: CLOSED

Merged main tested: **7b19626ca49b81e99fc66bdba76fc55d305b8777**.
GitHub confirms PR18 merged into main at this commit. Both clean local checkouts
were synced by fast-forward only; existing branches/local work were preserved.
C's authoritative component/client and exactly one Backend maintenance mount
are present. No application compatibility fix was required.

[Backend CI on this exact merged commit passed](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/actions/runs/37965114062).
The earlier full proposal checks below remain historical; the short actual
Chrome run here is fresh verification on merged main, not an assumption from
PR status. No unchanged local full suite was repeated.

Actual Chrome smoke using the retained isolated PostgreSQL test database:

- Created/listed two new labelled sample tasks through C's screen.
- Assigned Sample smoke maintainer; open v1 -> assigned v2 -> in_progress v3 ->
  completed v4 with notes, and terminal editor read-only.
- Cancelled a separate open sample task with a reason, version2/read-only.
- Reloaded the page and retrieved both records with the saved statuses, owner,
  versions and sample provenance; no uncaught page errors.

Completed ID: bed09a61-9942-4c9a-b27f-e1eb3b7275ab.
Cancelled ID: a4aea234-a7e7-46e3-8aac-1398153f895d.
Smoke asset: sample-merged-smoke-1ab14d32.
No existing records/databases/volumes were removed. Temporary services are
stopped after verification; isolated sample records and artifacts are retained.
The update publishing this closeout changes documentation only.

This closes the **sample-alert / demo-identity maintenance integration** handover.
It does not establish genuine incidents, authenticated operators, full live
forecast/dashboard operation or Docker deployment. Existing native startup
commands and earlier full conflict/pagination/offline/restart results below
remain applicable; this closeout intentionally ran the shorter requested smoke.

Remaining incident-feature prerequisites: accepted A/B/D identity/version and
worker-detector contracts; canonical incident UUID/epoch/asset-stream binding;
durable incident/evidence/history/outbox and retrieval APIs; explicit versioned
acknowledgement/idempotency with trusted identity/authorization; and D's genuine
incident FK/schema migration preserving sample data. Physical recovery,
acknowledgement and task status must stay independent. No next feature was added.

Ready-to-send: merged main7b19626 has C's authoritative maintenance screen and
passing exact-commit CI. Fresh Chrome smoke passed create/list, assignment,
start/completion with notes, cancellation and refresh persistence, with zero page
errors. The sample/demo maintenance integration handover is closed. Incident
tasks/acknowledgement still require adopted contracts, persistent registry and
versioned APIs, trusted identity and a reviewed genuine-task migration. Existing
data was preserved; no Docker/production claim or incident feature was added.

---

The following sections retain the pre-merge baseline and full proposal verification.


## Exact baseline and the integration defect

Tested fetched main: **090d5ee5fdb85ab1c59368cc05c1d009d4469f19**.
Source was a new clean worktree, not the old combined preview. GitHub confirms:

| PR | Actual merge destination / commit | In tested main? |
| --- | --- | --- |
| 9 backend | main / 090d5ee | Yes |
| 10 superseded D UI | persond / 04a4f2c | No |
| 12 C maintenance | feat/frontend-api-integration / ff6918d | No |

A real Chrome baseline check found only Fleet/Transformer/Alerts/What-if/
Maintenance navigation. Backend maintenance was absent. Therefore the report
that all three PRs merged did not establish a combined application on main.

The focused D integration branch normally incorporates C's reviewed API branch
**ff6918d300b79a83023f2b10e937f45e2f034b9f**, retaining C's history. This brings
C's backend readings, maintenance and stored-analytics frontend to main for
review. No C product component/client was rewritten. Backend code has zero diff
against tested main. The published PR records the exact candidate commit.
These successful integrated results are on this proposal, NOT deployed/merged main.

## Duplicate and startup review

PR10 added D's same-named BackendMaintenance component, maintenanceClient,
mount patch and browser verifier only to persond after PR9 merged. Bringing that
head wholesale to main would conflict with C's authoritative component and retain
redundant clients/patch. This proposal excludes that superseded UI implementation.
It has one C component, one C maintenance service/adapter and one App mount;
no duplicate backend route is introduced. D's independent mapper and HTTP
verification tools already on main are preserved. A new independent
verifyCombinedPersistence.cjs exercises C's screen, not the superseded mount.

Alembic has exactly **d004_worker_maintenance** as head; a fresh isolated database
successfully upgraded using ordinary upgrade head. Analytics and maintenance
routers/models coexist; backend migration, metadata, CORS and validation checks
passed. D001-D004 history was not rewritten. Environment API origin is
VITE_API_BASE_URL=http://127.0.0.1:8000; both localhost:5173 and127.0.0.1:5173
browser origins are permitted by the backend. Restart Vite after changing its
environment. Vite was started with --strictPort to avoid a hidden origin change.

VITE_DATA_MODE remains the default demo mode: Fleet, forecast/what-if and the
older Maintenance screen use labelled fixtures/browser storage. The separate
Backend readings and Backend maintenance screens use real backend requests.
Do not claim full live dashboard/forecast or genuine sensor/incident integration.

## Actual verification outcomes

| Check | Actual outcome |
| --- | --- |
| Fresh isolated application database upgrade | Passed, final D004 head |
| Full backend suite on integrated checkout | 222 passed,57.30s; PostgreSQL18/Python3.13 |
| Frontend npm test | 20 passed |
| Frontend lint and production build | Passed |
| Independent D mapper suite | 3 passed |
| Chrome workflow with real API/PostgreSQL | Passed |
| Chrome pagination with real records | 22 tasks and22 history events,20/2 pages; passed |
| Actual stopped backend | Visible connection error; creation disabled; no fixture fallback |
| Actual backend process restart | All four workflow tasks,versions/history persisted; terminal editors read-only |
| Latest B proposal schema checks at5813c64 | 11 passed; proposal validation only |

Actual Chrome workflow: create/list; reject unassigned start; assign; start;
reject completion without notes; complete with notes; terminal read-only;
inspect history; competing API update causes409; retrieve latest saved note,
retain browser draft, block save until explicit review, then use returned version;
cancel from open and in_progress only with a reason; full-page refresh persists
records. Wrong telemetry run/source produces an honest empty404 result.
Real GET/POST/PATCH CORS succeeded, with no uncaught page errors.

Completed task: fcea4e6d-c57c-4499-9ff8-5acf69fefd8e, version4.
Other real workflow task IDs: d33cc95d-7d1b-48ad-9c69-6915d3b6abfb (open,v3),
81d12490-9c28-4eea-83f3-d272f805557e (cancelled,v2),
904c56b8-66c0-41e5-9fb2-41fd072e6a7c (cancelled,v3).
All survived backend restart with their expected history counts.
Pagination history task:8ab60994-dc2a-49ea-a85a-6ee67977e29b,22 versions.

Separate intercepted browser checks cover failed409 detail retrieval, terminal
latest state, telemetry null/zero and pagination controls. Those are fixtures,
not server persistence proof.390px touch emulation also passed; no physical
phone was tested. Offline/restart results above used an actually stopped API,
not route interception. The harness waits for readiness after restart; its early
startup probe originally ran before the server was ready and was corrected.
The initial seeding probe used an incorrect telemetry field and received422;
the final reusable seeder uses the documented timestamp field and passed.

One uniquely created application database persond_combined_e6035c2e5839_test
was retained with its sample records. Automated tests cleaned only their own new
schemas/fresh test databases. Existing application databases/volumes were not
removed or migrated. Logs and screenshots are ignored local artifacts under
.venv/combined-browser-results in the original checkout. Temporary API/Vite and
test PostgreSQL services are stopped at completion; data is preserved.
Docker's Linux-engine pipe remains unavailable: no Docker deployment is verified.

## Reproduce the tested native startup

These are the actual Windows setup paths for this run. Existing Python/runtime
and isolated PostgreSQL cluster were reused; the new frontend installed its own
node_modules with npm ci. Use a new generated database; do not reuse production
or reset an existing database. PostgreSQL must allow creation of a test database.

```powershell
$taskRuntime = 'C:\Users\hrami\OneDrive\Documents\ChatGPT\final powernext\powernxt-ai-transformer-sentinel'
$taskCheckout = 'C:\Users\hrami\OneDrive\Documents\ChatGPT\final powernext\persond-combined-verification'
$taskPython = "$taskRuntime\.venv\Scripts\python.exe"
$taskDatabase = 'persond_combined_' + [guid]::NewGuid().ToString('N').Substring(0,12) + '_test'
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D "$taskRuntime\.venv\persond-pgdata" -o '-p 55432 -h 127.0.0.1' start
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h 127.0.0.1 -p 55432 -U sentinel -d sentinel_test -c "CREATE DATABASE $taskDatabase"
$env:DATABASE_URL = "postgresql+psycopg://sentinel@127.0.0.1:55432/$taskDatabase"
Set-Location $taskCheckout
& $taskPython -m alembic -c backend/alembic.ini upgrade head
& $taskPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

If the task-owned cluster is already running on55432, skip its start command.
The database role/trust configuration is the existing isolated development setup,
not production identity. Keep the backend terminal running. In a second terminal:

```powershell
Set-Location "$taskCheckout\frontend"
npm.cmd ci
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173 and select Backend maintenance. In a third terminal,
seed only labelled sample data and run the browser verifiers:

```powershell
Set-Location $taskCheckout
& $taskPython integration/seed_combined_demo.py --output "$taskRuntime\.venv\combined-seed.json"
$taskSeed = Get-Content "$taskRuntime\.venv\combined-seed.json" -Raw | ConvertFrom-Json
$env:DEMO_ASSET_ID = $taskSeed.asset_id
$env:DEMO_RUN_ID = $taskSeed.run_id
$env:FRONTEND_ORIGIN = 'http://127.0.0.1:5173'
$env:BACKEND_ORIGIN = 'http://127.0.0.1:8000'
$env:NODE_PATH = "$taskRuntime\.venv\browser-check\node_modules"
$env:BROWSER_PATH = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:BROWSER_ARTIFACT_DIR = "$taskRuntime\.venv\combined-browser-results"
node frontend/tests/browserIntegration.cjs
node frontend/tests/paginationBrowser.cjs
node frontend/tests/additionalBrowserChecks.cjs
```

Playwright is a separately installed development dependency in that NODE_PATH,
not a production/frontend dependency. Stop only the backend process, run
node integration/frontend/verifyCombinedPersistence.cjs --offline; restart the
same backend with the SAME DATABASE_URL and run the verifier with --saved.
The seeded six telemetry jobs are intentionally pending; this maintenance
verification does not run the analytics worker or assert physical fault accuracy.

Automated checks use TEST_DATABASE_URL pointing to this isolated *_test database:
pytest backend/tests -q --tb=short, frontend npm test/lint/build, and
node --test integration/frontend/maintenanceAdapter.test.mjs. Individual tests
create their own schemas; do not replace the *_test safety restriction.

## Genuine incident readiness: not ready for task creation/acknowledgement

Reviewed A worker branch b3f8f286e1f67c18c0157ceccadbff516ca4845a and main090d5ee;
B incident proposal912c9fee7c96c9d73ae01c5c6aa8006b95855d73 and latest B audit
5813c64f014026fbbe6e7e64b28cb8845c09ecec. Latest proposal tests:11 passed.

A persists analytics results/state, not canonical incidents. There are no
incident tables, incident/evidence/event routes or acknowledgement endpoint.
B's proposal explicitly awaits A/D acceptance. B's optional sustained detector
is not invoked by A's deployed worker; B's audited model1.0.2/detector1.0.1 is
newer than A's deployed model1.0.1. Schema examples/tests are not persistence.

Required before genuine-incident task creation/acknowledgement:

1. A/B/D adopt versioned detector/worker orchestration and canonical UUID mapping
   from detector_episode_key plus durable detector_epoch; enforce asset/source/run
   binding, retry/restart identity and model/config/policy handover.
2. Persist incident headers, immutable evidence/result references, detector state,
   lifecycle/history and idempotent cursor/outbox delivery in fenced transactions.
   Agree stable incident GET/evidence/events APIs and versioned acknowledgement API.
3. Agree trusted operator identity/authorization and acknowledgement idempotency;
   X-Demo-Actor is not sufficient. Keep physical recovery, acknowledgement and
   maintenance task status independent.
4. Review D's genuine-task schema/FK/idempotency migration and server-side evidence
   lookup while preserving sample rows. Current source=sample constraint rejects
   genuine incidents; do not disguise real IDs as sample IDs or reading IDs.
5. Verify concurrency, replay/delivery, restart/preservation and acknowledgement
   semantics end to end after these prerequisites are implemented and reviewed.

Contract review/design can proceed now. Genuine task creation and acknowledgement
implementation is blocked on these persistence/API/identity agreements. This
verification adds none of that next feature.

## Ready-to-send integration handover (not sent)

Main090d5ee contains D backend, but reported merges10/12 went to persond/C's API
branch, so main still lacked Backend maintenance. D prepared a focused integration
proposal incorporating C ff6918d, excluding the superseded D component/client/
mount and preserving independent verification tools. Real Chrome workflow,
cancellation, history20/2 pagination,409 operator review, refresh and actual
backend outage/restart passed. Backend222/frontend20/mapper3 tests plus lint/build
passed; main's D004 graph and both registrations are sound. Please review the
integration PR before a human main merge. Genuine incident tasks/acknowledgement
are not ready: B's proposal still needs adoption and A's incident registry,
versioned evidence/events/ack APIs, durable detector processing and trusted
identity. No incident feature, Docker deployment or production claim was added.
