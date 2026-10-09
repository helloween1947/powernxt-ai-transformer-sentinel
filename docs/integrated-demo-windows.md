# Repeatable Windows electrical and thermal demonstration

Use this guide from the reviewed integration checkout. [Executed evidence](integrated-demo-verification.md) distinguishes the development-browser checks from isolated worker reliability and pagination. No production deployment or calibrated fault detection is implied.

## Revision and dependency selection

`feature/integrated-demo-windows` combines remote main `090d5ee5fdb85ab1c59368cc05c1d009d4469f19` and C's `82e36e03791aa02e815ccd711b036706e24e0ccf` in local merge `e1edce480067587b35ca622742a9e2bf27cfca36`. Main includes D's reviewed maintenance integration; the merge adds C's frontend without removing it. The final source change is optional browser checks and these guides, not new model/application equations.

At the initial 9 October inspection, #5 was merged into `feat/frontend-setup`, #12 into `feat/frontend-api-integration`; those feature-branch merges had not incorporated their full code into main. **During this task, #18 incorporated that prerequisite frontend into main at `7b19626ca49b81e99fc66bdba76fc55d305b8777`.** That concurrent main update was reconciled into this integration branch without conflicts or frontend runtime changes. #16 remains draft on `codex/personc-maintenance-integration`; its dependency code is now in main. Reassess/retarget #16 against main and review its intended comparison/polling addition. Draft #19 contains that addition plus these Windows guides/checks against current main; choose the review route without double-applying changes. Passing checks and mergeability are not approval.

Person B's offline thermal preparation dependency is separately available at `dbe6a426916fab5c9a4d0c5544f68a14240a1cfd` on `feature/personb-thermal-demo`. It is unnecessary when selecting an already stored thermal run. It is used below only for creating a fresh demonstration, not to replace a running image.

## Existing backend and worker

The verified laptop backend is `http://127.0.0.1:8000`, with registry/telemetry/worker migration `d730a91b4c22`. Its deployed source is A's `9d2f9cda817bc6312d00a4fc001050b04b85a2cb`. It is sufficient for stored electrical/thermal views. Its maintenance API returns 404; using the separately mounted Backend maintenance screen requires a reviewed deployment of D's already integrated backend and migration join `d004_worker_maintenance`. That deployment was not performed here.

From the checkout that owns the existing Docker project (the original repository, not a differently named worktree):

```powershell
function Check-Native { if ($LASTEXITCODE -ne 0) { throw "Native exit: $LASTEXITCODE" } }
docker compose --profile analytics ps
Check-Native
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

If those existing containers have merely been stopped, their non-migrating restart command in that same directory is:

```powershell
docker compose --profile analytics start db backend worker
Check-Native
```

Worker startup can process retained pending jobs. `start` does not build, create missing containers, or migrate. A fresh installation or reviewed backend upgrade follows [the worker guide](analytics-worker-windows.md); an unreviewed frontend checkout must not replace development images. For verification use only that guide's **Repeatable integration on isolated Docker data** section. The current main maintenance head is a later reviewed successor to the deployed worker revision; never downgrade or delete data to reconcile it.

## Start the frontend

Actual settings are `VITE_API_BASE_URL` and `VITE_DATA_MODE`. Keep `demo` for the original illustrative screens; Backend readings independently uses real API data. No `.env` is copied or edited.

At integration repository root, in a new PowerShell terminal:

```powershell
function Check-Native { if ($LASTEXITCODE -ne 0) { throw "Native exit: $LASTEXITCODE" } }
$Repo = (Get-Location).Path
Set-Location (Join-Path $Repo 'frontend')
npm.cmd ci
Check-Native
$oldBase = $env:VITE_API_BASE_URL
$oldMode = $env:VITE_DATA_MODE
try {
    $env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
    $env:VITE_DATA_MODE = 'demo'
    npm.cmd run dev -- --host localhost --port 3000 --strictPort
    Check-Native
} finally {
    $env:VITE_API_BASE_URL = $oldBase
    $env:VITE_DATA_MODE = $oldMode
}
```

Open `http://localhost:3000`. Keep the terminal running; Ctrl+C stops Vite. `--strictPort` prevents an unnoticed origin change. If occupied, select a free port and confirm its exact origin is permitted by backend CORS. On this laptop `localhost:3000` was already allowed, so no backend recreation was needed. Preserve all existing CORS origins; change only the confirmed local origin if required. VITE settings are public browser configuration, never credentials.

Frontend working directory verification commands:

```powershell
npm.cmd test
Check-Native
npm.cmd run lint
Check-Native
npm.cmd run build
Check-Native
```

Set the same process-local API settings before building if that build is intended for local preview. No public deployment is part of this guide.

## Obtain this backend's identifiers

Use actual registry/history responses, not a teammate's local numeric IDs:

```powershell
$Base = 'http://127.0.0.1:8000'
$assets = Invoke-RestMethod "$Base/api/v1/assets?limit=100&offset=0"
$assets.items | Select-Object asset_id,name
# Continue with offset=100,200,... if required.
$Asset = Read-Host 'Exact asset_id from this backend'
$configs = Invoke-RestMethod "$Base/api/v1/assets/$Asset/configurations?limit=100&offset=0"
$configs.items | Select-Object version,created_at,thermal_parameters
# Obtain source/run from the retained generator metadata or its creator.
# The APIs intentionally do not discover all simulator runs automatically.
$Run = Read-Host 'Exact stored simulator run_id from this backend'
Invoke-RestMethod "$Base/api/v1/assets/$Asset/telemetry?source=simulator&run_id=$Run&limit=100"
Invoke-RestMethod "$Base/api/v1/assets/$Asset/analytics/latest?source=simulator&run_id=$Run"
```

Each configuration belongs to its specific asset. Distinguish current registry configuration from each reading's bound version. For a fresh demo without an existing registered transformer, run this at repository root instead of selecting an existing asset:

```powershell
$Asset = 'demo-thermal-' + [guid]::NewGuid().ToString('N')
$body = @{asset_id=$Asset;name='DEMONSTRATION - synthetic thermal';location='Assumed simulator lab';timezone='UTC'} | ConvertTo-Json
$registered = Invoke-RestMethod -Method Post -Uri "$Base/api/v1/assets" -ContentType 'application/json' -Body $body
# Illustrative ratings are suitable only for this newly labelled synthetic asset.
$baselineBody = Get-Content 'data/sample/asset-configuration-assumed.json' -Raw
$baselineCreated = Invoke-RestMethod -Method Post -Uri "$Base/api/v1/assets/$Asset/configurations" -ContentType 'application/json' -Body $baselineBody
$BaselineVersion = [int]$baselineCreated.version
Write-Host "New synthetic asset=$($registered.asset_id) baseline=$BaselineVersion"
```

Capture each returned identity. If a POST response is uncertain, inspect registry/configuration history before retrying. Do not apply these sample electrical ratings to an existing real asset. Continue below using the actual returned baseline version.

## Fresh six-reading thermal run

Use an existing project virtual environment with `backend/requirements-dev.txt`, or create one with `py -3.12 -m venv .venv`, then install those declared requirements. `$Python` must be an absolute interpreter path because the helper runs in a separate worktree. The verified laptop used the original checkout's virtual environment.

From integration repository root, after selecting `$Base`, `$Asset`, and a baseline version from this backend:

```powershell
$Repo = (Get-Location).Path
$Python = (Resolve-Path '.venv/Scripts/python.exe').Path # or the existing original-checkout interpreter
$BaselineVersion = [int](Read-Host 'Exact baseline version to preserve')
$Run = 'thermal-' + [guid]::NewGuid().ToString('N')
$Out = Join-Path $Repo "data/generated/$Run"
New-Item -ItemType Directory -Path $Out | Out-Null
$utf8 = [Text.UTF8Encoding]::new($false)
$offset = 0
$baseline = $null
do {
    $page = Invoke-RestMethod "$Base/api/v1/assets/$Asset/configurations?limit=100&offset=$offset"
    $baseline = $page.items | Where-Object version -eq $BaselineVersion | Select-Object -First 1
    $offset += 100
} while (($null -eq $baseline) -and ($page.items.Count -eq 100))
if ($null -eq $baseline) { throw 'Exact baseline not found.' }
$baselinePath = Join-Path $Out 'baseline-configuration.json'
[IO.File]::WriteAllText($baselinePath, ($baseline | ConvertTo-Json -Depth 100), $utf8)

git fetch origin feature/personb-thermal-demo
Check-Native
$Helper = Join-Path $Repo ('.worktrees/thermal-helper-' + [guid]::NewGuid().ToString('N').Substring(0,8))
git worktree add --detach $Helper dbe6a426916fab5c9a4d0c5544f68a14240a1cfd
Check-Native
$payloadPath = Join-Path $Out 'new-configuration-payload.json'
Push-Location $Helper
try {
    & $Python -m integration.prepare_thermal_demo --configuration-json $baselinePath --output $payloadPath
    Check-Native
} finally { Pop-Location }
$payload = Get-Content $payloadPath -Raw
$payload # Review before the next block.
```

Review the exact payload: all electrical settings, cooling, limits, pre-existing provenance and non-null coefficients unchanged. Only missing rise/time constant/loss ratio/exponent receive **40°C / 180min / 5 / 0.8** and explicit `assumed` provenance. The actual helper validates schemas; it never contacts the API. For new helper versions inspect/review their changes before use.

Append once, capture returned version, generate and submit saved packets:

```powershell
# If this POST times out, inspect configuration history before any retry.
$created = Invoke-RestMethod -Method Post -Uri "$Base/api/v1/assets/$Asset/configurations" -ContentType 'application/json' -Body $payload
$Version = [int]$created.version
$snapshotPath = Join-Path $Out 'new-configuration-response.json'
[IO.File]::WriteAllText($snapshotPath, ($created | ConvertTo-Json -Depth 100), $utf8)
& $Python -m backend.app.simulator --base-url $Base generate --asset-id $Asset --configuration-version $Version --run-id $Run --seed 42 --start '2026-01-01T00:00:00Z' --duration-seconds 301 --interval-seconds 60 --initial-oil-temperature-c 45 --configuration-json $snapshotPath --output-dir "$Out/simulator"
Check-Native
& $Python -m backend.app.simulator --base-url $Base send --input "$Out/simulator/telemetry.jsonl"
Check-Native
Write-Host "asset=$Asset source=simulator run=$Run configuration=$Version"
```

If generation rejects real ratings/limits, retain the new configuration and report that incompatibility; do not replace ratings or tune model equations. A sender failure is resolved with the **same** saved JSONL and deduplication, not regenerated identities. Preserve old configurations/results. B's handoff is at `$Helper/docs/person-b-thermal-demo-handoff.md` inside the actual unique helper worktree.

## Presentation sequence

1. Show the fixture banner and select **Backend readings**.
2. Load registered transformers; select the actual asset, **Simulator**, and exact saved run. Click **Load latest reading and history**.
3. Show January measurement times separately from API retrieval/storage clocks. These are historical synthetic samples, not current device readings.
4. Show stored electrical metrics, configuration version, model `stored-reading-top-oil-1.0.1`, and expand **Parameter provenance**.
5. Show six measured points and five independent predictions/residuals. First chronological frame has `initialized_from_measurement_prediction_not_independent` and null prediction/residual. Later intervals are 60s; residual is observed minus predicted, preserving sign.
6. Show latest telemetry versus latest completed analytics. They can differ while work is pending or unavailable. Change to an empty Device/replay stream to show that synthetic data is cleared.
7. Explain that the original Fleet/Alerts/What-if/browser Maintenance views are labelled fixtures. Assumed-model residuals are not fault alerts or automatic maintenance recommendations.

## Optional actual Chrome checks

Install the optional verification tool separately from frontend dependencies at integration root:

```powershell
npm.cmd install --prefix data/generated/browser-tools --no-audit --no-fund playwright
Check-Native
```

In a **new disposable PowerShell terminal**, at frontend working directory, set the values obtained above and an ignored output directory:

```powershell
function Check-Native { if ($LASTEXITCODE -ne 0) { throw "Native exit: $LASTEXITCODE" } }
$Asset = Read-Host 'Exact verified six-reading asset_id'
$Run = Read-Host 'Exact verified six-reading simulator run_id'
$env:NODE_PATH = (Resolve-Path '../data/generated/browser-tools/node_modules').Path
$env:FRONTEND_ORIGIN = 'http://localhost:3000'
$env:BACKEND_URL = 'http://127.0.0.1:8000'
$env:DEMO_ASSET_ID = $Asset
$env:DEMO_RUN_ID = $Run
# Optional: an existing six-reading coefficient-free run on this same asset.
# $env:COEFFICIENT_FREE_RUN_ID = 'actual-original-run'
$env:BROWSER_ARTIFACT_DIR = Join-Path (Resolve-Path '../data/generated').Path ('browser-' + [guid]::NewGuid().ToString('N'))
node tests/analyticsBrowser.cjs
Check-Native
node tests/integratedDemoBrowser.cjs
Check-Native
```

Chrome's standard Windows executable path is used by the original C check. The additional checks accept `BROWSER_PATH` when necessary. The extended script clearly labels HTTP503 and pending/lag response injection; it never mutates worker state. It verifies initial load + six 5s refreshes, then exhaustion; recovery is manual. A physical phone is not represented by 390px browser emulation. Close the disposable terminal to discard its process-local settings.

For a two-page **isolated** simulator stream (21–39 readings), set that stack's actual API/origin/asset/run and run `node tests/analyticsPaginationBrowser.cjs`. It is read-only and checks IDs/page return against actual API history; never use the maintenance pagination script to create unrelated development records. This task's separate 22-reading run used duration1261s/interval60s and the retained isolated worker stack, not the normal development worker.

## Safe worker recovery

Execute only **Repeatable integration on isolated Docker data** in [analytics-worker-windows.md](analytics-worker-windows.md). Define `Check-Native` first; use Windows `COMPOSE_FILE="compose.yaml;integration/compose.analytics-test.yaml"`, a unique `analytics_worker_test_` project and free port (normally18002), with matching verification base URL. Save and restore all four guide variables in `finally`. Build normally with `--pull --no-cache`, migrate only the test database, and run `python -m integration.verify_analytics_worker` plus `alembic check`. Finally stop only that isolated project, retaining its volume. Do not stop the development worker, run the development migration block, prune, or use `down -v` for this check.

Expected isolated result: six initial completions, six unchanged retries, eight final readings/jobs/results across two runs, advances `[1,7]`, abandoned-claim recovery attempt2, restart persistence, and no new upgrade operations. Keep browser rendering evidence separate from this reliability result.
