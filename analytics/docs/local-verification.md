# Local compatibility verification

Checked 8 October 2026 against main commit `26efab6` (transactional ingestion merge). Verification was completed locally before publication. Shared contracts and backend/deployment/frontend files were not modified; this contribution stays within `analytics/`.

## Checks

- Combined `python -m pytest backend/tests analytics/tests -q --tb=short`: **120 passed** (87 teammate backend, 16 model, 11 adapter and 6 actual API/database compatibility tests).
- Real isolated PostgreSQL `_test` database, fresh per-test schemas and A's actual Alembic migrations; no development/production data used.
- Python 3.12 with dependencies from `backend/requirements-dev.txt` in local ignored `.venv`.
- `python -m analytics.examples.demo`: eight-category fixture and three distinct action forecasts.
- `python -m analytics.evaluation.run`: normal RMSE about 0.3515 C, no normal alert openings, all four injected synthetic cases detected.

Upstream Starlette HTTPX and Alembic path-handling deprecation warnings did not fail checks. Teammate files were not changed to suppress them.

## Actual API compatibility coverage

The tests register assets/configurations, ingest real API readings and pass the resulting normalized envelope/quality flags/config to analytics. They check gradual heating, persistent overload, what-if differences, backend negative-current and suspect-temperature flags, raw-metadata exclusion, retries, equal/late timestamps, delayed jobs, stream isolation, configuration binding, omitted thermal parameters, device first-arrival freshness and historical simulation time.

## Remaining integration boundary

The adapter is verified and callable. A/D's worker, model-state/results storage, extended job lifecycle, event publication, container inclusion and C's dashboard connection are not implemented in the inspected repository. Full continuous dashboard/maintenance delivery remains team integration work. Synthetic results are consistency checks, not field calibration or standards certification.
