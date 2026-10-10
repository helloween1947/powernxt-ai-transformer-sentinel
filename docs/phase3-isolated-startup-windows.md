# Phase 3 Isolated Startup & Verification Guide (Windows PowerShell)

**Target Candidate:** `feature/persona-phase3-combined-integration`  
**Tested Source Commit SHA:** `311c10a45f9b5fb5dbef695e2195b58436c0bbdd`  
**Isolated Default Ports:** Database: `55433` (maps to internal 5432), API: `8801` (maps to internal 8000)  
**Isolated Volume:** `sentinel_phase3_candidate_data` (zero connection to development volume `sentinel_postgres_data`)  

---

## 1. Overview & Isolation Architecture

This guide provides tested, repeatable PowerShell instructions for **Person C** and **Person D** to reproduce the Phase 3 candidate stack on their local machine without interfering with their running development stack or local databases.

### Isolation Rules
- **Non-Development Ports:** Never bind to development ports `5432`, `5433`, `8000`, or `3000`.
- **Dedicated Volume:** All database writes are isolated to `sentinel_phase3_candidate_data`.
- **No Shared Credentials:** Process-local test credentials are used; development secrets remain untouched.
- **Fail-Safe Shutdown:** Services are stopped with `docker compose stop`; volumes and logs are preserved.

---

## 2. Step-by-Step PowerShell Instructions

### Step 1: Fetch and Check Out Candidate in a Clean Worktree
Run from your primary repository root:

```powershell
# Fetch remote branches
git fetch origin

# Create a clean dedicated worktree for candidate verification
git worktree add -b review-phase3-candidate .worktrees/review-phase3 origin/feature/persona-phase3-combined-integration

# Navigate to the worktree
cd .worktrees/review-phase3

# Verify candidate commit SHA
git rev-parse HEAD
# Output should match the published candidate
```

---

### Step 2: Build Normal Backend & Worker Images
Build the production Docker images from the worktree root:

```powershell
# Build normal backend and worker images for the candidate
docker compose -p sentinel-phase3-candidate -f integration/compose.phase3-candidate.yaml build
```

---

### Step 3: Start Isolated Database Container & Verify Health
Start the isolated PostgreSQL container:

```powershell
# Start database and wait for healthcheck
docker compose -p sentinel-phase3-candidate -f integration/compose.phase3-candidate.yaml up -d --wait db

# Verify database container is running and healthy
docker ps --filter "name=sentinel-phase3-candidate-db" --format "{{.Names}}: {{.Status}} ({{.Ports}})"
# Expected: sentinel-phase3-candidate-db: Up ... (healthy) (127.0.0.1:55433->5432/tcp)
```

---

### Step 4: Apply Isolated Migrations & Verify Sole Head
Run Alembic upgrade inside a clean one-off container against the isolated database:

```powershell
# Upgrade database to candidate migration head
docker compose -p sentinel-phase3-candidate -f integration/compose.phase3-candidate.yaml run --rm --no-deps backend python -m alembic -c backend/alembic.ini upgrade head

# Verify current revision matches d006_combined_integration
docker compose -p sentinel-phase3-candidate -f integration/compose.phase3-candidate.yaml run --rm --no-deps backend python -m alembic -c backend/alembic.ini current
# Expected: d006_combined_integration (head)

# Verify zero schema drift
docker compose -p sentinel-phase3-candidate -f integration/compose.phase3-candidate.yaml run --rm --no-deps backend python -m alembic -c backend/alembic.ini check
# Expected: No new upgrade operations detected.
```

---

### Step 5: Start Backend & Worker Services & Verify Health
Start the backend API and durable analytics worker:

```powershell
# Start backend and worker services
docker compose -p sentinel-phase3-candidate -f integration/compose.phase3-candidate.yaml up -d backend worker

# Verify API liveness
curl.exe -s http://127.0.0.1:8801/health/live
# Expected: {"status":"live","service":"backend-api",...}

# Verify API readiness (database connected)
curl.exe -s http://127.0.0.1:8801/health/ready
# Expected: {"status":"ready","database":"connected",...}
```

---

### Step 6: Prepare Reproducible Test Streams (No Local A IDs)
Create a new synthetic asset and telemetry configuration using standard API calls:

```powershell
# Generate a unique test asset ID
$testAssetId = "asset-test-" + [guid]::NewGuid().ToString("N").Substring(0, 8)

# Register asset
$assetPayload = @{
    asset_id = $testAssetId
    name = "Phase 3 Candidate Test Transformer"
    location = "Isolated Substation Alpha"
    timezone = "UTC"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8801/api/v1/assets" -Method Post -Body $assetPayload -ContentType "application/json"

# Register configuration
$configPayload = @{
    version = 1
    rated_kva = 1000.0
    rated_voltage_v = 11000.0
    rated_current_a = 52.49
    voltage_convention = "line_to_line"
    measurement_side = "primary"
    cooling_type = "ONAN"
    operational_limits = @{
        max_top_oil_temp_c = 105.0
        max_load_pct = 120.0
    }
    thermal_parameters = @{
        ambient_temp_c = 25.0
        oil_time_constant_mins = 180.0
    }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://127.0.0.1:8801/api/v1/assets/$testAssetId/configurations" -Method Post -Body $configPayload -ContentType "application/json"

Write-Host "Created test stream for asset: $testAssetId"
```

---

### Step 7: Local Administrative Token Management (For Authenticated Handover Tests)
For Person D testing administrative handover endpoints without sharing private keys:

```powershell
# Issue process-local admin token
$adminTokenFile = Join-Path $env:TEMP ("admin_token_" + [guid]::NewGuid().ToString("N") + ".txt")

# Set URL for operator tool to target isolated DB
$env:DATABASE_URL = "postgresql+psycopg://sentinel:sentinel_phase3_pw@127.0.0.1:55433/sentinel_phase3_db"

# Issue token
python -m backend.app.operators issue --name "local-test-admin" --role "admin" --token-file $adminTokenFile

$adminToken = (Get-Content $adminTokenFile).Trim()

# Test authenticated endpoint
Invoke-RestMethod -Uri "http://127.0.0.1:8801/api/v1/assets/$testAssetId/model-handovers" `
    -Method Post `
    -Headers @{ Authorization = "Bearer $adminToken" } `
    -Body (@{
        schema_version = "model-control-1.0.0"
        expected_version = 0
        idempotency_key = [guid]::NewGuid().ToString()
        source = "simulator"
        run_id = "test-run"
        configuration_version = 1
        model_version = "stored-reading-top-oil-1.0.2"
        reason = "Local isolated verification handover"
    } | ConvertTo-Json) `
    -ContentType "application/json"

# Revoke token after verification
python -m backend.app.operators revoke --name "local-test-admin"
Remove-Item -Force $adminTokenFile
```

---

### Step 8: Start Frontend Against Isolated API (Person C)
To verify the frontend dashboard against this isolated backend:

```powershell
# Navigate to frontend directory
cd frontend

# Install exact locked dependencies
npm ci

# Launch test Vite server on non-standard port 3001 pointing to isolated API (port 8801).
# Note: Keep VITE_DATA_MODE=demo so illustrative demo screens remain stable, while the dedicated
# "Backend readings" and "Backend maintenance" screens query the live isolated API at VITE_API_BASE_URL.
$env:VITE_API_BASE_URL = "http://127.0.0.1:8801"
$env:VITE_DATA_MODE = "demo"
npx vite --host localhost --port 3001 --strictPort
```

Open `http://localhost:3001` in your browser to inspect live telemetry and analytics.

---

### Step 9: Graceful Stop (Preserving Retained Evidence)
When testing is complete, stop only the candidate containers without deleting the database volume:

```powershell
# Gracefully stop containers
docker compose -p sentinel-phase3-candidate -f integration/compose.phase3-candidate.yaml stop

# Confirm containers are Exited (not running) and volumes are preserved
docker ps -a --filter "name=sentinel-phase3-candidate"
```
