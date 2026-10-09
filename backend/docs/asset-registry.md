# Transformer asset registry

The registry stores transformer identities independently from immutable configurations.
It adds no telemetry, analytics, simulation, or dashboard behaviour. OpenAPI schemas are
available at `/openapi.json` and interactive documentation at `/docs`.

## API for Person C

| Method | Path | Success |
|---|---|---|
| POST | `/api/v1/assets` | 201, asset with `current_configuration: null` |
| GET | `/api/v1/assets?limit=20&offset=0` | 200, `{items, limit, offset}` |
| GET | `/api/v1/assets/{asset_id}` | 200, asset including latest configuration |
| POST | `/api/v1/assets/{asset_id}/configurations` | 201, allocated configuration version |
| GET | `/api/v1/assets/{asset_id}/configurations?limit=20&offset=0` | 200, `{items, limit, offset}` history |

Duplicate identifiers return 409. Unknown assets return 404, including history or
configuration creation. Invalid bodies/pagination return 422. Database conflicts return
409 and database failures 503 with sanitized messages. There are no update/delete routes.
These development endpoints follow the backend's existing unauthenticated API policy.

`asset_id` is a stable, case-sensitive ASCII identifier (letters, digits, dots, underscores,
hyphens; first character alphanumeric; maximum 100 characters). Name and location must
be nonempty. `timezone` is an IANA zone such as `Asia/Kolkata` or `UTC`.
All `created_at` responses are timezone-aware UTC ISO-8601 timestamps.

Listing defaults to 20, is bounded to 1–100 items, and uses nonnegative offsets.
Assets sort by `asset_id` ascending; history sorts by version ascending. Fetch further
history pages until `items` is empty. A current configuration is null until the first
configuration is created. Offset pagination is deterministic for unchanged data; concurrent
asset inserts can shift pages. History is append-only, so previous versions remain accessible.

Example asset request:

```json
{"asset_id":"demo-transformer-001","name":"DEMONSTRATION - assumed transformer","location":"Demo lab","timezone":"Asia/Kolkata"}
```

Example creation response (timestamps are illustrative):

```json
{"asset_id":"demo-transformer-001","name":"DEMONSTRATION - assumed transformer","location":"Demo lab","timezone":"Asia/Kolkata","created_at":"2026-10-07T12:00:00Z","current_configuration":null}
```

Use `data/sample/asset-configuration-assumed.json` as the complete configuration POST body.
A configuration response has the same fields plus `asset_id`, `version`, and `created_at`.
Optional unspecified nested fields serialize as null. For example, the sample's
`thermal_parameters` response is:

```json
{"rated_top_oil_rise_c":null,"rated_hot_spot_rise_c":null,"oil_time_constant_min":null,"winding_time_constant_min":null,"loss_ratio":null,"oil_exponent":null,"winding_exponent":null}
```

A retrieve response embeds that full configuration in `current_configuration`; history
returns the full version objects in `items`.

## Configuration units and meaning

| Field | Meaning |
|---|---|
| `rated_kva` | Positive finite total three-phase apparent-power rating, kVA |
| `rated_voltage_v` | Positive finite RMS voltage, volts, on `measurement_side` |
| `rated_current_a` | Positive finite RMS line current, amperes, on `measurement_side` |
| `voltage_convention` | `phase_to_neutral` or `line_to_line` for rated voltage |
| `measurement_side` | `primary` or `secondary`; applies to both voltage and current |
| `cooling_type` | Nonempty nameplate cooling class, e.g. `ONAN` |
| `operational_limits.max_load_pct` | Positive load percentage of rated capacity |
| `operational_limits.min_voltage_pu`, `max_voltage_pu` | Positive per-unit bounds relative to rated voltage, with min < max when both supplied |
| `operational_limits.max_top_oil_temp_c`, `max_hot_spot_temp_c` | Finite Celsius limits above absolute zero; oil limit ≤ hot-spot limit when both supplied |
| `thermal_parameters.rated_top_oil_rise_c` | Positive top-oil rise over ambient at rated load, Celsius |
| `thermal_parameters.rated_hot_spot_rise_c` | Positive hot-spot rise **over top oil** at rated load, Celsius |
| `thermal_parameters.oil_time_constant_min`, `winding_time_constant_min` | Positive time constants, minutes |
| `thermal_parameters.loss_ratio` | Positive ratio of rated load losses to no-load losses |
| `thermal_parameters.oil_exponent`, `winding_exponent` | Positive dimensionless model exponents |

Operational and thermal fields are optional; missing values are not invented. All supplied
numbers must be finite. Unknown fields are rejected. Ratings are not inferred from sample
sensor readings; no physical consistency calculation is performed between capacity, voltage,
and current because topology and nameplate tolerances are not yet contracted.

`parameter_provenance` must include exactly one entry for every supplied parameter:
`assumed`, `simulated`, `nameplate`, or `measured`. Nested keys use dotted paths, e.g.
`thermal_parameters.oil_time_constant_min`. Convention, side, and cooling class also have
sources. Metadata (`asset_id`, `version`, timestamps) are server-managed and have no source
entry. Unknown parameters have no source entry. The sample is entirely **assumed**, not a
measurement or an equipment recommendation; it deliberately leaves all thermal values unknown.

Each POST allocates a positive per-asset version. PostgreSQL locks the parent asset row until
commit, then queries the latest version using a fresh READ COMMITTED snapshot. A unique
`(asset_id, version)` constraint independently guards against duplicates. Different assets
can be configured concurrently. Retrying a successful POST creates another version: there
is no idempotency-key contract. Configurations are immutable through the API.

## Proposed decisions for Person B

The existing analytics contract specifies an `asset_config` dictionary but does not define
its input keys. The registry uses `rated_kva`; a future adapter can supply rated MVA via
`rated_kva / 1000` if required. Person B should confirm these field names, three-phase
capacity convention, RMS voltage/line-current convention, thermal-rise reference, minute
units, loss-ratio definition, and exponent meaning. Impedance remains unmodelled because no
units or base convention are agreed. The analytics contract remains unchanged and proposed.

## Migration and tests

Run commands from the repository root. Existing Compose ports remain host 5433 and container
`db:5432`. Do not remove volumes or clear the development database. Upgrade creates tables;
it does not seed data or modify existing application records. Downgrade drops registry tables
and their contents, so use it only in disposable test schemas.

```powershell
Set-Location 'C:\Users\marka\.gemini\antigravity\scratch\powernxt-ai-transformer-sentinel'
git switch feature/asset-registry
docker compose up -d db
docker compose build backend
docker compose run --rm backend alembic -c backend/alembic.ini upgrade head
docker compose up -d backend
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
& .\integration\verify-asset-registry.ps1
```

The verification script waits for readiness, uses a unique demonstration ID, creates versions
1 and 2, checks history, normally restarts both services, and verifies persistence without
removing volumes. If PowerShell execution policy blocks the script, run its contents in your
interactive session under your organization's policy.

For local Alembic outside Docker, activate the Python virtual environment and set
`DATABASE_URL` securely to a PostgreSQL psycopg URL using `localhost:5433`. Then run
`python -m alembic -c backend/alembic.ini upgrade head` from the root. Local Python settings
require `CORS_ORIGINS` to be a JSON array, e.g.
`$env:CORS_ORIGINS = '["http://localhost:3000","http://localhost:5173"]'`.
Do not echo credentials.
Compose injects its own container URL, so no host URL override is needed for container commands.

Tests require an explicit PostgreSQL `TEST_DATABASE_URL` whose database name ends in `_test`.
Each test migrates a unique schema and drops only that schema afterwards. The development
schema is never cleared. CI provides PostgreSQL 16 and runs all backend tests, including
concurrent configuration creation and migration downgrade/upgrade in a disposable schema.

Example for the repository's **default local development credentials only** (use your
securely configured test URL instead if credentials differ):

```powershell
docker compose exec -T db createdb -U sentinel sentinel_test  # once; skip if already present
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
$env:CORS_ORIGINS = '["http://localhost:3000","http://localhost:5173"]'
$env:TEST_DATABASE_URL = 'postgresql+psycopg://sentinel:sentinel_dev_pw@localhost:5433/sentinel_test'
python -m pytest backend/tests -v
Remove-Item Env:TEST_DATABASE_URL
```

See `docs/asset-registry-verification.md` for actual cloud validation and limitations.
