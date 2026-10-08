# Person B: Digital Twin and analytics

Implemented against the backend at commit `26efab6` (transactional telemetry ingestion and asset registry). Runtime needs Python 3.11+ and the standard library only. No database, backend dependency or scientific library is imported by the analytics package.

## Team entrypoints

```python
from analytics import process_reading, process_telemetry_response, compare_what_if

# A's direct normalized-reading contract:
result = process_reading(
    reading=ingestion_result["normalized_telemetry"],
    quality_flags=ingestion_result["quality_flags"],
    asset_config=bound_configuration_response,
    previous_state=saved_state,
)

# Preferred queued-job adapter: also honors state_policy and live arrival freshness.
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

The existing Dockerfile copies only `backend/`, so A/D must include `analytics/` when wiring their worker into the container. No shared contract, backend, deployment or frontend file was changed by this contribution; all repository changes are local within Person B's `analytics/` directory.
