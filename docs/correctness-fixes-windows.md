# Windows handoff after review and merge

These commands are prepared for Windows PowerShell; they were **not executed from Linux**. Run from your existing repository root after the PR is reviewed and merged. Keep the existing `.env`; do not copy the example over it. PostgreSQL host connections use 5433, while Compose backend connections use `db:5432`.

The first block stashes tracked/untracked local work if needed, retaining the stash without applying it to a different branch. Ignored `.env` and generated data remain in place. Record `$previousBranch` and `$savedWork` for restoration later. Each native command is checked before proceeding.

```powershell
function Assert-NativeSuccess {
    if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE); stop and inspect its output." }
}
$previousBranch = git branch --show-current
Assert-NativeSuccess
$savedWork = $null
$localChanges = git status --porcelain
Assert-NativeSuccess
if ($localChanges) {
    git stash push --include-untracked -m "before-reviewed-correctness-update"
    Assert-NativeSuccess
    $savedWork = git rev-parse refs/stash
    Assert-NativeSuccess
    Write-Host "Retained stash $savedWork from branch $previousBranch"
}
git fetch origin
Assert-NativeSuccess
git switch main
Assert-NativeSuccess
git pull --ff-only origin main
Assert-NativeSuccess
git log -1 --format="%H %s"
Assert-NativeSuccess
```

Confirm the checked-out merged source contains the reviewed migration below before proceeding. A fast-forward failure needs resolution preserving local commits; do not reset or force-push.

Build with the repository Dockerfile and declared dependencies. If the build fails, stop: do not claim a clean build or proceed with an older image. Fix Docker Desktop/network/trust configuration using trusted sources; do not disable TLS verification.

```powershell
if (-not (Test-Path "backend/migrations/versions/20261008_ce21c3b8140a_enforce_configuration_immutability.py")) {
    throw "Reviewed migration is absent; verify the PR has merged and main is updated."
}
docker compose build --pull --no-cache backend
Assert-NativeSuccess
docker compose up -d db
Assert-NativeSuccess
docker compose stop backend
Assert-NativeSuccess
docker compose run --rm backend alembic -c backend/alembic.ini upgrade head
Assert-NativeSuccess
docker compose up -d --no-build backend
Assert-NativeSuccess

$baseUrl = "http://127.0.0.1:8000"
$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $response = Invoke-WebRequest "$baseUrl/health/ready" -UseBasicParsing
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}
if (-not $ready) { throw "Backend did not become ready; inspect docker compose logs backend db." }
Invoke-RestMethod "$baseUrl/health/live"
Invoke-RestMethod "$baseUrl/health/ready"
docker compose exec -T backend alembic -c backend/alembic.ini current
Assert-NativeSuccess
docker compose exec -T backend alembic -c backend/alembic.ini check
Assert-NativeSuccess
```

Expect head `ce21c3b8140a` (unless a subsequent reviewed migration extends it) and `No new upgrade operations detected`. The migration prevents SQL UPDATE/DELETE of historical configurations; append a version instead. Upgrade preserves existing rows. Downgrade to `84b8976a7d0d` removes the protection without deleting rows, so use a reviewed maintenance procedure rather than routine rollback. Linux downgrade testing was confined to isolated data.

Use Python 3.12 and repository-declared dependencies to run the existing scripts. These scripts create unique demonstration assets/configurations/readings and pending jobs. Simulator exports go to ignored `data/generated/`. The registry and telemetry scripts **normally restart backend and database**, temporarily interrupting service; execute those two during a maintenance window. No volume deletion is required.

```powershell
if (-not (Test-Path ".venv/Scripts/python.exe")) {
    py -3.12 -m venv .venv
    Assert-NativeSuccess
}
& .\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Assert-NativeSuccess
& .\.venv\Scripts\python.exe -m integration.verify_normal_operation_simulator --base-url $baseUrl
Assert-NativeSuccess
& .\.venv\Scripts\python.exe -m integration.verify_asset_registry --base-url $baseUrl
Assert-NativeSuccess
& .\.venv\Scripts\python.exe -m integration.verify_telemetry_ingestion --base-url $baseUrl
Assert-NativeSuccess
Invoke-RestMethod "$baseUrl/health/ready"
```

Expect simulator PASS: six created readings/jobs, six identical retries, latest measurement `2026-01-01T00:05:00Z`, analytics pending, and zero default device-history records for that demonstration. Registry and telemetry should report successful persistence checks; identical telemetry resubmission should leave one reading and one job.

Save the actual outputs with the checked-out commit and timestamp as Windows evidence. Earlier user-reported Windows checks are retained in the audit as historical evidence, not verification of this correction revision. When you choose to resume the original branch, inspect the retained stash first; the following optional block applies it without dropping it:

```powershell
if ($savedWork) {
    git stash show --stat $savedWork
    Assert-NativeSuccess
    git switch $previousBranch
    Assert-NativeSuccess
    git stash apply $savedWork
    Assert-NativeSuccess
}
```

Do not run the schema-creating PostgreSQL test suite against the development database. Its isolated test configuration is separate from these API demonstrations.
