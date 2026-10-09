# Person D maintenance assignment and history

Assignment, validated task status changes, completion/cancellation notes and
persistent history are implemented locally on `persond`. The first milestone
still works. This is the pre-publication verification snapshot; current publishing
and integration status is in `docs/persond-publication.md`. All commands below
use **Windows PowerShell and the Windows `.venv`**.
Do not run this virtual environment from Ubuntu/WSL.

## Local work and branch review

Local `persond` remains at `26efab6259524686199ef6a64ca66b541c7eda78`, tracking
`origin/persond` at `c9e3f0d8a4dafea954a1617baea8455f992bf509`. Its seven commits
ahead are already shared main history, not a committed D milestone. Both D
milestones exist in the working tree. No reset, clean or branch merge was used.
Before editing, all 12 original contribution files were copied to the ignored
`.venv/persond-before-workflow-327e69d8a7a640ef91eb0c050bbf37fe` folder.

README, CONTRIBUTING, the original maintenance runbook and backend conventions
were read. No AGENTS.md was found in this repository or the checked workspace
ancestors. The branch tips below were fetched and reviewed on 8 October 2026.

| Remote branch | Reviewed commit | Current work |
| --- | --- | --- |
| `main` | `26efab6259524686199ef6a64ca66b541c7eda78` | Shared A registry/ingestion base |
| `chore/team-repository-setup` | `2619044900e0e0fd1ec76d151559d1ecf868342a` | A foundation |
| `feature/asset-registry` | `b9d1c5d6722887f40941490ddb69207568f911c0` | A registry/config versions |
| `feature/telemetry-ingestion` | `db17a8d8a6f079353bb9795c1eba193d9978e7d3` | A ingestion/history/pending jobs |
| `feature/personb-twin-analytics` | `8183b77226c9615c5338264484d214e9fcd6a1d7` | B callable models and adapter |
| `feat/frontend-setup` | `cc7678c65ce91db526d1f1b93feb70d4319e0aa4` | C original fixture UI |
| `feat/frontend-api-integration` | `a55478654d5cb945ccf4d7134add131314e5a7cd` | C current remote UI/reading helpers |
| `personc` and `persond` | `c9e3f0d8a4dafea954a1617baea8455f992bf509` | Old remote person labels |

No newer C tip appeared in this fetch. C's latest available feature branch is
unchanged since the first review. C and B were inspected in detached worktrees.
A is identified by Markab Debbarma's backend commits, B by Vignesh's analytics
commit, and C by akash-patil18's frontend commits.

A uses FastAPI routers, SQLAlchemy sessions, per-asset row locking, PostgreSQL
constraints and Alembic. It stores assets/configurations, readings and pending
jobs. There is no operator/login/session model, alert table, completed analytics
store or worker invocation of B in the inspected main branch.

B now produces genuine calculated **in-memory incident observations when called
with suitable input**, rather than only a proposed interface. Observations have
`incident_id`, category, severity, lifecycle, evidence/threshold, rationale and
evidence availability. Incident IDs include asset/source/run/config version,
initial measurement epoch, type and sequence. Evidence retains timestamps;
outer `metadata` includes stream, measurement time, configuration and
model/detector versions. Data confidence is channel-availability scoring, not a
calibrated anomaly probability; anomaly scores remain null. Recovery uses
continuous evidence and hysteresis, not task completion. B does not persist or
publish UUID events, and its checked examples are synthetic. A/B/D still need to
agree trusted persisted incident/event identity and transport before real alerts
can create maintenance tasks.

C's maintenance UI currently uses `title`, `owner`, `assetId`, `alertId`,
`evidence`, `recommendation`, `status`, `notes` and `createdAt`. Statuses are
`Open`, `In progress`, `Completed`. It uses browser localStorage in demo mode;
acknowledgement resets with fixture reload. Its provisional live task URL is
`/maintenance/tasks`, list expects an array, and PATCH lacks a version/demo actor.
It has no task-history view, cancellation option or task pagination controls.
The separate Backend readings helpers already use A's versioned APIs. These are
integration boundaries and unfinished work, not failed features.

## Prerequisite checklist

| Condition | Classification | Evidence and impact |
| --- | --- | --- |
| First milestone still works | Verified ready | 15 original tests and original HTTP verifier passed again; original saved task retained |
| Routes registered | Verified ready | Original routes plus PATCH/history exercised through the app and real HTTP |
| Migrations apply | Verified ready | Fresh test schemas and existing D001 demo upgraded; model/schema check passed |
| Asset/sample relationship | Verified ready | Registry FK, known asset required, sample source enforced; no contradictory asset field accepted |
| Trusted real alert relationship | Missing | No persisted alert registry/worker; blocks genuine-alert task creation |
| B incident output/provenance | Verified ready for callable boundary | 33 analytics tests passed in B checkout; backend alert persistence remains missing |
| Genuine incident/event ID mapping | Requires team agreement | B incident IDs differ from shared UUID event envelope; no assumed agreement |
| C direct task contract | Incompatible | URL, field names, statuses, page wrapper and update version differ |
| Reusable C mapping adapter | Verified ready | Three adapter tests and real HTTP adapter check passed; screen is not wired automatically |
| Final C status/paging integration | Requires team agreement | C must import the adapter, keep task versions and expose paging/cancellation/history |
| Assignment/operator identity | Missing registry; requires team agreement | Prototype uses validated display names, not verified operator IDs |
| Actor/session identity | Missing session; requires team agreement | PATCH uses explicitly labeled `X-Demo-Actor`; no authentication claim |
| PostgreSQL persistence | Verified ready | Native PG18 on 127.0.0.1:55432; task and history survived actual backend restart |
| Windows Python/dependencies | Verified ready | Python 3.13.14; existing FastAPI 0.143.0, SQLAlchemy 2.1.4, psycopg 3.2.13, Alembic 1.20.0 used without reinstall |
| WSL CLI/distribution | Implemented but execution unverified | Status lists default Ubuntu/WSL2 running; direct uname probe stalled and was stopped |
| Docker/Compose CLI | Verified ready | Docker client 29.7.2 and Compose 5.4.0; Compose syntax check passed |
| Docker daemon/deployment | Missing ready daemon | `docker version`, container and volume queries return Docker Desktop unable to start; Desktop status says starting |
| Existing containers/volumes | Implemented but unverified inventory | Daemon queries fail; no containers or volumes were deleted |
| Native env example | Incompatible with verified setup | Port/CORS discrepancies described below; explicit local environment avoids them |

The missing operator/session and trusted-alert interfaces can be deferred for
this explicitly sample/demo workflow. They block verified production identity
and genuine-alert integration. Docker blocks the documented container deployment,
but does not block the verified Windows/Python/native PostgreSQL demonstration.

Actual configuration issues reproduced: `.env.example` points to 5432 although
Compose publishes Windows port 5433; its comma-separated `CORS_ORIGINS` raises
`SettingsError` in the installed pydantic-settings before the field validator.
For local Compose-connected Python, A must agree the port correction and JSON
array CORS syntax (or explicitly support comma parsing). Compose's backend
environment already uses JSON CORS and internal `db:5432`, a different context.
The root README also still describes implemented registry/ingestion as upcoming.
No shared settings files were changed in this maintenance milestone.

WSL installation alone has not fixed Docker. The smallest next environment
action is to restart Docker Desktop after the WSL setup and check its startup
diagnostics if the daemon still fails. No global WSL/Docker configuration,
database volume or existing PostgreSQL service was changed. WSL integration with
Docker could not be established while Desktop remained in its starting state.

## Workflow contract

Original create/get/list URLs and required request fields are retained. POST
also accepts optional `owner`, a trimmed nonblank display name up to 100
characters. GET/list responses add nullable `owner`, `notes`, integer `version`
and UTC `updated_at`. New tasks start at version 1. Registered sample-alert
identity/provenance remains unchanged; only source `sample` is accepted.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/maintenance/tasks` | Create sample task, optionally with owner; 201 or 200 on retry |
| `GET /api/v1/maintenance/tasks` | `{items, limit, offset}`; optional asset filter |
| `GET /api/v1/maintenance/tasks/{id}` | Current task and version |
| `PATCH /api/v1/maintenance/tasks/{id}` | Version-checked assignment/status/notes update |
| `GET /api/v1/maintenance/tasks/{id}/history` | History `{items, limit, offset}`, ascending version |

Both paginated endpoints accept limit 1–100 and offset >= 0. PATCH requires a
JSON integer `expected_version` >= 1 and header `X-Demo-Actor`. Do not send an actor
in the body. Send at least one of `owner`, `status`, `notes`. `owner: null`
unassigns an open task; omit fields to retain their values. Notes are trimmed and
limited to 2000 characters. Status/notes cannot be null. No-op updates return 422.

| Current state | Allowed next state | Requirements |
| --- | --- | --- |
| `open` | `in_progress` | Nonblank owner, already assigned or supplied in the same request |
| `open` | `cancelled` | Nonblank reason supplied in this request's notes |
| `in_progress` | `completed` | Owner retained and nonblank completion notes supplied in this request |
| `in_progress` | `cancelled` | Nonblank reason supplied in this request's notes |
| `open` / `in_progress` | Same state | Effective assignment/notes change; in-progress owner cannot be removed |
| `completed` / `cancelled` | None | Terminal tasks are read-only; no reopen or history rewrite API |

Direct open -> completed, in-progress -> open and terminal edits return 409.
Missing owner/notes, malformed input or absent demo actor return 422. Unknown
tasks/history return 404. Stale versions return 409: retrieve the current task,
show the competing change, then explicitly retry using its current version.
Do not silently overwrite or blindly resubmit a stale edit.

Each accepted update takes a PostgreSQL row lock, checks the version, increments
it, and appends history in the **same transaction**. A history-storage failure
rolls back the task change too. History includes previous/new status and owner,
previous/new notes, actor display label, identity source, version and UTC time.
The API only appends history; this is not a tamper-proof/authenticated audit system.

There is no operator registry or established login session. `owner` validates a
prototype display name only. `X-Demo-Actor` is caller-supplied and recorded as
`identity_source: "demo_header"`; it is not authenticated. New task creation has
actor null and `unattributed_creation` to preserve D001 POST compatibility.
Existing tasks receive a truthful version-1 `legacy_import` snapshot at migration
time, without inventing a historical creator. Task completion never modifies the
alert snapshot, recovery or acknowledgement.

POST retries with no owner retain D001 compatibility and return the current task.
If owner is explicitly provided on a retry it must match the current owner; use
PATCH for reassignment. Summary/action conflicts retain the original 409 rule.

Example PATCH (actor supplied separately in the header):

```json
{"expected_version": 1, "owner": "Demo maintainer", "status": "in_progress", "notes": "Sample inspection started"}
```

Next PATCH:

```json
{"expected_version": 2, "status": "completed", "notes": "Sample inspection completed"}
```

The real HTTP check completed task `e71e973f-ef06-4417-93e6-4a01c4c86042` at
version 3, owner `Demo maintainer`, status `completed`, notes `Sample inspection
completed`. It returned three history entries: open -> in_progress -> completed.
Both updates recorded actor `Person D demo operator` with demo_header provenance.
The ID, status, notes, versions and history were unchanged after backend restart.

The corresponding API task response includes these actual fields:

```json
{
  "id": "e71e973f-ef06-4417-93e6-4a01c4c86042",
  "asset_id": "sample-transformer-d",
  "alert": {
    "source": "sample",
    "alert_id": "sample-workflow-e5e68302-f226-4992-8e48-003135b38431",
    "asset_id": "sample-transformer-d",
    "summary": "Explicit sample fixture; no genuine detector output."
  },
  "action": "Sample cooling inspection",
  "status": "completed",
  "created_at": "2026-10-08T17:22:37.205705Z",
  "owner": "Demo maintainer",
  "notes": "Sample inspection completed",
  "version": 3,
  "updated_at": "2026-10-08T17:22:37.228022Z"
}
```

## Run and demonstrate on this prepared laptop

Open **Windows PowerShell** in the actual repository, not its parent:

```powershell
Set-Location 'C:\Users\hrami\OneDrive\Documents\ChatGPT\final powernext\powernxt-ai-transformer-sentinel'
```

Dependencies are already working; no install is needed for this continuation.
The isolated database files and both databases from the first milestone remain.
Start the cluster if stopped, set the explicit demo connection/CORS, upgrade,
then start the API:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D '.venv\persond-pgdata' -l '.venv\persond-postgres.log' -o '-h 127.0.0.1 -p 55432' start
$env:DATABASE_URL = 'postgresql+psycopg://sentinel@127.0.0.1:55432/sentinel_d_demo'
$env:CORS_ORIGINS = '["http://localhost:5173","http://127.0.0.1:5173"]'
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Migration order is A registry -> A telemetry -> D001 -> `d002_task_workflow`.
The additive D002 migration keeps existing IDs, creation times and sample alerts.
It backfills owner=null, notes="", version=1 and an import history snapshot.
Its downgrade refuses to erase used workflow data. Apply migrations before
starting the updated app. No new dependencies or database engine were introduced.

In a second PowerShell terminal, change to the same folder, then:

```powershell
.\.venv\Scripts\python.exe integration/verify_maintenance.py
node integration/frontend/verifyMaintenanceApi.mjs
```

The first command repeats your original milestone. The second creates a new
sample task using C's mapped fields, assigns a demo maintainer, starts/completes
it, checks history/list mapping and verifies stale-update rejection. It prints
PASS, task/history JSON and a restart command containing its generated ID.
No npm installation is needed for these Node scripts.

For a manual demonstration after the original verifier has registered the sample
asset, copy these commands into the second terminal. They contain no placeholders:

```powershell
$taskDemoBody = Get-Content 'integration/fixtures/sample-maintenance-task.json' -Raw | ConvertFrom-Json
$taskDemoBody.alert.alert_id = 'sample-manual-' + [guid]::NewGuid().ToString()
$task = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/maintenance/tasks' -ContentType 'application/json' -Body ($taskDemoBody | ConvertTo-Json -Depth 5)
$taskDemoHeaders = @{ 'X-Demo-Actor' = 'Person D demo operator' }
$taskChange = @{ expected_version=$task.version; owner='Demo maintainer'; status='in_progress'; notes='Sample inspection started' } | ConvertTo-Json
$task = Invoke-RestMethod -Method Patch -Uri "http://127.0.0.1:8000/api/v1/maintenance/tasks/$($task.id)" -Headers $taskDemoHeaders -ContentType 'application/json' -Body $taskChange
$taskChange = @{ expected_version=$task.version; status='completed'; notes='Sample inspection completed' } | ConvertTo-Json
$task = Invoke-RestMethod -Method Patch -Uri "http://127.0.0.1:8000/api/v1/maintenance/tasks/$($task.id)" -Headers $taskDemoHeaders -ContentType 'application/json' -Body $taskChange
$task | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/maintenance/tasks/$($task.id)/history" | ConvertTo-Json -Depth 5
```

The generated alert ID creates a separate demonstration task on each run.
`$task` stores each API response so the next update uses its current version.
Expect `completed`, owner `Demo maintainer`, version 3, and history versions 1–3.
To demonstrate cancellation instead, use a fresh task and PATCH status `cancelled`
with a nonblank reason in `notes`. A completed task cannot be cancelled afterwards.

Press Ctrl+C in the server terminal and restart Uvicorn using the same command.
In the second terminal, retrieve the manual demo task and history again:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/maintenance/tasks/$($task.id)" | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/maintenance/tasks/$($task.id)/history" | ConvertTo-Json -Depth 5
```

For the automatic Node demo, use its printed restart command. Only its generated
task ID varies; use the exact value printed by that run. The session's already
verified task can be checked directly with:

```powershell
node integration/frontend/verifyMaintenanceApi.mjs 'http://127.0.0.1:8000' 'e71e973f-ef06-4417-93e6-4a01c4c86042'
```

Run tests from the repository root while the isolated PostgreSQL cluster runs:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://sentinel@127.0.0.1:55432/sentinel_test'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
node --test integration/frontend/maintenanceAdapter.test.mjs
```

Expect 125 backend tests and three adapter tests to pass. Tests use temporary
schemas in the dedicated `_test` database, not the saved demonstration tasks.
When finished, stop Uvicorn with Ctrl+C and stop only this isolated database:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D '.venv\persond-pgdata' stop -m fast
```

The cluster is loopback-only with local trust authentication for demonstration.
Its files are ignored by Git and preserved when stopped. Do not remove the data
folder or recreate the working virtual environment to run this continuation.

## Instructions for C and merge order

The adapter lives under D's `integration/frontend/`; no C-owned UI files changed.
Import/copy the small mapper into C's API layer after agreement:

- Use versioned `/api/v1/maintenance/tasks` URLs.
- Map current create fields through `toCreateRequest(uiTask, {sampleMode: true})`
  only for explicitly labeled sample alerts. Unlinked what-if/manual tasks are
  outside this milestone. Use a registered backend asset ID; browser fixture
  IDs are not automatically registered or mapped to real assets.
- Map responses through `toFrontendTask` and page responses through
  `toFrontendPage`; the existing screen can use `.items` while retaining the
  returned limit/offset for pagination controls. Do not hide subsequent pages.
- For PATCH, call `toUpdateRequest(changes, savedTask.version)`, send the demo
  actor header, then retain the returned version. Add cancellation and read-only
  terminal controls; show 422 validation errors and 409 conflict/reload guidance.
- Add reassignment/history UI later as needed. The backend already supports them.
  Keep acknowledgement separate; no acknowledge/recover endpoint was added.

There are no duplicate maintenance endpoints or conflicting migrations on the
reviewed B/C branches. B changes only analytics; C's changes relative to its
common base are frontend-only. Its older tip lacks A's backend, so a two-tip
diff looks like backend deletion; this is branch ancestry, not a C deletion
commit. Integrate reviewed frontend changes onto shared main, not by replacing
main with C's older repository snapshot.

Required order: A's already merged main base, then D001/D002 maintenance migration
and API, then C's agreed adapter/UI connection. B can be reviewed independently;
real incident persistence/worker/event wiring must precede genuine-alert task
creation. B's backend image integration also needs analytics copied into the
container; Docker/production integration and expanding CI are deferred.

An isolated detached `../persond-integration-check` checkout combines main with
copies of D's local files, B's analytics and C's tracked frontend files. No branch
merge was performed. Its backend/analytics checks confirm coexistence, not a
finished worker, browser workflow or deployment.

## Files and validation

Extended: maintenance schema/model/service/API and model registration. Added:
D002 migration, 23 workflow tests, C mapper/three tests/live verifier, and this
runbook. Updated both existing maintenance documents. D001, original task fixture
and original verifier/test file remain unchanged from the first milestone.
The complete Git selection is 18 files across both uncommitted milestones; see
the exact `git add` list in `docs/persond-first-milestone.md`.

Checks completed in this continuation:

| Check | Result |
| --- | --- |
| First milestone before extension | 15 tests passed; original verifier and saved-task retrieval passed |
| Current full backend suite | 125 passed: 87 A + 15 original D + 23 workflow |
| Workflow coverage | Assignment/unassignment, transitions/notes, actor/version validation, unknown tasks, paging, two concurrent writers, atomic rollback, fresh-process persistence, D001 data preservation, guarded downgrade passed |
| D002 on existing demo database | Passed; original task preserved |
| Alembic model/migration check | No new upgrade operations detected |
| Original HTTP verifier after extension | Passed |
| Adapter tests | 3 passed |
| Actual HTTP adapter demo and backend restart | Passed; same completed task/history/version retrieved |
| B detached checkout | 33 analytics tests passed, including six backend compatibility checks |
| C detached checkout | Lint/build and six telemetry adapter tests passed |
| Isolated main+D+B+C checkout | 158 backend/analytics tests plus three mapper tests passed |
| Compose configuration syntax | Passed; daemon/deployment unavailable |

No complete C browser integration, PostgreSQL 16 container run, Docker deployment,
authenticated identity, real alert ingestion or production audit integrity was
verified. Existing Starlette/Alembic deprecation warnings do not fail the tests.

## Review and upload

Use the exact 18-file `git add` command in the updated first-milestone runbook.
Review `git status`, then the staged diff before committing. Commit message:
`Add persistent maintenance tasks with validated workflow and history`.
Upload with `git push -u origin persond` only after your review; do not force-push.
No commit, push, PR, shared merge or message was performed here. Ignore local
`.venv` snapshots/data/logs and all detached review/integration checkouts.

## Ready-to-send teammate message

> My branch is `persond`. Both maintenance milestones are implemented locally:
> labeled sample-alert task creation/retrieval/listing, plus assignment, validated
> status changes, required completion/cancellation notes, and persistent history.
> Task updates and history commit atomically; stale versions return 409.
>
> Existing POST/GET `/api/v1/maintenance/tasks` and GET `/{id}` remain. New PATCH
> `/{id}` takes `expected_version` and optional owner/status/notes; new GET
> `/{id}/history` returns `{items, limit, offset}`. Responses add owner, notes,
> version and updated_at. States: open -> in_progress -> completed, or cancel
> from open/in_progress. Completed/cancelled tasks are read-only. Apply D001 then
> D002 (`d002_task_workflow`) before starting the API.
>
> Identity is explicitly prototype-only: owner is a display name, and PATCH uses
> caller-supplied `X-Demo-Actor`, recorded as demo_header. No operator/session
> verification is claimed. Tasks remain sample alerts; completion never recovers
> or acknowledges an alert.
>
> A: review migration/API registration and agree trusted alert persistence and
> operator/session identity. B: your incident observations/provenance were
> inspected/tested; we still need persisted incident/event identity and worker
> transport before creating genuine-alert tasks. C: use the mapper under
> `integration/frontend`, retain task versions, unwrap paginated items, and agree
> status/assignment/conflict UI behavior. Your current screen still uses fixtures
> and browser storage; it has not been automatically connected.
>
> Verification: 125 backend tests, three mapping tests, real HTTP updates/history
> and actual restart persistence passed. B's 33 tests and C's lint/build/six
> adapter tests passed. The isolated combined checkout passed backend/analytics
> checks (158 tests). Docker still cannot provide a ready daemon despite WSL listing Ubuntu
> WSL2; the demo uses isolated Windows PostgreSQL18. Full browser/deployment,
> real-alert integration, acknowledgement and incident summaries remain pending.
> Changes are local, uncommitted and unpushed. No teammate branches were modified.
