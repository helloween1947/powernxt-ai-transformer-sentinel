# Asset registry implementation and validation

## Branch dependency

Default branch: `main`, inspected at `c9e3f0d8a4dafea954a1617baea8455f992bf509`.
`chore/team-repository-setup` was **not merged** into it. `feature/asset-registry`
was created from setup commit `2619044900e0e0fd1ec76d151559d1ecf868342a`.
The registry depends on that backend foundation. Merge neither branch automatically;
review the setup dependency before merging the registry PR into main.

## Executed checks in the cloud workspace

Working directory: `/workspace/powernxt-ai-transformer-sentinel`.

- Python 3.12 virtual environment installed `backend/requirements-dev.txt` and timezone data.
- PostgreSQL 16 Compose service created a fresh cloud development database. There were no
  pre-existing containers or volumes here; the Windows database was not accessible.
- Generated and reviewed migration `f272b723f71b` locally with Alembic autogenerate. It creates
  assets and configurations, a restrictive foreign key, positive/finite rating checks,
  supported convention/side checks, and unique per-asset versions. Primary-key and unique
  indexes support identity lookup and per-asset version/history queries.
- Applied migration to the cloud development database without clearing data. Repeated
  `upgrade head` inside Compose succeeded. `current` reported `f272b723f71b (head)`;
  `alembic check` reported no new upgrade operations.
- **36 tests passed** (31 registry tests and all 5 existing health/CORS tests), with no
  failures/skips. Each registry test migrated its own schema in `sentinel_test`. Tests
  covered eight simultaneous API writes producing distinct versions 1–8, preservation
  of each configuration, database uniqueness/rating/version constraints, bounded listing
  and history, validation, sanitized failures, and upgrade/downgrade preserving an
  unrelated record. Deprecation warnings from TestClient and Alembic remain non-fatal.
- Ruff passed for new registry, test, migration, and verification Python files; diff
  whitespace review passed.
- Built the Python 3.12 backend image and ran it with the existing Compose settings.
- Executed `python integration/verify_asset_registry.py` against the running Docker API.
  It created asset `demo-registry-b21a05ebb0d64c6e81e62ead54794dea`, posted assumed versions
  1 and 2, retrieved version 1, restarted `db` and `backend` normally, waited for readiness,
  and verified both versions and the latest configuration persisted unchanged.
- `/health/live` and `/health/ready` returned 200 after restart; readiness reported
  `database=connected`. OpenAPI includes all five registry operations.

Migration and runtime commands actually executed from the root:

```sh
# DATABASE_URL was scoped to the command and pointed to localhost:5433.
.venv/bin/alembic -c backend/alembic.ini revision --autogenerate -m 'Add transformer asset registry'
.venv/bin/alembic -c backend/alembic.ini upgrade head
# TEST_DATABASE_URL was scoped to the command and pointed to sentinel_test.
.venv/bin/pytest backend/tests -q
docker compose run --rm backend alembic -c backend/alembic.ini upgrade head
docker compose up -d backend
.venv/bin/python integration/verify_asset_registry.py
docker compose exec -T backend alembic -c backend/alembic.ini current
docker compose exec -T backend alembic -c backend/alembic.ini check
```

## Cloud build adjustments and unrun checks

The standard Docker build was blocked here by a read-only Docker cache, BuildKit proxy
DNS resolution, and the base image missing the platform's TLS interception trust root.
A temporary, untracked cloud Dockerfile was derived from `backend/Dockerfile`, adding the
platform-provided CA bundle and `PIP_CERT`/`SSL_CERT_FILE`. BuildKit used host networking,
a host mapping for the provided proxy, and the existing proxy environment variables.
TLS certificate and package-signature verification remained enabled. The repository's
Dockerfile and Compose configuration were unchanged.

The validated image was built with:

```sh
DOCKER_CONFIG=/tmp/asset-registry-docker docker build --network host \
  --add-host proxy:172.31.4.13 \
  --build-arg HTTP_PROXY --build-arg HTTPS_PROXY --build-arg NO_PROXY \
  --build-context cloud-trust=/tmp/asset-registry-cloud-trust \
  -f /tmp/asset-registry-cloud.Dockerfile \
  -t powernxt-ai-transformer-sentinel-backend .
```

Those temporary paths and the proxy address belong to this cloud instance; they are not
Windows configuration requirements. The standard build on Windows, the PowerShell wrapper,
and migration against the user's existing Windows database were **not executed** here.
The wrapper invokes the same standard-library Python verification script tested in cloud.
Hosted GitHub Actions execution is unverified; its PostgreSQL service is configured.
GitHub API access returned `Forbidden`, so draft PR creation may require using the compare
link manually. No branch was merged, no database volume removed, and no `.env` committed.

See [API fields, sample requests/responses, and exact Windows commands](../backend/docs/asset-registry.md).
