# PowerShell handoff

Prepared commands, **not executed on Windows by this task**. Use after review/merge. Existing user-reported Windows ce21 migration, readiness, consistency and simulator PASS are historical, not worker verification. Keep `.env`, data and volumes. Run at your repository root, with Docker Desktop running.

## Preserve work and update main

```powershell
function Check-Native {
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $LASTEXITCODE; stop and inspect output." }
}
$previousBranch = git branch --show-current
Check-Native
$savedWork = $null
$changes = git status --porcelain
Check-Native
if ($changes) {
    git stash push --include-untracked -m "before-reviewed-analytics-worker-update"
    Check-Native
    $savedWork = git rev-parse refs/stash
    Check-Native
    Write-Host "Retained $savedWork from $previousBranch; do not apply it to main blindly."
}
git fetch origin
Check-Native
git switch main
Check-Native
git pull --ff-only origin main
Check-Native
git log -1 --format="%H %s"
Check-Native
```

Ignored `.env`/generated files stay in place. If main cannot fast-forward, resolve preserving local commits; never reset/force-push. The stash remains retained. Restore later on its original branch using `git switch $previousBranch` then `git stash apply $savedWork`, inspecting conflicts; do not drop it automatically.

## Normal build, reviewed migration and startup

This block updates your development services **only after review/merge**, during a maintenance window. It may process all retained pending backlog when the worker starts. Upgrade the API together with the worker because the old API accepts only pending job status. Do not continue with a failed build or migration.

```powershell
if (-not (Test-Path "backend/migrations/versions/20261009_d730a91b4c22_add_durable_analytics_worker.py")) {
    throw "Reviewed worker migration is absent; verify merged main."
}
docker compose --profile analytics build --pull --no-cache backend worker
Check-Native
docker compose --profile analytics up -d db
Check-Native
docker compose --profile analytics stop backend worker
Check-Native
docker compose --profile analytics run --rm backend alembic -c backend/alembic.ini upgrade head
Check-Native
docker compose --profile analytics up -d --no-build backend worker
Check-Native
$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $response = Invoke-WebRequest "http://127.0.0.1:8000/health/ready" -UseBasicParsing
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}
if (-not $ready) { throw "Not ready; inspect docker compose logs backend worker db." }
Invoke-RestMethod "http://127.0.0.1:8000/health/ready"
docker compose exec -T backend alembic -c backend/alembic.ini current
Check-Native
docker compose exec -T backend alembic -c backend/alembic.ini check
Check-Native
docker compose --profile analytics logs --tail 100 worker
Check-Native
```

Expect head `d730a91b4c22` (or a later reviewed successor) and no new upgrade operations. No destructive downgrade or volume deletion is needed. Downgrade refuses once worker history exists; retain schema/evidence when rolling back application code.

## Repeatable integration on isolated Docker data

The integration refuses the normal development project/API. It requires a unique project prefix, dedicated container/volume overrides and a database ending `_test`, with Compose matching the selected API port. Requires Compose supporting `!override`/`!reset` (2.24.4+). The block creates a separate retained test volume, unique demonstration records and ignored simulator exports. It normally stops/restarts **only its test worker**, including an intentionally abandoned two-second lease; development services are unaffected.

```powershell
if (-not (Test-Path ".venv/Scripts/python.exe")) {
    py -3.12 -m venv .venv
    Check-Native
}
& .\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Check-Native
$oldProject = $env:COMPOSE_PROJECT_NAME
$oldComposeFile = $env:COMPOSE_FILE
$oldPort = $env:ANALYTICS_TEST_PORT
$oldBasis = $env:WORKER_VERIFICATION_IMAGE_BASIS
$env:COMPOSE_PROJECT_NAME = "analytics_worker_test_" + [guid]::NewGuid().ToString("N").Substring(0,8)
# Windows Compose path-list separator is semicolon; Linux uses colon.
$env:COMPOSE_FILE = "compose.yaml;integration/compose.analytics-test.yaml"
$env:ANALYTICS_TEST_PORT = "18002"
$env:WORKER_VERIFICATION_IMAGE_BASIS = "normal repository Dockerfile build executed on Windows"
try {
    docker compose --profile analytics build --pull --no-cache backend worker
    Check-Native
    docker compose up -d db
    Check-Native
    docker compose run --rm backend alembic -c backend/alembic.ini upgrade head
    Check-Native
    docker compose up -d --no-build backend
    Check-Native
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $response = Invoke-WebRequest "http://127.0.0.1:18002/health/ready" -UseBasicParsing
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw "Isolated backend is not ready." }
    & .\.venv\Scripts\python.exe -m integration.verify_analytics_worker --base-url "http://127.0.0.1:18002"
    Check-Native
    docker compose exec -T backend alembic -c backend/alembic.ini check
    Check-Native
} finally {
    docker compose --profile analytics stop worker backend db
    $env:COMPOSE_PROJECT_NAME = $oldProject
    $env:COMPOSE_FILE = $oldComposeFile
    $env:ANALYTICS_TEST_PORT = $oldPort
    $env:WORKER_VERIFICATION_IMAGE_BASIS = $oldBasis
}
```

Choose a different free `ANALYTICS_TEST_PORT` and matching base URL if18002 is in use. Expect PASS: first batch6 completed,6 identical retries, final8 readings/jobs/results across two runs, state advances[1,7], recovery attempts2, restart persistence true. Inspect the returned `asset_id`/`run_id`; API access during verification uses:

```powershell
# Substitute IDs returned by the actual verification while its isolated API is running.
Invoke-RestMethod "http://127.0.0.1:18002/api/v1/telemetry/READING_ID/analytics"
Invoke-RestMethod "http://127.0.0.1:18002/api/v1/assets/ASSET_ID/analytics/latest?source=simulator&run_id=RUN_ID"
```

Save actual outputs with timestamp and full checked-out commit; do not treat the prepared image-basis label as proof without the successful build output. Browser/front-end checks remain separate. Full PostgreSQL tests require a separate explicitly selected `TEST_DATABASE_URL` ending `_test`; never point tests to development data.
