# Worker verification evidence — 9 October 2026, IST

Executed in Linux cloud on `feature/analytics-worker`, based on main `59f960432168dbe62e96ba6f107ce5ae92c323df`. Person B source is `637fbe810714d0d5c403728ddf7bcba746ea55a9`. [Structured evidence](analytics-worker-evidence.json) records executed source hashes matched to the isolated container and the exact demonstration IDs. The delivery commit identifies these source bytes; no self-referential SHA is invented here.

New executions:

| Check | Result |
|---|---|
| `python -m pytest backend/tests -q --tb=short` | **164 passed**, isolated PostgreSQL database ending `_test`, per-test migrated schemas |
| Targeted Ruff/format checks and `git diff --check` | Passed |
| `alembic -c backend/alembic.ini upgrade head --sql` | Exit0; additive SQL reviewed |
| Populated migration regression | Existing asset/configuration/telemetry/job columns unchanged; zero attempts/null leases/errors; downgrade refuses to destroy processed history |
| Isolated `alembic current` / `alembic check` | Head `d730a91b4c22`; exit0, no new upgrade operations |
| `python -m integration.verify_analytics_worker --base-url http://127.0.0.1:18002` | PASS; full registered configuration -> simulator -> readings/jobs -> worker -> stored result API |

Worker tests cover deterministic competing claims, concurrent independent computations, sequential stream updates, result uniqueness and identical submission, expired leases/abandoned work, stale-owner errors/results, commit-time expiry, rollback of all writes, retries/exhaustion/backoff, late/equal measurements, global watermark across configuration/model changes, missing/invalid/zero inputs, held-input continuity, missing oil without re-assimilation, dt1/59/60/61/137/299/300/301, result/status APIs, explicit stream filters, ground-truth exclusion, graceful shutdown and reproduced B examples. B's separate historical57/180/221-test results in the supplied handoff were **not rerun or claimed** here.

The integration creates6 primary-run readings/jobs/results and verifies6 identical resubmissions do not change any counts, stored states or advance counters. Normal worker restart preserves state/results. A seventh reading receives an intentionally abandoned2s lease and recovers on attempt2. Another run on the same asset cold-starts independently: final8 readings,8 jobs,8 results and advances[1,7]. Result latest selection, device-stream isolation and readiness pass. An initial script run using the existing no-thermal configuration correctly returned unsupported_configuration electrical results; the harness was corrected to use a separately named assumed-coefficient sample and subsequently passed. That initial demonstration data remains retained.

The normal fresh command `docker build --pull --no-cache --progress plain -f backend/Dockerfile -t powernxt-worker-clean:20261009 .` failed: Debian hostname resolution failed, apt exit100 could not locate curl; overall build exit1. This repeats the environment DNS limitation. No dependencies were bypassed or TLS disabled. The functioning isolated image used the existing backend image's installed dependencies plus current backend source, **not a successful normal dependency build**. Previous correctness-task proxy/certificate diagnosis is historical; this task's fresh build failed on DNS. A normal image build remains an outstanding check.

Unique isolated project, API port18002, database `worker_integration_test` and independently named PostgreSQL volumes keep testing away from development. Test workers were stopped/restarted normally; stacks are stopped at closure with volumes/data retained. Backend source/container byte checks and original `.env`/unrelated-document hashes passed. The development cloud containers retained their October8 start times and migration `84b8976a7d0d`; no development deployment/migration occurred.

Known Windows ce21 migration, readiness, Alembic consistency and simulator successes are **user-reported prior checks**. No worker/Windows/browser/frontend execution is claimed. [PowerShell commands](analytics-worker-windows.md) are prepared for after review/merge and include an isolated repeatable verifier.

GitHub PR/workflow access is Forbidden; no successful CI, draft creation or review is inferred. A compare link and [prepared PR description](analytics-worker-pr.md) accompany the pushed branch if API access remains blocked. No merge/auto-merge or teammate message is sent.
