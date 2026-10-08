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
