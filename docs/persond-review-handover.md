# Person D review and coordination handover

This records the original milestone review. For the latest branch fetch,
WSL/Docker checks, assignment/status/history implementation, current test results
and ready-to-send message, use `docs/persond-maintenance-workflow.md`.

Inspected on 8 October 2026. Scope: current early implementation, not completion
of the team's roadmap. Instructions read: root README and CONTRIBUTING; no
AGENTS.md was found in the repository or checked workspace ancestors.

## Branch evidence

Remote branches were fetched before review. Ownership follows commit authors,
changed files and explicit role descriptions, rather than the old person labels.
A's foundation/registry/ingestion commits are by Markab Debbarma; C's frontend
commits are by akash-patil18. Their responsibilities match the supplied roles.

| Branch | Full inspected tip | Role / evidence |
| --- | --- | --- |
| `chore/team-repository-setup` | `2619044900e0e0fd1ec76d151559d1ecf868342a` | A: backend foundation; merged into main |
| `feature/asset-registry` | `b9d1c5d6722887f40941490ddb69207568f911c0` | A: versioned registry; merged into main |
| `feature/telemetry-ingestion` | `db17a8d8a6f079353bb9795c1eba193d9978e7d3` | A: ingestion/history; merged into main |
| `feat/frontend-setup` | `cc7678c65ce91db526d1f1b93feb70d4319e0aa4` | C: original fixture dashboard |
| `feat/frontend-api-integration` | `a55478654d5cb945ccf4d7134add131314e5a7cd` | C: latest frontend implementation inspected/tested |
| `main` | `26efab6259524686199ef6a64ca66b541c7eda78` | Shared base including A's merged steps |
| `personc` | `c9e3f0d8a4dafea954a1617baea8455f992bf509` | Old initial repository; does not contain C's dashboard |
| `persond` (remote) | `c9e3f0d8a4dafea954a1617baea8455f992bf509` | Existing D branch before this work |

C was checked in a detached local worktree at `../personc-review`; no C branch
was modified. Local persond was fast-forwarded to shared main before adding the
maintenance milestone. No feature branches were merged for inspection.

## What A currently has

- FastAPI app, settings, structured logging, CORS, liveness/readiness probes.
- SQLAlchemy sessions, PostgreSQL, Alembic migrations and PostgreSQL-backed tests.
- Asset create/list/detail and append-only versioned nameplate configurations.
- Transactional telemetry ingestion, original/normalized payloads, quality flags,
  configuration references, retry/conflict handling and out-of-order policy.
- Latest/history reads isolated by asset, source and simulation/replay run ID.
- A persisted pending processing job with each new reading; this is not completed
  analytics. CI has a PostgreSQL service for the backend test suite.
- Written telemetry, analytics and event contracts; sample data labeled as samples.

## What C currently has

- React/Vite dashboard with fleet, transformer, alert, what-if and maintenance
  screens using illustrative fixtures.
- Browser-local maintenance create/status/notes flow in localStorage; sample
  acknowledgement changes reset when fixture data reloads.
- A separate Backend readings screen with versioned asset/telemetry request
  helpers, pagination, stream selection, timestamp/configuration provenance,
  missing values, quality flags, pending status and request errors.
- Six adapter tests; latest frontend lint and build both pass locally.

## Actual issues versus future work

No incorrect backend or frontend implementation was reproduced by the checks
run here. This is bounded evidence, not a claim that all behavior is correct.

One confirmed documentation discrepancy: the root README still calls the asset
registry and telemetry tables upcoming, although their code/migrations are in
main. C's dashboard is on its feature branch, while main has only its placeholder
README. Use the branch evidence above rather than assuming main has every screen.
These shared documentation changes are left for the owners to coordinate.

Environment issue: the initially resolved psycopg 3.3.6 binary was blocked by
Windows Application Control. The allowed 3.2.13 version works in this virtual
environment. Docker Desktop cannot start; WSL is not installed. Tests used an
isolated PostgreSQL 18 cluster under `.venv`, not the existing service.

Deprecation warnings from the newly resolved Starlette TestClient and Alembic
configuration are non-failing tooling warnings. They are not absent product
features or failed tests.

Still upcoming: simulator/workers, completed analytics, real alert registry,
live event delivery/recovery, genuine what-if results and end-to-end integration.
C's main fixture screen live-mode URLs/schema are provisional and do not yet
match all backend routes. Its separate Backend readings helpers do match the
documented current asset/telemetry routes. Backend maintenance integration,
acknowledgement and task updates remain future work, not bugs in this first step.
No live C-browser-to-backend connection or complete application was verified.

## D milestone and changed files

Implemented: labeled sample alert -> task creation -> task retrieval/listing ->
PostgreSQL persistence across backend restart. Identical retries reuse one task;
changed content for the same identity conflicts. Registered assets are required.
Caller-provided actions are not model-generated recommendations.

| File | Purpose |
| --- | --- |
| `backend/app/api/__init__.py` | Register maintenance router |
| `backend/app/api/maintenance.py` | Versioned create/list/detail API and error masking |
| `backend/app/models/__init__.py` | Register model with Alembic metadata |
| `backend/app/models/maintenance.py` | Task table, asset FK and unique sample identity |
| `backend/app/schemas/maintenance.py` | Strict request/response and sample provenance |
| `backend/app/services/maintenance.py` | Asset validation, atomic creation and retry handling |
| `backend/migrations/versions/20261008_d001_add_sample_maintenance_tasks.py` | Migration after A's telemetry revision |
| `backend/tests/test_maintenance.py` | 15 PostgreSQL-backed maintenance tests |
| `integration/fixtures/sample-maintenance-task.json` | Clearly labeled request fixture |
| `integration/verify_maintenance.py` | Live HTTP creation/retrieval and restart checker |
| `docs/persond-first-milestone.md` | Contract, exact Windows run/verify/upload instructions |
| `docs/persond-review-handover.md` | This evidence and coordination message |

D owns maintenance behavior. The small backend additions follow A's structure
because a shared backend/database already exists. A should review registration
and migration integration; existing services/contracts are otherwise unchanged.

## Checks actually run

| Check | Result |
| --- | --- |
| Git/filesystem/Python/Node availability and repository clone/fetch | Passed |
| Backend health tests before database verification | 5 passed |
| Full backend suite with PostgreSQL 18 and migrations | 102 passed: 87 existing + 15 maintenance |
| New tests: validation, unknown asset/task, retry/conflict, paging/filtering, concurrent retries, database error masking | Passed |
| New persistence test: fresh app/engine in two separate Python processes | Passed |
| Live Alembic upgrade on isolated demo DB | Passed through `d001_maintenance` |
| Live HTTP create/retry, retrieve and asset-filtered list | Passed |
| Actual Uvicorn process stopped/restarted; same task retrieved over HTTP | Passed; ID `f892495a-0da1-42b0-95b9-bac16c192035` |
| C: `npm ci`, `npm run lint`, `npm run build` | Passed in detached review checkout |
| C: `node --test tests/telemetryAdapter.test.js` | 6 passed |
| `git diff --check` | Passed |

The backend suite used Python 3.13.14, psycopg 3.2.13, SQLAlchemy 2.1.4 and
PostgreSQL 18. C's checks used Node 24.19.0 and npm 11.17.0. Dependencies were
installed from existing requirements/lockfile; no new production dependency
specification was introduced. Docker/Compose deployment, PostgreSQL 16 CI,
migration downgrade, browser integration and finished analytics were not tested.

## Limits and next milestone

Only sample alerts and open tasks are supported. No genuine alert foreign key
exists until A/B supply a trusted alert store. No task updates, assignee, notes,
acknowledgement, history/audit, incident summaries or deployment automation were
implemented. No auth workflow was added to the early backend.

Next milestone: agree genuine alert identity/provenance and a maintenance update
contract, then add one task status transition with an append-only history record
and connect C's screen. Keep acknowledgement semantics distinct from task status.

Specific decisions for A/B/C:

- A: confirm table/migration and route registration; choose the trusted persisted
  alert identity and an asset relationship the maintenance service can validate.
- B: define actual alert output and recommendation evidence/provenance; decide
  how real-device and simulation/run identities will be retained.
- C: agree snake_case versus adapter mapping, `items` pagination and lowercase
  status; keep sample tasks labeled. Assignments and PATCH are a later contract.

## Ready-to-send teammate message

> My branch is `persond`. I completed the first maintenance milestone locally:
> a clearly labeled sample alert creates a PostgreSQL-backed task, which can be
> retrieved/listed and survives backend restart. This extends A's existing
> FastAPI/SQLAlchemy/Alembic backend and does not require B's completed analytics.
>
> Available APIs: POST/GET `/api/v1/maintenance/tasks` and GET
> `/api/v1/maintenance/tasks/{task_id}`. The list returns `{items, limit, offset}`
> and supports `asset_id`. POST takes `{alert: {source: "sample", alert_id,
> asset_id, summary}, action}`; the response includes `id`, `asset_id`, `alert`,
> `action`, `status: "open"` and `created_at`. Use
> `integration/fixtures/sample-maintenance-task.json` and
> `integration/verify_maintenance.py`. Apply Alembic migration `d001_maintenance`.
>
> A: please review route/model registration and the migration, and agree a
> trusted alert store/identity. B: please agree genuine alert provenance and
> recommendation evidence, including simulation/run identity. C: please agree
> field/status mapping and list pagination; the current browser task format
> needs an adapter. Updates/assignment/notes are not in this milestone.
>
> Verification: 102 backend tests passed (15 new maintenance tests), and a live
> HTTP create/retry/retrieve/list check plus actual backend restart passed.
> C's current branch also passed lint/build and six adapter tests in isolation.
> Full browser integration and deployment remain untested. Genuine alerts,
> acknowledgement, task updates/history/audit and incident summaries are pending.
>
> Changes are local, uncommitted and unpushed. My local persond was fast-forwarded
> to shared main before the work. No A/C feature branches were merged or changed,
> and this message has not been sent.
