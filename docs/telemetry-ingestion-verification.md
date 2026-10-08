# Telemetry ingestion verification evidence

## Repository and prior Windows results

The cloud checkout initially remained on `feature/asset-registry`. After fetching, `main`
was verified at `122d17c25ced4d244491e4fccdde21d586fe0b43`, containing the merged registry.
The cloud `feature/telemetry-ingestion` branch was created from that updated main with a clean
working tree. No AGENTS.md was found in the workspace. Existing Dockerfile, Compose ports,
CORS configuration, database volume, registry migration and tests were preserved.

**Prior Windows results, reported by the user:** Docker readiness and asset-registry
restart-persistence checks passed before this task. No additional Windows result is inferred
from that report. The agent did not access the Windows filesystem/database or execute the
new PowerShell wrapper on Windows.

## Executed cloud checks

Working directory: `/workspace/powernxt-ai-transformer-sentinel`.

- Generated and reviewed migration `84b8976a7d0d` with Alembic autogenerate. Its parent is
  registry revision `f272b723f71b`. It creates telemetry readings and processing jobs,
  composite configuration foreign keys, permanent stream/message uniqueness, one-job-per-
  reading uniqueness, source/run/schema/state-policy checks and a stream/time index.
- Applied the migration to the retained cloud development database on `localhost:5433`.
  Before/after comparison confirmed its existing **one asset and two configurations** were
  unchanged. No tables/volumes were cleared to apply the upgrade.
- Repeated `upgrade head` through the backend container succeeded. Final `current` reported
  `84b8976a7d0d (head)` and `alembic check` reported no new upgrade operations.
- **87 tests passed**: 51 new telemetry tests plus all 36 existing registry/health/CORS tests.
  None failed or skipped. PostgreSQL tests used fresh migrated schemas in `sentinel_test`;
  they did not clear development data. Existing TestClient/Alembic deprecation warnings
  remain non-fatal. The existing CI PostgreSQL service supports the new suite unchanged.
- Coverage includes valid/unknown/missing/malformed inputs, strict finite numbers, quality
  flags, implausible value preservation, live/replay/source isolation, explicit configuration
  references, history filters/pagination, permanent duplicates/conflicts, eight concurrent
  identical deliveries, concurrent conflicting deliveries and concurrent distinct event
  times. Actual PostgreSQL job-insert failure proved both reading and job roll back. Direct
  database constraints and migration downgrade/upgrade preserving registry rows were tested.
- Ruff and diff whitespace checks passed for the changed Python/code files. Sample request
  and response JSON files were validated against the actual Pydantic schemas.
- Rebuilt the Python 3.12 backend image and recreated it through the existing Compose file.
  Cloud-only proxy/CA build preparation was reused from the earlier environment setup;
  package signatures and TLS verification stayed enabled. The tracked Dockerfile/Compose
  were not modified. The trusted build used the platform CA bundle and a temporary build
  file under `/tmp`, not copied credentials.
- Ran `integration/verify_telemetry_ingestion.py` twice with unique demo assets to check
  repeatability. The final run created `demo-telemetry-31a0faf242be43f2a7cd31c54ed9f2e4`,
  reading **2**, pending job **2**. It verified POST 201, retrieval, identical retry 200 with
  the exact original result, and database counts of exactly **one reading and one job for
  that asset**. It normally restarted both database and backend, waited for readiness,
  checked unchanged persistence, and retried again with unchanged counts. Live history
  stayed empty for the simulator run. The earlier demo remains separate and was not deleted.
- Post-restart `/health/live` and `/health/ready` returned 200, with ready/connected database.
  All three telemetry endpoints appeared in OpenAPI. The pre-existing cloud registry asset
  still exposed configuration versions 1 and 2 with current version 2.

## Commands executed

From the repository root, using scoped development/test URLs configured for the operation:

```sh
# DATABASE_URL points to the retained cloud development database at localhost:5433.
.venv/bin/alembic -c backend/alembic.ini revision --autogenerate -m 'Add transactional telemetry ingestion'
.venv/bin/alembic -c backend/alembic.ini upgrade head
# TEST_DATABASE_URL points only to sentinel_test.
.venv/bin/pytest backend/tests -q

# Cloud-specific build with the existing platform proxy and trusted CA bundle.
DOCKER_CONFIG=/tmp/asset-registry-docker docker build --network host \
  --add-host proxy:172.31.4.13 \
  --build-arg HTTP_PROXY --build-arg HTTPS_PROXY --build-arg NO_PROXY \
  --build-context cloud-trust=/tmp/asset-registry-cloud-trust \
  -f /tmp/asset-registry-cloud.Dockerfile \
  -t powernxt-ai-transformer-sentinel-backend .
docker compose run --rm backend alembic -c backend/alembic.ini upgrade head
docker compose up -d --no-build backend
.venv/bin/python integration/verify_telemetry_ingestion.py
docker compose exec -T backend alembic -c backend/alembic.ini current
docker compose exec -T backend alembic -c backend/alembic.ini check
```

The temporary CA/proxy paths/address above are specific to this cloud instance and are not
Windows requirements. The integration script uses ordinary `docker compose restart db backend`;
it never removes volumes. Demonstration measurements are synthetic and configuration sources
are explicitly assumed. Every accepted job remains pending; no analytical results are claimed.

## Checks not executed and contract review

The standard Windows Docker rebuild, applying the telemetry migration to the user's existing
Windows database, and the PowerShell wrapper were not executed here. The wrapper invokes the
same Python check verified in cloud. Hosted GitHub Actions execution is also unverified.
GitHub API read access returned `Forbidden`; draft PR creation may require the prepared
compare link and description rather than API tooling.

Team review decisions: permanent stream-scoped dedup replaces the unimplemented 24-hour
baseline; callers select explicit configuration versions; per-channel quality/sanity ranges
and future worker event-time/state policies need analytics-owner confirmation. No historical
configuration effectiveness is implied. Fault ground truth is rejected from the envelope
and remains outside detector inputs. There is no processing worker yet.

See [exact Windows commands and API samples](../backend/docs/telemetry-ingestion.md).
