# Person D: first maintenance milestone

Verification snapshot: implemented locally on `persond` before publication.
For current publication/integration status, see `docs/persond-publication.md`.
See `docs/persond-review-handover.md` for branch evidence, review and checks.
The first milestone was reverified during continuation. The current extension,
assignment/status/history contract, prerequisite review and demonstration steps
are in `docs/persond-maintenance-workflow.md`.

## What this adds

A clearly labeled sample alert becomes one shared, persistent maintenance task.
You can create it, retrieve it by ID and list tasks for an asset. An identical
retry returns the same task rather than creating a duplicate. Restarting the
backend does not remove it.

This extends A's FastAPI application, SQLAlchemy sessions, asset registry and
PostgreSQL/Alembic setup. There is no separate application or alternative database.
No new production dependencies were added. B's analytics are not required.
The action is supplied by the caller; this does not calculate a recommendation.

## Provisional API for C

These are new, proposed maintenance interfaces, not changes to A's event contract.
They need team agreement before connecting genuine alerts.

| Request | Result |
| --- | --- |
| `POST /api/v1/maintenance/tasks` | 201 on creation; 200 on an identical retry |
| `GET /api/v1/maintenance/tasks/{task_id}` | 200 with one task; 404 if absent |
| `GET /api/v1/maintenance/tasks?asset_id=sample-transformer-d&limit=20&offset=0` | 200 with `{items, limit, offset}` |

`asset_id` is optional on list requests. Pages are ordered by creation time and
task ID; limit is 1–100 and offset is nonnegative.

Copyable request fixture: `integration/fixtures/sample-maintenance-task.json`:

```json
{
  "alert": {
    "source": "sample",
    "alert_id": "sample-cooling-inspection-001",
    "asset_id": "sample-transformer-d",
    "summary": "Illustrative alert for maintenance API verification; not a detector result."
  },
  "action": "Sample task: arrange a cooling-system inspection for demonstration only."
}
```

The asset must already exist in A's registry. One nested asset field is the source
of truth; the response's top-level asset ID is derived from it. An extra top-level
asset ID is rejected, preventing contradictory relationships. A sample alert ID
must start with `sample-`. Its identity is scoped to its asset and source. This
milestone accepts a caller-supplied sample snapshot, not a lookup into an alert
registry (none is implemented). It cannot authenticate a genuine alert's origin.

Required strings are trimmed, must be nonblank, and have length limits. Unknown
fields are rejected. Unsupported sources, malformed IDs, missing required fields
or invalid pagination return 422. Unknown assets return 404. Reusing the same
asset/source/alert ID with different summary or action returns 409. Database
failures return 503 without raw database details. Concurrent retries serialize
using A's asset row lock; a database uniqueness constraint is the backstop.

Example response from the actual HTTP smoke check:

```json
{
  "id": "f892495a-0da1-42b0-95b9-bac16c192035",
  "asset_id": "sample-transformer-d",
  "alert": {
    "source": "sample",
    "alert_id": "sample-cooling-inspection-001",
    "asset_id": "sample-transformer-d",
    "summary": "Illustrative alert for maintenance API verification; not a detector result."
  },
  "action": "Sample task: arrange a cooling-system inspection for demonstration only.",
  "status": "open",
  "created_at": "2026-10-08T16:57:40.780437Z",
  "owner": null,
  "notes": "",
  "version": 1,
  "updated_at": "2026-10-08T16:57:40.780437Z"
}
```

IDs and timestamps are generated values. A new database will produce different
ones. The POST response also includes `Location` for retrieving the task.

C's current `api.js` uses camelCase fields, capitalized statuses, an array of
tasks, and PATCH updates. The workflow extension now provides assignment,
notes, validated status updates and history. Use the reusable adapter in
`integration/frontend/maintenanceAdapter.mjs`; C must also send the retrieved
version and explicit demo actor. See the current workflow runbook before
connecting the screen. Acknowledgement remains pending.

## Run on this prepared Windows workspace

All commands below are PowerShell. Open a terminal in this exact repository:

```powershell
Set-Location 'C:\Users\hrami\OneDrive\Documents\ChatGPT\final powernext\powernxt-ai-transformer-sentinel'
```

This changes your terminal's working folder. The project is the subfolder above,
not its parent, which has an unrelated empty Git repository.

Dependencies are already installed. To recreate them if necessary:

```powershell
if (!(Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install 'psycopg[binary]==3.2.13'
```

The virtual environment keeps Python packages inside this project. The second
install chooses a compatible version allowed by A's requirements: Windows
Application Control blocked the initially resolved 3.3.6 binary, whereas 3.2.13
worked. No machine policy was changed.

During the original milestone WSL was absent. WSL now lists a running Ubuntu
WSL 2 distribution, but Docker still reports that it cannot start; listing a
distribution does not establish a working Docker deployment. The project uses an
isolated PostgreSQL 18 cluster at `.venv\persond-pgdata`, on loopback port 55432.
It contains `sentinel_test` and `sentinel_d_demo`. The existing Windows PostgreSQL
service and its databases were not used or modified. This cluster uses local
trust authentication for the demonstration; its data folder is Git-ignored.

Start the prepared cluster and apply migrations to the demo database:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D '.venv\persond-pgdata' -l '.venv\persond-postgres.log' -o '-h 127.0.0.1 -p 55432' start
$env:DATABASE_URL = 'postgresql+psycopg://sentinel@127.0.0.1:55432/sentinel_d_demo'
$env:CORS_ORIGINS = '["http://localhost:5173","http://127.0.0.1:5173"]'
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

`pg_ctl` starts the isolated database. Alembic applies A's migrations followed by
`d001_maintenance` and `d002_task_workflow`, which add tasks and history. Uvicorn starts the API;
leave that terminal open. These commands are for the already prepared workspace.
If the cluster is already running, skip the start command. Do not recreate an
existing data folder. Open `http://127.0.0.1:8000/docs` to inspect the API.

In a **second** PowerShell terminal, change to the same repository folder, then:

```powershell
.\.venv\Scripts\python.exe integration/verify_maintenance.py
```

This creates the sample asset if absent, submits the fixture, checks retrieval,
checks duplicate retry and checks the filtered list. Expect `PASS` and task JSON.
It is safe to repeat with unchanged fixture content.

To submit a request yourself, run in that second terminal after the smoke check
has registered the sample asset:

```powershell
$sampleBody = Get-Content 'integration/fixtures/sample-maintenance-task.json' -Raw
$task = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/maintenance/tasks' -ContentType 'application/json' -Body $sampleBody
$task | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/maintenance/tasks/$($task.id)"
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/maintenance/tasks?asset_id=sample-transformer-d&limit=20&offset=0'
```

`$sampleBody` reads the JSON fixture. `$task` saves the API response, so its ID can
be reused without replacing any placeholders. All commands above copy directly.
To test another asset later, replace the fixture's asset ID with an actually
registered ID and use a new `sample-...` alert ID. This is sample data only.

### Verify persistence

Press Ctrl+C in the first terminal to stop Uvicorn. Restart with the same command:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In the second terminal, where `$task` still exists:

```powershell
.\.venv\Scripts\python.exe integration/verify_maintenance.py --task-id $task.id
```

Expect `PASS: previously saved sample task retrieved` and the same ID, action and
creation time. Persistence lives in PostgreSQL, not in the running Python process.
Deleting `.venv\persond-pgdata` would delete this local demonstration data.

### Run tests

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://sentinel@127.0.0.1:55432/sentinel_test'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

The test database name must end in `_test`. Each database test migrates its own
temporary schema and removes only that schema afterwards. This does not use the
demo task. Expect 125 passing tests with the current extension. The first-milestone
file `backend/tests/test_maintenance.py` still contains 15 tests; the new workflow
file `backend/tests/test_maintenance_workflow.py` adds 23 tests.

After stopping Uvicorn, stop the isolated database while preserving its files:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D '.venv\persond-pgdata' stop -m fast
```

### On a teammate's fresh checkout

Use A's PostgreSQL/Compose setup, install backend dependencies, set `DATABASE_URL`
to that team's development database, and apply `alembic upgrade head` before
starting Uvicorn. Use an isolated `_test` database for `TEST_DATABASE_URL`.
The native cluster above is local runtime state and will not be uploaded by Git.

## Review and upload your changes

The implementation is uncommitted. `persond` tracks `origin/persond`; it was
fast-forwarded from `c9e3f0d` to shared `main` at `26efab6`. This introduces the
already merged shared foundation into the branch without a feature-branch merge.
A and C's remote branches remain untouched. There were no existing project edits
to preserve in this freshly cloned checkout.

Run from the repository root. `git diff` shows tracked registration changes;
open the new files too, since untracked files are not shown by that first diff.
The staged diff below includes all new files for review.

```powershell
git status --short --branch
git diff
git add backend/app/api/__init__.py backend/app/api/maintenance.py backend/app/models/__init__.py backend/app/models/maintenance.py backend/app/schemas/maintenance.py backend/app/services/maintenance.py backend/migrations/versions/20261008_d001_add_sample_maintenance_tasks.py backend/migrations/versions/20261008_d002_add_task_workflow_history.py backend/tests/test_maintenance.py backend/tests/test_maintenance_workflow.py integration/fixtures/sample-maintenance-task.json integration/verify_maintenance.py integration/frontend/maintenanceAdapter.mjs integration/frontend/maintenanceAdapter.test.mjs integration/frontend/verifyMaintenanceApi.mjs docs/persond-first-milestone.md docs/persond-review-handover.md docs/persond-maintenance-workflow.md
git diff --cached --check
git diff --cached
git commit -m "Add persistent maintenance tasks with validated workflow and history"
git push -u origin persond
```

`git add` selects exactly the 18 contribution files. `git diff --cached` lets you
review everything selected. `git commit` records your work locally. The final
command uploads it to your branch; run it only after your review. No force push
is needed. If Git rejects the push because the remote changed, fetch and inspect
that change before reconciling it. Never force-push to resolve that situation.

Do not add `.venv`, local database files, `.env`, logs, caches or the separate
`personc-review` checkout. No push, commit, message or shared-branch merge was
performed in this session.
