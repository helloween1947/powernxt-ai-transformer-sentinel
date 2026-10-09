Sensor deliveries previously had no durable ingestion or retrieval workflow. This adds
POST /api/v1/telemetry and per-asset latest/history endpoints, preserving raw JSON and
normalized UTC measurements with missing channels kept null. Every accepted reading is
atomically stored with one pending processing job; acceptance does not claim analytics.

Permanent deduplication within asset/source/run is enforced by PostgreSQL uniqueness and
serialized admission. Identical retries return the original reading/job; changed content
under the same key returns 409. Explicit asset configuration versions are checked by a
composite foreign key. Late/equal-time readings are retained with historical-only jobs;
latest uses measurement time with an ID tie-breaker. Live and replay/simulator streams
remain separate. Invalid input/fault labels are rejected and implausible values are flagged
without replacing them or clamping them.

Migration 84b8976a7d0d extends registry revision f272b723f71b. It applied to the retained
cloud development database while preserving existing registry records. API/contract docs,
sample requests/responses and a repeatable Python/PowerShell verification script are included.
The existing PostgreSQL CI service remains compatible. This branch starts from updated main
at 122d17c25ced4d244491e4fccdde21d586fe0b43; there is no unmerged setup dependency.

Validation: 87 PostgreSQL-backed/backend tests passed, including all 36 existing tests,
concurrent identical/conflicting/distinct-time requests, real job-insert rollback and
migration preservation. Docker API ingestion/retry/retrieval plus normal backend/database
restart retained exactly one reading and one pending job per demonstration asset. Liveness,
readiness, Alembic schema drift, sample schemas and Ruff checks passed. The cloud Docker
build used temporary platform proxy/CA preparation with TLS verification enabled; tracked
Docker/Compose files are unchanged. Windows telemetry checks and hosted CI were not run.

The user's previously successful Windows asset readiness/persistence checks are recorded
as user-reported results. Person B should review permanent dedup scope, explicit configuration
binding, quality/sanity mapping and the future worker's stream/watermark contract. No analytics,
alerts, simulator or WebSocket features are added. Please review without merging automatically.
