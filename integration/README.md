# Integration, Validation & Maintenance Subsystem

**Owner**: Person D (Integration, QA & DevOps Engineer)

For combined backend acceptance, use `python -m integration.run_backend_completion`;
see [isolated Windows startup/recovery](../backend/docs/backend-completion-operations.md).
This uniquely scoped coordinator replaces the old hard-coded phase3 candidate
verifier. It captures clean builds, exact exits, full suites, successful live
workflows and real backup restoration without targeting development.

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

## Durable analytics worker

`python -m integration.verify_analytics_worker --base-url http://127.0.0.1:18002` requires the dedicated `compose.analytics-test.yaml` override and a unique `analytics_worker_test_` project. It refuses development containers/volumes/API, creates unique assumed demonstration records, normally restarts its test worker and checks unfinished lease recovery. See [exact startup and Windows commands](../docs/analytics-worker-windows.md). Existing ingestion-only verifiers assume the worker is disabled; use the worker-specific verifier when processing is enabled.


## Current combined application verification

See [integration-verification.md](../docs/integration-verification.md) for the
exact tested main, C-authoritative integration proposal, native startup, real
browser versus fixture results and genuine-incident prerequisites. The merged
PR numbers alone do not establish that their changes reached main.

## Incident runtime dependency inventory

Run `python -m integration.inspect_incident_dependencies` from repository root
with backend dependencies installed. This read-only local inventory does not
connect to a database or certify contract acceptance/runtime readiness. See
[post-merge dependency results](../docs/persond-incident-dependency-verification.md).

## Genuine incident maintenance (stacked draft)

See [D verification](../docs/persond-genuine-maintenance-verification.md) and
[request/auth/migration contract](../docs/contracts/incident-maintenance-contract.md).
`python -m integration.verify_incident_maintenance --help` describes isolated
live worker/API and restart verification. Requires A registry + D005 and a private
admin credential; creates labelled synthetic records and retains them. No automatic
task creation, acknowledgement coupling or genuine UI/deployment claim.
