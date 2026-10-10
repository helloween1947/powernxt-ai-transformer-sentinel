# Phase 3 Shared Raw Evidence Index

**Candidate Reference:** `feature/persona-phase3-combined-integration`  
**Pure Code Merge HEAD SHA:** `311c10a45f9b5fb5dbef695e2195b58436c0bbdd`  
**Evidence Checksum Manifest:** [`docs/evidence/evidence-checksums.sha256`](file:///C:/Users/marka/.gemini/antigravity/scratch/powernxt-ai-transformer-sentinel/docs/evidence/evidence-checksums.sha256)  

---

## 1. Overview & Raw Evidence Policy

To unblock **Person C** and **Person D**'s independent technical audits without relying on second-hand summaries or assertions, this index catalogs the raw, unedited execution logs captured from isolated Docker and database verification of the Phase 3 candidate.

All artifacts were generated against the isolated candidate stack (`sentinel-phase3-candidate`) and isolated test database (`127.0.0.1:55433/sentinel_phase3_test`). Development services and volumes were untouched.

---

## 2. Shared Artifacts Catalog

| File Path | Description & Scope | Confirmed Exit Code / Status | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| [`docs/evidence/docker-build.log`](file:///C:/Users/marka/.gemini/antigravity/scratch/powernxt-ai-transformer-sentinel/docs/evidence/docker-build.log) | Clean Docker build log of `sentinel-backend:phase3-candidate-311c10a` | Exit 0 | `19e5552957101a6e22040977c834df9b2bd33f5f0b72b7edecbbfa9af0950788` |
| [`docs/evidence/docker-images.json`](file:///C:/Users/marka/.gemini/antigravity/scratch/powernxt-ai-transformer-sentinel/docs/evidence/docker-images.json) | Full Docker image inspect output (digest, layers, architecture) | Valid JSON | `09135f2ab2f4ec714195aca93a02b3e37cf1d327e93a2031e4fa2459244959b4` |
| [`docs/evidence/compose.isolated.sanitized.yaml`](file:///C:/Users/marka/.gemini/antigravity/scratch/powernxt-ai-transformer-sentinel/docs/evidence/compose.isolated.sanitized.yaml) | Sanitized isolated Compose file with ports 55433 & 8801 and isolated volume | Valid Compose | `6e7dcb345b7a23183917f8fd5e0cbe5116f0b79b8806bce34e1c03d1aa02fe02` |
| [`docs/evidence/alembic-migration.log`](file:///C:/Users/marka/.gemini/antigravity/scratch/powernxt-ai-transformer-sentinel/docs/evidence/alembic-migration.log) | Full stdout/stderr of `alembic current` and `alembic check` | Exit 0 (`No new upgrade operations detected`) | `9a6f4a2805e2b02cdc52febd34a79916c95b0c03c9e9ca4e0dc89c4bdf5c0bd7` |
| [`docs/evidence/populated-migration-preservation.json`](file:///C:/Users/marka/.gemini/antigravity/scratch/powernxt-ai-transformer-sentinel/docs/evidence/populated-migration-preservation.json) | Populated migration records across 18 tables seeded at `d004`, upgraded to `d006`, and verified | Valid JSON (100% field parity) | `f75b2de52ae2a426870ce165ba7937b00e630f61aaf72e8bbf398bdf1902e1a0` |
| [`docs/evidence/worker-recovery-fencing.log`](file:///C:/Users/marka/.gemini/antigravity/scratch/powernxt-ai-transformer-sentinel/docs/evidence/worker-recovery-fencing.log) | Pytest execution log of analytics worker fencing, claims, and restart | Exit 0 (36 passed) | `f172d122a0f096e26490a0464d912f59dfd934ad7a564faea4f72691f5ce9491` |
| [`docs/evidence/handover-historical-replay.log`](file:///C:/Users/marka/.gemini/antigravity/scratch/powernxt-ai-transformer-sentinel/docs/evidence/handover-historical-replay.log) | Pytest execution log of authenticated handover, 1.0.1 historical replay & What-if | Exit 0 (53 passed) | `428762d33c8693bc1ab3114c8e2fcceefcee7b59ee95b7ed1cd0b5e86719cdb9` |
| [`docs/evidence/live-candidate-verification.json`](file:///C:/Users/marka/.gemini/antigravity/scratch/powernxt-ai-transformer-sentinel/docs/evidence/live-candidate-verification.json) | Live Docker candidate API integration (health, deduplication, 401 barrier, 1.0.2 adoption, 409 rejection, What-if immutability, restart persistence) | PASS | `13264b8f23a0538f7876f7e6df4fb8156b2cc98b864f5cade7d5383196588148` |

---

## 3. Evidence Verification Instructions

To verify the integrity of these raw artifacts in PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 docs/evidence/* | Format-Table -AutoSize
```

Compare the computed hash values against [`docs/evidence/evidence-checksums.sha256`](file:///C:/Users/marka/.gemini/antigravity/scratch/powernxt-ai-transformer-sentinel/docs/evidence/evidence-checksums.sha256). All hashes must match identically.
