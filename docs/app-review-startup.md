# Isolated combined application startup

Use the D review branch from a clean checkout. Requirements: PostgreSQL, Python3.12+ (native evidence used3.13.14), Node22.12+ (evidence used24.19.0), and installed Google Chrome for browser checks. Do not point these commands at a development database. Docker was unavailable during this review; native startup is reproducible but is not Docker verification.

The commands below assume an **already owned isolated PostgreSQL service** at127.0.0.1:55432. If none exists, create a separate cluster/service on an unused port using the PostgreSQL administration instructions; do not restart development or reuse a shared volume. Substitute its port/user consistently.

From repository root in PowerShell:

```powershell
if (Test-Path '.venv') { throw 'Use a new clean review checkout; preserve the existing environment' }
python -m venv .venv
$qaPython = (Resolve-Path '.venv\Scripts\python.exe').Path
& $qaPython -m pip install -r backend/requirements-dev.txt -r analytics/contracts/requirements-test.txt
$qaDatabase = 'persond_review_' + [guid]::NewGuid().ToString('N') + '_test'
createdb -h 127.0.0.1 -p 55432 -U sentinel $qaDatabase
if ($LASTEXITCODE -ne 0) { throw 'New isolated database creation failed' }
$env:DATABASE_URL = "postgresql+psycopg://sentinel@127.0.0.1:55432/$qaDatabase"
$env:CORS_ORIGINS = '["http://127.0.0.1:15882","http://localhost:15882"]'
& $qaPython -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Isolated migration failed' }
& $qaPython -m alembic -c backend/alembic.ini heads
& $qaPython -m alembic -c backend/alembic.ini check
# Expected sole head: d006_combined_integration; no new operations.
& $qaPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 15881
```

In a second terminal, set the same owned `DATABASE_URL` and run the normal worker:

```powershell
& .venv\Scripts\python.exe -m backend.app.workers
```

Use another terminal for the frontend:

```powershell
cd frontend
npm.cmd ci
$env:VITE_DATA_MODE = 'live'
$env:VITE_API_BASE_URL = 'http://127.0.0.1:15881'
npm.cmd run build
npm.cmd run preview -- --host 127.0.0.1 --port 15882 --strictPort
```

Visit `http://127.0.0.1:15882`. Connection settings must match that API origin. CORS includes the **browser origin**, not just the API port. Fleet cards show device streams; selecting a stored simulator run retrieves that run's evidence. Choose the registered asset/source/run and use the global Operator bar for incident workflows. Sample illustrations do not become persisted incidents.

For a private review credential, provision an owned account against the isolated database, writing a **new** private file outside Git:

```powershell
& .venv\Scripts\python.exe -m backend.app.operators issue --name d-app-admin --role admin --token-file C:\PRIVATE_REVIEW_DIRECTORY\admin.txt
```

Create/protect that private directory first. Never paste token values into commands, logs, screenshots or repository files. Enter the credential only in the password input. Roles are `reader`, `operator`, `admin`; server identity is authoritative. These expiring local credentials do not establish production SSO. Revoke owned review accounts when done.

To create repeatable synthetic fixtures with `integration.prepare_app_review`, **pause only the owned review worker**: that helper explicitly executes each worker job itself. Use `--base`, `--database-url`, `--token-file`, `--output`; its database guard requires `persond_review_*_test` on loopback. It records asset/run/incident/sample-task IDs in the output. Restart the separate worker for `integration.extend_app_review`, which deliberately verifies normal processing. Do not run the fixture helper against shared services.

Chrome verifiers require Playwright installed in a tooling environment (not committed `node_modules`); use installed Chrome through `channel: 'chrome'`. Supply `REVIEW_EVIDENCE` containing `seed.json` and protected `private/{admin,operator,reader}.txt`. The auth verifier also needs `REVIEW_PYTHON` and the owned `DATABASE_URL`; it expires/revokes **only** `d-app-reader`/`d-app-operator` in that database. Reissue to new private files before another full run. No credential files belong in published evidence.

```powershell
node integration/verify_app_browser.cjs
node integration/verify_app_auth_browser.cjs
node integration/verify_app_pagination_browser.cjs
```

For the full real offline/restart rehearsal set `REVIEW_RESTART=1`. The browser writes `stop-request.flag`, then waits20s for `stopped.flag`. At that gate snapshot with `integration.snapshot_app_review`, stop **only the known owned API PID**, then write `stopped.flag`. When it writes `restart-request.flag`, restart the same owned API against the same database/CORS, check readiness, compare another snapshot and write `restarted.flag`. Use a fresh evidence directory per full run; existing flags are not proof of a new restart. The normal non-restart invocation does not verify backend restart.

After review, revoke owned credentials and stop only owned Chrome/API/preview/worker processes. Stop the QA cluster only if you started it. Retain databases, evidence and volumes. Restore process-scoped environment variables; never edit `.env` or remove volumes to reset a review.
