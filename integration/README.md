# Integration, Validation & Maintenance Subsystem

**Owner**: Person D (Integration, QA & DevOps Engineer)

## Scope & Responsibilities
- Automated end-to-end integration test suites across backend, analytics, and frontend.
- Maintenance workflow tracking and lifecycle state transitions.
- Deployment pipelines, container orchestration, and continuous integration enhancements.
- System-wide benchmarking, stress tests, and demonstration scripts.
- Architecture documentation, operational runbooks, and validation reports.

## Getting Started
- Integration workflows use Docker Compose: `compose.yaml`.
- Automated test entrypoint: `.\.venv\Scripts\pytest.exe backend/tests`.
- CI definitions: `.github/workflows/ci.yaml`.

## Telemetry admission and restart verification

From the repository root with migrated Compose services:
`python integration/verify_telemetry_ingestion.py`
or PowerShell `& .\integration\verify-telemetry-ingestion.ps1`.
The script creates a unique demonstration asset/run, proves retries create exactly one
reading/job, normally restarts db/backend and verifies persistence. It adds demo records
without deleting existing data. See `backend/docs/telemetry-ingestion.md`.

## Normal-operation simulator

From repository root with backend dependencies installed and the local Docker API ready:

```powershell
python -m integration.verify_normal_operation_simulator --base-url http://127.0.0.1:8000
# Equivalent when that Python environment is active:
& .\integration\verify-normal-operation-simulator.ps1
```

Creates a unique synthetic demonstration asset/configuration and six readings; checks
exact payload history, pending jobs, latest, stream isolation and duplicate reading/job
counts through API plus scoped read-only Docker database inspection. Keeps all existing
records/volumes, performs no restarts, and retains ignored generated artifacts. See
[usage and Windows commands](../docs/normal-operation-simulator.md) and
[actual cloud evidence](../docs/normal-operation-simulator-verification.md).
