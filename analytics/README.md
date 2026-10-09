Review update: see [Person B code audit](../docs/person-b-code-audit.md). This branch contains model `stored-reading-top-oil-1.0.2`; adopting it in A's worker requires explicit version/state handling.

# Person B: Digital Twin and analytics

Optional follow-on APIs: `evaluate_persistent_rules`, `forecast_from_worker_state`,
and `compare_worker_scenarios`. See [sustained evidence and scenario handoff](../docs/person-b-next-analytics-handoff.md)
for explicit policies, executed examples, limits and integration ownership. These do not
change the worker schema or automatically publish alerts or expose forecast APIs.

**Recommended worker handoff:** `from analytics import process_stored_reading`.
For a direct normalized input, use `from analytics import compute_analytics`.
The current [durable worker handoff](../docs/person-b-analytics-worker-handoff.md)
records loading/cadence decisions, five computation outcomes and current-main compatibility.
See [Person A's tested integration contract](../docs/person-b-analytics-handoff.md),
[simulator review](../docs/person-b-simulator-review.md), the schemas in `analytics/schemas/`,
and `analytics/examples/worker-test-examples.json` for Person C. This conservative entrypoint
returns explicit availability and null unsupported health/confidence outputs. It uses its own
version-bound state; the earlier demonstration APIs below are preserved, not silently migrated.

For all tests, install `analytics/requirements-test.txt` (includes backend dev dependencies and
the test-only JSON Schema validator). Runtime remains standard-library-only.

Implemented against the backend at commit `26efab6` (transactional telemetry ingestion and asset registry). Runtime needs Python 3.11+ and the standard library only. No database, backend dependency or scientific library is imported by the analytics package.

## Preserved demonstration entrypoints

```python
from analytics import process_reading, process_telemetry_response, compare_what_if

# A's direct normalized-reading contract:
result = process_reading(
    reading=ingestion_result["normalized_telemetry"],
    quality_flags=ingestion_result["quality_flags"],
    asset_config=bound_configuration_response,
    previous_state=saved_state,
)

# Earlier demonstration adapter: honors state_policy and live arrival freshness.
result = process_telemetry_response(ingestion_result, bound_configuration_response, saved_state)
# A persists result + result["updated_state"] atomically under a per-stream lock.

comparison = compare_what_if(result["updated_state"], scenarios)
```

The adapter returns the eight categories in the proposed shared analytics contract. It uses channel-level `measurement_quality` and ingestion reason lists, the explicitly bound immutable configuration version, and state per `(asset_id, source, run_id)`. It never reads `original_payload`, scenario labels or arbitrary raw metadata. Historical-only and non-advancing jobs return unchanged state.

Missing thermal parameters are unavailable, not replaced with demo values. The existing team's sample configuration has no thermal parameters, so it gives useful electrical metrics but null thermal estimates. Action comparisons require explicit thermal coefficients and a usable measured initial temperature.

Sequence components, power factor, kW/kvar, winding hot-spot, insulation aging and remaining useful life stay null because the supplied channels/implemented model cannot establish them. Magnitude imbalance is labeled separately from negative-sequence unbalance. The top-oil model is simplified and is not certified IEEE C57.91 compliance. See [contract review](docs/contract-review.md) and [backend integration](docs/backend-integration.md).

## Local execution

From the repository root:

```sh
python -m unittest discover -s analytics/tests -p 'test_twin.py' -v
python -m unittest discover -s analytics/tests -p 'test_adapter.py' -v
python -m analytics.examples.demo
python -m analytics.evaluation.run
```

The demo writes `analytics/examples/analytics_response.json` with normalized readings, a bound assumed configuration, eight-category analytics and three what-if scenarios. The evaluation writes `analytics/evaluation/results.json`. Both use synthetic data and are explicitly labeled; neither claims field accuracy.

With A's declared backend development dependencies installed and an isolated PostgreSQL database ending in `_test`:

```sh
# macOS/Linux shell
TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/sentinel_test \
  python -m pytest backend/tests analytics/tests -q
```

```powershell
# Windows PowerShell, from repository root
$env:TEST_DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@localhost:5432/sentinel_test"
.\.venv\Scripts\python.exe -m pytest backend/tests analytics/tests -q
```

Database tests reuse A's isolated-schema fixture and migrations. [Local verification](docs/local-verification.md) records the checked baseline and results. Shared pytest configuration/CI currently discovers only backend tests unless `analytics/tests` is supplied explicitly; D should add analytics to CI when this local work is reviewed.

## Ownership and current integration boundary

Reusable model functions are exported from `analytics` and implemented in `analytics/transformer_twin/`. A owns worker scheduling, locking, state/results storage, job completion and transport; C renders output and scenario controls; D owns domain-event publication, acknowledgements and maintenance tasks. This component does not change A's pending-job schema or fabricate completed jobs.

The existing Dockerfile copies only `backend/`, so A/D must include `analytics/` when wiring their worker into the container. This contribution changes only Person B's `analytics/` files and the two `docs/person-b-*` handoff documents; shared contracts, backend, deployment and frontend files are unchanged.
