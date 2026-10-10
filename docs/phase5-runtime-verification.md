# Phase 5 Development Runtime Verification Protocol

**Date:** 2026-10-10
**Coordinator:** Person A (Backend Lead & Integration Coordinator)
**Status:** **AWAITING EXECUTION APPROVAL** (Preparation and Rehearsal PASSED)
**Candidate Source:** [`42db6aa99e19d5cf15a31a982998a4d462aa62f7`](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/commit/42db6aa99e19d5cf15a31a982998a4d462aa62f7) (Branch: `feature/phase4-full-implementation`)
**Upgrade Plan Reference:** [`docs/phase5-upgrade-plan.md`](phase5-upgrade-plan.md)
**Rehearsal Record Reference:** [`docs/phase5-rehearsal-verification.md`](phase5-rehearsal-verification.md)
**Evidence Record:** [`docs/phase5-evidence.json`](phase5-evidence.json)

---

## 1. Execution Barrier Notice

> [!WARNING]
> **Pending Execution Authorization:**
> The local development upgrade plan has been fully rehearsed and verified in an isolated environment.
> Modifying long-running development services (`sentinel-postgres` on port 5433, `sentinel-backend` on port 8000, and demo frontend on port 3000) is strictly gated until explicit authorization is granted by the repository owner.
> This protocol specifies the verification steps to be executed immediately following authorized upgrade application.

---

## 2. Post-Upgrade Verification Checklist & Commands

Following execution of the upgrade steps in [`docs/phase5-upgrade-plan.md`](phase5-upgrade-plan.md), Person A and the technical team will execute and verify each of the following gates on the upgraded development runtime:

### Gate 1: Running Image & Process Identity
Confirm that the running container images match the approved candidate revision:
```powershell
docker inspect sentinel-backend --format "{{.Config.Image}} {{.Image}}"
# Expected image: sentinel-backend:phase5-candidate-42db6aa (sha256:1d3417c9...)
docker inspect powernxt-ai-transformer-sentinel-worker-1 --format "{{.Config.Image}} {{.Image}}"
# Expected image: sentinel-backend:phase5-candidate-42db6aa (sha256:1d3417c9...)
```

### Gate 2: Database Migration Head & Schema Consistency
Confirm single migration head `d006_combined_integration` and zero schema drift:
```powershell
docker exec sentinel-postgres psql -U sentinel -d sentinel_db -t -A -c "SELECT version_num FROM alembic_version;"
# Verified output: d006_combined_integration

docker run --rm --network host -e DATABASE_URL="postgresql+psycopg://sentinel:sentinel_dev_pw@127.0.0.1:5433/sentinel_db" sentinel-backend:phase5-candidate-42db6aa alembic -c /workspace/backend/alembic.ini check
# Verified output: No new upgrade operations detected.
```

### Gate 3: Historical Demonstration Preservation
Verify that canonical demonstration stream `demo-normal-85203b1018bc498c8b90873f383cc740` retains all historical records and Model 1.0.1 identity:
```powershell
py -3 -c "
import urllib.request, json
url = 'http://127.0.0.1:8000/api/v1/assets/demo-normal-85203b1018bc498c8b90873f383cc740/analytics/latest?source=simulator&run_id=thermal-144c79522cbd4cd092b7718fea4b05fe'
with urllib.request.urlopen(url) as r:
    data = json.loads(r.read())
    assert data['latest_completed_reading_id'] == 25
    assert data['result']['model_version'] == 'stored-reading-top-oil-1.0.1'
    print('Historical demo stream preserved 100%')
"
```

### Gate 4: Historical What-if Immuntability
Verify that What-if scenario forecasting on historical streams uses Model 1.0.1 dispatch and causes zero database mutations:
```powershell
py -3 -c "
import urllib.request, json
url = 'http://127.0.0.1:8000/api/v1/assets/demo-normal-85203b1018bc498c8b90873f383cc740/what-if'
payload = {
    'schema_version': 'what-if-request-1.0.0',
    'source': 'simulator',
    'run_id': 'thermal-144c79522cbd4cd092b7718fea4b05fe',
    'baseline': {'duration_s': 3600.0, 'thermal_load_pu': 1.0, 'ambient_temperature_c': 25.0},
    'reduced_load': {'duration_s': 3600.0, 'thermal_load_pu': 0.7, 'ambient_temperature_c': 25.0}
}
req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())
    assert data['model']['model_version'] == 'stored-reading-top-oil-1.0.1'
    print(f'Historical What-if executed: Model 1.0.1, delta={data[\"final_temperature_difference_c\"]:.2f} C')
"
```

### Gate 5: Model 1.0.2 Handover & Stale Rejection
Confirm that Model 1.0.2 is adopted for newly activated streams while stale Model 1.0.1 attempts are rejected with HTTP 409:
- Handover endpoint: `POST /api/v1/assets/{asset_id}/detector-handovers`
- Model 1.0.2 request returns HTTP 201 with new detector epoch.
- Model 1.0.1 request returns HTTP 409 (`unsupported_model_version`).

### Gate 6: Worker Loop & Genuine Incident Lifecycle
Verify end-to-end telemetry ingestion, overload incident opening, versioned acknowledgement, and genuine maintenance task creation (`alert_source: "analytics"`).

### Gate 7: Browser UI Verification
Confirm:
1. Operator authentication via `OperatorAuthBar` displays active role badge.
2. Stream triage console (`BackendIncidents`) renders live incidents and event timeline.
3. What-if console (`BackendWhatIf`) displays side-by-side trajectories and explicit "Conditional healthy-model estimates" disclaimer.
4. Maintenance console (`BackendMaintenance`) allows switching between sample alerts and genuine incident-linked tasks.

---

## 3. Incident Rollback Criteria

If any of the post-upgrade verification checks fail:
1. **Stop Writes:** Immediately stop the worker container (`docker stop powernxt-ai-transformer-sentinel-worker-1`).
2. **Execute Recovery:** Run the rollback procedure in Section 6 of [`docs/phase5-upgrade-plan.md`](phase5-upgrade-plan.md).
3. **No Improvised Downgrades:** Never attempt manual Alembic downgrades or SQL column drops against live data. Restore exclusively from the verified binary backup.
