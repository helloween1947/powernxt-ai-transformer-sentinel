# Phase 5 Concrete Local Development Upgrade Plan

**Date:** 2026-10-10
**Coordinator:** Person A (Backend Lead & Integration Coordinator)
**Target Runtime:** Local Development Stack (`sentinel-postgres`, `sentinel-backend`, `sentinel-worker`, demo frontend)
**Candidate Source:** [`42db6aa99e19d5cf15a31a982998a4d462aa62f7`](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/commit/42db6aa99e19d5cf15a31a982998a4d462aa62f7) (Branch: `feature/phase4-full-implementation`)
**Base Lineage:** `feature/persona-phase3-combined-integration` (`a0689417efd0b674b93198eb537d940cb3547285`)
**Verified Candidate Image:** `sentinel-backend:phase5-candidate-42db6aa`
**Evidence Record:** [`docs/phase5-evidence.json`](phase5-evidence.json)

---

## 1. Upgrade Scope & Prerequisites

> [!IMPORTANT]
> **Authorization Barrier:**
> This plan specifies the exact sequence to upgrade the long-running development stack.
> It requires explicit execution authorization from the repository owner before application to existing development containers or database volumes.
> Routine isolated testing and reversible rehearsal have already been executed and verified.

### Affected Services & Estimated Downtime
- **PostgreSQL Database (`sentinel-postgres`, Port 5433):** Zero container downtime; read/write migration lock window ~5 seconds.
- **FastAPI Backend (`sentinel-backend`, Port 8000):** Container restart downtime ~10–15 seconds.
- **Analytics Worker (`powernxt-ai-transformer-sentinel-worker-1`):** Quiescence and container restart downtime ~15–20 seconds.
- **Demo Frontend (Port 3000):** Relaunch with upgraded candidate source ~5 seconds.
- **Total Expected Interruption:** < 30 seconds.

---

## 2. Preflight Checks & Stop Conditions

Before executing any changes on the development environment:

```powershell
# Preflight 1: Confirm 0 active worker leases
docker exec sentinel-postgres psql -U sentinel -d sentinel_db -t -A -c "SELECT COUNT(*) FROM telemetry_processing_jobs WHERE lease_until > NOW();"
# STOP CONDITION: Must output "0". If > 0, wait for leases to expire before proceeding.

# Preflight 2: Confirm clean database connectivity and current migration head
docker exec sentinel-postgres psql -U sentinel -d sentinel_db -t -A -c "SELECT version_num FROM alembic_version;"
# STOP CONDITION: Must output "d004_worker_maintenance".

# Preflight 3: Verify candidate Docker image exists and is ready
docker images sentinel-backend:phase5-candidate-42db6aa
# STOP CONDITION: Must report image tag present.
```

---

## 3. Verified Backup & Restoration References

A full, verified binary custom backup has been created outside Git:

- **Primary Custom Archive:** `C:\Users\marka\.gemini\antigravity\scratch\powernxt-backups\phase5\sentinel_db_dev_d004.dump`
- **File Size:** 49,544 bytes
- **SHA-256 Checksum:** `B6BCCAF1DF95F56D7509721C056A8A52751F31A1DAEDEA7E9114891F4C0F13B5`
- **Plain SQL Archive:** `C:\Users\marka\.gemini\antigravity\scratch\powernxt-backups\phase5\sentinel_db_dev_d004.sql`
- **File Size:** 309,108 bytes
- **SHA-256 Checksum:** `EC56BA195C9F06AAF78D2C7727EED1CAB45E3C43F870C19EA6FBEA523A56320D`
- **Restoration Verified:** Successfully restored and verified into isolated PostgreSQL 16 container (`sentinel_phase5_restore_verify`) with 100% table and row parity.

---

## 4. Exact PowerShell Upgrade Sequence

Execute the following commands upon receiving explicit execution authorization:

### Step 4.1: Quiesce Worker & Create Fresh Pre-Upgrade Backup
```powershell
# 1. Stop background worker to prevent concurrent telemetry claims
docker stop powernxt-ai-transformer-sentinel-worker-1

# 2. Capture fresh pre-upgrade snapshot
docker exec sentinel-postgres pg_dump -U sentinel -d sentinel_db -Fc -f /tmp/sentinel_db_pre_upgrade_final.dump
docker cp sentinel-postgres:/tmp/sentinel_db_pre_upgrade_final.dump "C:\Users\marka\.gemini\antigravity\scratch\powernxt-backups\phase5\sentinel_db_pre_upgrade_final.dump"
Get-FileHash "C:\Users\marka\.gemini\antigravity\scratch\powernxt-backups\phase5\sentinel_db_pre_upgrade_final.dump" -Algorithm SHA256
```

### Step 4.2: Execute Alembic Migration to `d006_combined_integration`
```powershell
# Run migrations using the candidate container against development PostgreSQL (port 5433)
docker run --rm `
  --network host `
  -e DATABASE_URL="postgresql+psycopg://sentinel:sentinel_dev_pw@127.0.0.1:5433/sentinel_db" `
  sentinel-backend:phase5-candidate-42db6aa `
  alembic -c /workspace/backend/alembic.ini upgrade head

# Verify Alembic migration head and schema consistency
docker exec sentinel-postgres psql -U sentinel -d sentinel_db -t -A -c "SELECT version_num FROM alembic_version;"
# Output must be: "d006_combined_integration"

docker run --rm `
  --network host `
  -e DATABASE_URL="postgresql+psycopg://sentinel:sentinel_dev_pw@127.0.0.1:5433/sentinel_db" `
  sentinel-backend:phase5-candidate-42db6aa `
  alembic -c /workspace/backend/alembic.ini check
# Output must be: "No new upgrade operations detected."
```

### Step 4.3: Update Backend Container & Worker Container
```powershell
# Recreate backend and worker with candidate image
docker stop sentinel-backend
docker rm sentinel-backend
docker rm powernxt-ai-transformer-sentinel-worker-1

# Start upgraded backend
docker run -d `
  --name sentinel-backend `
  --restart unless-stopped `
  -p 127.0.0.1:8000:8000 `
  --network powernxt-ai-transformer-sentinel_default `
  -e DATABASE_URL="postgresql+psycopg://sentinel:sentinel_dev_pw@db:5432/sentinel_db" `
  -e ENVIRONMENT="development" `
  -e LOG_LEVEL="INFO" `
  -e CORS_ORIGINS='["http://localhost:3000","http://localhost:5173","http://127.0.0.1:5173"]' `
  sentinel-backend:phase5-candidate-42db6aa

# Start upgraded worker
docker run -d `
  --name powernxt-ai-transformer-sentinel-worker-1 `
  --restart unless-stopped `
  --network powernxt-ai-transformer-sentinel_default `
  -e DATABASE_URL="postgresql+psycopg://sentinel:sentinel_dev_pw@db:5432/sentinel_db" `
  -e ENVIRONMENT="development" `
  -e LOG_LEVEL="INFO" `
  sentinel-backend:phase5-candidate-42db6aa `
  python -m backend.app.workers
```

### Step 4.4: Issue Local Operator Token
```powershell
# Provision local operator credential inside upgraded backend container
docker exec sentinel-backend python -m backend.app.operators issue --name dev_operator --role admin --token-file /tmp/dev_operator.token
docker exec sentinel-backend cat /tmp/dev_operator.token
```

### Step 4.5: Relaunch Frontend with Candidate Build
```powershell
# Relaunch Vite demo frontend pointing to port 8000
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
$env:VITE_DATA_MODE="demo"
# Restart process in .worktrees\phase4-implementation\frontend
```

---

## 5. Post-Upgrade Verification Checklist

Confirm each item before declaring upgrade complete:

1. **API Readiness:** `curl http://127.0.0.1:8000/health/ready` returns HTTP 200.
2. **Historical Data Integrity:**
   - 25 Model 1.0.1 results intact: `SELECT count(*) FROM analytics_results WHERE model_version='stored-reading-top-oil-1.0.1';` = 25.
   - 7 historical assets intact: `SELECT count(*) FROM assets;` = 7.
   - 3 sample tasks intact: `SELECT count(*) FROM maintenance_tasks WHERE alert_source='sample';` = 3.
3. **Historical What-if Replay:**
   - `POST /api/v1/assets/demo-normal-85203b1018bc498c8b90873f383cc740/what-if` returns Model 1.0.1 forecast with 0 worker writes.
4. **Model 1.0.2 Handover for New Streams:**
   - `POST /api/v1/assets/{new_id}/detector-handovers` returns HTTP 201 with allocated epoch.
   - Stale Model 1.0.1 handover attempts return HTTP 409 `unsupported_model_version`.
5. **UI & Incident Operations:**
   - Operator logs into `OperatorAuthBar` using issued token.
   - Incident triage console (`BackendIncidents`) renders without errors.
   - Dual-scenario What-if console (`BackendWhatIf`) displays temperature trajectories and healthy-model disclaimer.

---

## 6. Rollback & Recovery Procedure

If any step fails or unresolvable regressions occur:

```powershell
# 1. Stop upgraded worker and backend
docker stop powernxt-ai-transformer-sentinel-worker-1 sentinel-backend
docker rm powernxt-ai-transformer-sentinel-worker-1 sentinel-backend

# 2. Restore pre-upgrade database from verified backup
docker cp "C:\Users\marka\.gemini\antigravity\scratch\powernxt-backups\phase5\sentinel_db_dev_d004.dump" sentinel-postgres:/tmp/restore.dump
docker exec sentinel-postgres pg_restore -U sentinel -d sentinel_db --clean --if-exists /tmp/restore.dump

# 3. Restart previous backend and worker using original image
docker run -d --name sentinel-backend --restart unless-stopped -p 127.0.0.1:8000:8000 `
  --network powernxt-ai-transformer-sentinel_default `
  -e DATABASE_URL="postgresql+psycopg://sentinel:sentinel_dev_pw@db:5432/sentinel_db" `
  powernxt-ai-transformer-sentinel-backend

docker run -d --name powernxt-ai-transformer-sentinel-worker-1 --restart unless-stopped `
  --network powernxt-ai-transformer-sentinel_default `
  -e DATABASE_URL="postgresql+psycopg://sentinel:sentinel_dev_pw@db:5432/sentinel_db" `
  powernxt-ai-transformer-sentinel-worker python -m backend.app.workers

# 4. Confirm restoration
docker exec sentinel-postgres psql -U sentinel -d sentinel_db -t -A -c "SELECT version_num FROM alembic_version;"
# Output: "d004_worker_maintenance"
```
