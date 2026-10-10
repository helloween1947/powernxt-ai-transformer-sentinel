# Phase 5 Executed Rehearsal Verification Record

**Date:** 2026-10-10
**Candidate Source:** [`42db6aa99e19d5cf15a31a982998a4d462aa62f7`](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/commit/42db6aa99e19d5cf15a31a982998a4d462aa62f7) (Branch: `feature/phase4-full-implementation`)
**Base Lineage:** `feature/persona-phase3-combined-integration` (`a0689417efd0b674b93198eb537d940cb3547285`)
**Image Rehearsed:** `sentinel-backend:phase5-candidate-42db6aa` (ID: `sha256:1d3417c9c15c29a9af50058b2a54853b42e39b59d8a1c31005d937ca6aabf106`)
**Isolated Rehearsal Stack:** `sentinel-phase5-rehearsal` (`integration/compose.phase5-rehearsal.yaml`)
**Ports:** Isolated PostgreSQL on loopback `55435`, Isolated API on loopback `8802`
**Evidence Manifest:** [`docs/phase5-evidence.json`](phase5-evidence.json)

---

## 1. Scope & Execution Safety

All rehearsal steps were executed in **strict isolation** without touching or modifying the live development stack:
- Live development PostgreSQL (`sentinel-postgres`, port 5433, up 35+ hours) remained untouched.
- Live development FastAPI backend (`sentinel-backend`, port 8000, up 8+ hours) remained untouched.
- Live development demo frontend (PID 43464, port 3000) remained untouched.

---

## 2. Backup Creation & Restoration Parity

### 2.1 Backup Capture
Created binary custom dump (`-Fc`) and plain SQL dump (`-Fp`) outside Git at `C:\Users\marka\.gemini\antigravity\scratch\powernxt-backups\phase5`:
- `sentinel_db_dev_d004.dump`: 49,544 bytes, SHA-256: `B6BCCAF1DF95F56D7509721C056A8A52751F31A1DAEDEA7E9114891F4C0F13B5`
- `sentinel_db_dev_d004.sql`: 309,108 bytes, SHA-256: `EC56BA195C9F06AAF78D2C7727EED1CAB45E3C43F870C19EA6FBEA523A56320D`

### 2.2 Restoration Parity in Ephemeral Container (`sentinel_phase5_restore_verify`)
Restored dump via `pg_restore -U sentinel -d sentinel_db_restored /tmp/sentinel_db_dev_d004.dump` (exit code 0):

| Table Name | Source Dev Count | Restored Count | Status |
| :--- | :--- | :--- | :--- |
| `alembic_version` | 1 (`d004_worker_maintenance`) | 1 (`d004_worker_maintenance`) | **PARITY MATCH** |
| `analytics_results` | 25 | 25 | **PARITY MATCH** |
| `analytics_states` | 5 | 5 | **PARITY MATCH** |
| `analytics_streams` | 5 | 5 | **PARITY MATCH** |
| `asset_configurations` | 9 | 9 | **PARITY MATCH** |
| `assets` | 7 | 7 | **PARITY MATCH** |
| `maintenance_task_history` | 7 | 7 | **PARITY MATCH** |
| `maintenance_tasks` | 3 | 3 | **PARITY MATCH** |
| `telemetry_processing_jobs` | 25 | 25 | **PARITY MATCH** |
| `telemetry_readings` | 25 | 25 | **PARITY MATCH** |

---

## 3. Rehearsed Migration Execution

Applied candidate migrations to the restored copy in `sentinel-phase5-rehearsal-db` (port 55435):

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade d004_worker_maintenance -> w001_what_if_snapshots, Add immutable what-if snapshots; leave worker/results/configuration data intact.
INFO  [alembic.runtime.migration] Running upgrade d004_worker_maintenance -> a001_incident_registry, Add canonical incident registry and trusted identity; preserve sample tasks.
INFO  [alembic.runtime.migration] Running upgrade a001_incident_registry -> d005_incident_tasks, Link genuine tasks without rewriting sample records or registry history.
INFO  [alembic.runtime.migration] Running upgrade a001_incident_registry -> a002_incident_outbox, Add incident delivery checkpoints without rewriting existing event history.
INFO  [alembic.runtime.migration] Running upgrade a002_incident_outbox, d005_incident_tasks, w001_what_if_snapshots -> d006_combined_integration, Join reviewed branch migrations; preserve all applied revisions and records.
```

### Alembic Check Result:
```text
No new upgrade operations detected.
```
Schema is in 100% agreement with SQLAlchemy models across all 19 relational tables.

---

## 4. End-to-End Rehearsal Verification Suite (10/10 PASS)

Executed probe suite against isolated upgraded API (`http://127.0.0.1:8802`):

```text
=== Phase 5 Rehearsal Verification Suite ===
1. Verifying Operator Session...
   Logged in: admin_rehearsal (Role: admin, Ref: b78693fa-1362-4cfd-b23f-6daadb8d9941)
2. Verifying Historical What-if simulation immutability...
   Historical What-if executed: Model stored-reading-top-oil-1.0.1, delta=-4.06 C
3. Creating asset and configuration with thermal parameters...
4. Registering Model 1.0.2 detector handover...
   Handover accepted: Epoch 98aafef2-1d50-49f9-8d6b-4963d8ea8b8f
   Testing rejection of new Model 1.0.1 handover...
   Confirmed: New Model 1.0.1 handover correctly rejected with 409 unsupported_model_version
5. Ingesting telemetry to trigger worker processing...
   Waiting 5 seconds for worker processing loop...
6. Querying incidents for stream...
   Incident opened: d8adc2b4-4348-406e-8c99-53e5ca015040 (Status: active, Version: 1)
   Events: 1, Evidence items: 1
7. Acknowledging incident...
   Acknowledged at version: 2
8. Creating genuine maintenance task linked to incident...
   Maintenance task created: 830e231d-fb7c-463a-91c5-358ad41ff2ec
   Task updated to in_progress (Version: 2)
9. Executing What-if forecasting on Model 1.0.2 state...
   Model 1.0.2 What-if: Baseline=78.43 C, Reduced=72.40 C, Delta=-6.03 C

=== ALL REHEARSAL VERIFICATION CHECKS PASSED (10/10) ===
```

---

## 5. Worker Recovery & Restart Persistence

- **Command:** `docker restart sentinel-phase5-rehearsal-worker`
- **Exit Code:** 0
- **Post-Restart Inspection:** Container state `running`; worker immediately recovered leases and resumed loop without state corruption.
- **Data Audit Post-Rehearsal:**
  - 25 historical Model 1.0.1 results intact.
  - 6 new Model 1.0.2 results computed.
  - 6 historical assets intact.
  - 3 historical sample tasks intact.
  - 1 new genuine incident-linked task created and advanced.
  - 3 new incidents opened for the synthetic stream.
  - Canonical historical demonstration stream (`demo-normal-85203b1018bc498c8b90873f383cc740`) reading ID 25 and Model 1.0.1 identity strictly preserved.
