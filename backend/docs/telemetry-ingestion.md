# Telemetry ingestion API

The API stores readings and durable pending processing jobs. **Accepted is not analyzed.**
No analytics worker, alerts, simulator, or WebSocket delivery is implemented.
The authoritative field definitions and run/deduplication policies are in
[the telemetry contract](../../docs/contracts/telemetry-contract.md).

## Endpoints

| Method / path | Behaviour |
|---|---|
| `POST /api/v1/telemetry` | 201 first acceptance; 200 identical retry; 409 conflicting delivery key |
| `GET /api/v1/assets/{asset_id}/telemetry/latest` | Latest measurement in one selected stream; 404 if empty |
| `GET /api/v1/assets/{asset_id}/telemetry` | Paginated, filtered history in one selected stream |

Unknown assets return 404. Invalid schema/measurements/flags/timestamps/run selection and
configuration versions not belonging to the asset return 422. Database failures return
sanitized 503 responses. Existing health and registry endpoints remain available. These
routes follow the existing development backend's unauthenticated policy.

POST a registered asset ID and explicit existing `configuration_version`. Use the sample
JSON files as request bodies; they require registering the example asset first. For Person C,
an abbreviated request is:

```json
{
  "schema_version": "1.0.0",
  "message_id": "d053f900-0ea1-4a6c-bb4d-7e3cc0dcffec",
  "asset_id": "XFR-SUB04-TX01",
  "timestamp": "2026-10-08T12:00:00+05:30",
  "source": "device",
  "run_id": null,
  "configuration_version": 1,
  "measurements": {"voltage_r_v": 11000, "current_r_a": null},
  "measurement_quality": {"current_r_a": "missing"}
}
```

The response contains server `id`, stream/asset/message identifiers, bound configuration,
UTC `measurement_time`/`arrival_time`, `original_payload`, `normalized_telemetry`, per-channel
`quality_flags`, `out_of_order`, `analytics_status: "pending"`, and
`processing_job: {"id": ..., "status": "pending", "state_policy": "forward_only"}`.
`normalized_telemetry` contains every channel, with null for missing values and normalized
quality for all channels. The original payload keeps the supplied structure and values.
A complete illustrative response is in
[`data/sample/telemetry-response-sample.json`](../../data/sample/telemetry-response-sample.json);
its IDs/times are illustrative and not a validation result.

History returns `{ "items": [full_reading_responses], "limit": 20, "offset": 0 }`.
Use measurement-time `start` (inclusive) and `end` (exclusive). Both need explicit offsets.
URL-encode a plus sign in offsets as `%2B`; HTTP clients with query parameter builders do this.
Live examples:

```http
GET /api/v1/assets/XFR-SUB04-TX01/telemetry/latest
GET /api/v1/assets/XFR-SUB04-TX01/telemetry?start=2026-10-08T00:00:00Z&end=2026-10-09T00:00:00Z&limit=20&offset=0
```

Replay/simulation queries must specify the stream:

```http
GET /api/v1/assets/XFR-SUB04-TX01/telemetry/latest?source=simulator&run_id=sim-run-20261007-01
GET /api/v1/assets/XFR-SUB04-TX01/telemetry?source=file_replay&run_id=replay-demo-01&limit=20
```

History sorts oldest measurement first, then ascending reading ID. Latest sorts measurement
time first, then greatest ID. A late arrival remains in history and gets a historical-only
job. Equal-time readings also get historical-only jobs. The data has no completed analytical
result; job IDs are durable admission acknowledgements, not detector outputs.

## Windows PowerShell: rebuild, migrate, and verify

Run from the existing Windows checkout. Preserve local changes; Git will refuse switching
when they conflict. Do not remove volumes or reset work. Docker host PostgreSQL port remains
5433 and backend container PostgreSQL address remains `db:5432`.

```powershell
Set-Location 'C:\Users\marka\.gemini\antigravity\scratch\powernxt-ai-transformer-sentinel'
git fetch origin
git switch feature/telemetry-ingestion
docker compose up -d db
docker compose build backend
docker compose run --rm backend alembic -c backend/alembic.ini upgrade head
docker compose up -d --no-build backend
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
& .\integration\verify-telemetry-ingestion.ps1
docker compose exec -T backend alembic -c backend/alembic.ini current
docker compose exec -T backend alembic -c backend/alembic.ini check
```

The PowerShell wrapper needs Python 3.12 on PATH and invokes the standard-library Python
script. It creates a unique labelled demonstration asset and assumed configuration, submits
synthetic simulator telemetry, retrieves it, verifies identical retries return the same
result, and queries the database inside the backend container to prove **one reading and
one pending job**. It normally restarts both services, waits up to 60 seconds for readiness,
checks persistence, and retries again after restart. It never deletes records or volumes.
For environments where scripts cannot run under the local PowerShell policy, invoke directly:

```powershell
python .\integration\verify_telemetry_ingestion.py --base-url http://127.0.0.1:8000
```

Migration `84b8976a7d0d` extends registry revision `f272b723f71b`. It creates only telemetry
readings/jobs, foreign keys, a permanent dedup constraint, a one-job-per-reading constraint,
and a stream/time index. Upgrade does not delete registry data. Downgrade destroys telemetry
history/jobs; run it only in disposable test schemas. Do not regenerate this migration when
applying it on Windows.

## Isolated PostgreSQL tests

CI already provides PostgreSQL 16 with an isolated `sentinel_test` database. The new tests
use the existing per-test migrated schema fixture and require no CI service changes. All
registry, health, and telemetry tests run together with no development-database clearing.
Local example using only the repository's default development credentials (substitute your
securely configured test URL when they differ):

```powershell
docker compose exec -T db createdb -U sentinel sentinel_test  # Once; skip if it exists.
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
$env:CORS_ORIGINS = '["http://localhost:3000","http://localhost:5173"]'
$env:TEST_DATABASE_URL = 'postgresql+psycopg://sentinel:sentinel_dev_pw@localhost:5433/sentinel_test'
python -m pytest backend/tests -v
Remove-Item Env:TEST_DATABASE_URL
```

See [actual verification evidence](../../docs/telemetry-ingestion-verification.md) for checks
run in cloud, user-reported prior Windows results, and checks requiring Windows execution.
