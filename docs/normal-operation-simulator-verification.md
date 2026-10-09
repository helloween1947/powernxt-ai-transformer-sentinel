# Normal-operation simulator execution evidence

Verified 2026-10-08 in the Linux Codex cloud workspace using Python 3.12. This is actual execution against the local Docker API, not a Windows execution claim.

## Tests and static checks

- Full `pytest backend/tests -q`: **115 passed**, including 28 simulator tests (27 generation/sender tests and one isolated PostgreSQL API sequence test), plus the existing 87 backend tests.
- Tests used the dedicated PostgreSQL `sentinel_test` database at host port5433, creating/dropping only fixture-owned temporary schemas. Development database schemas/data were not cleared. Existing Starlette/httpx and Alembic deprecation warnings remain.
- Ruff check and format checks for simulator code, tests and integration script passed after review cleanup.
- Curated example packets validate against actual `TelemetryCreate`, contain UUID4-compatible identifiers, and regenerate identically from the recorded snapshot/specification.

## Actual Docker integration

Command from repository root:

```bash
.venv/bin/python -m integration.verify_normal_operation_simulator
```

Result:

```json
{
  "status": "PASS",
  "asset_id": "demo-normal-ee0939653a0f41f59e075f7f17af5a10",
  "source": "simulator",
  "run_id": "normal-ee0939653a0f41f59e075f7f17af5a10",
  "configuration_version": 1,
  "sample_count": 6,
  "first_submission": {
    "created": 6,
    "identical_duplicates": 0,
    "failures": 0
  },
  "resubmission": {
    "created": 0,
    "identical_duplicates": 6,
    "failures": 0
  },
  "database_counts": {
    "readings": 6,
    "jobs": 6
  },
  "latest_measurement_time": "2026-01-01T00:05:00Z",
  "latest_reading_id": 8,
  "analytics_status": "pending",
  "default_device_history_count": 0,
  "output_directory": "data/generated/normal-ee0939653a0f41f59e075f7f17af5a10"
}
```

The script checked ready/connected, created a uniquely labelled demo asset and assumed configuration, fetched its exact registry version, generated the six-packet sequence and submitted through POST `/api/v1/telemetry`. It then resent the exact saved bytes. Read-only database counts confirmed six readings/six jobs both before and after resend. History was fetched in limit2 pages and every original payload was compared to its generated packet; every reading had the explicit configuration reference, pending analytics/job and no out-of-order flag. Default device history was empty. Latest equalled the last history item and final measurement timestamp.

The generated output directory is ignored, retained locally and includes `verification-result.json` in addition to the three generator artifacts. The curated four-packet example under `data/sample/normal-operation/` is committed; it does not claim registry presence.

The standalone generator CLI also fetched the selected configuration and regenerated the six-packet JSONL byte-for-byte into a new output directory. The standalone sender CLI then reported `created=0`, `identical_duplicates=6`, `failures=0` against the same Docker API.

## Scope and Windows evidence

No backend image rebuild, service restart, volume deletion, development migration, analytics execution or browser UI verification was needed or performed for this simulator task. The running Docker service implements the merged ingestion API; the new generator/sender executed from the host Python environment against that real API. Database migration head is unchanged (`84b8976a7d0d`); the isolated tests applied the existing chain in fresh schemas. Generator modules can also be included in a normal future backend image build.

Previously completed Windows migration, readiness, telemetry deduplication and restart-persistence checks are user-reported prior successes. They are not new simulator Windows results. Exact repeatable Windows setup, generation/submission and verification commands are in [normal-operation-simulator.md](normal-operation-simulator.md); the integration script also has a PowerShell wrapper. Those checks remain for the Windows user to execute with their own local IDs.

No analytics accuracy claim follows from this test. Person B should review the declared synthetic envelope, first-order thermal assumptions and magnitude/noise conventions. There are no fault labels, fault generation, replay controls, analytics worker, or WebSockets in this change.
