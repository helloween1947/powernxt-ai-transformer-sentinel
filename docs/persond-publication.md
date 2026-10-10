# Person D publication and dashboard integration

**Current integration status:** see [persond-integration-readiness.md](persond-integration-readiness.md).
The sections below describe the earlier publication snapshot; UI files were
subsequently moved to a focused D-owned follow-up and audit PR8 has merged.

Repository: `C:\Users\hrami\OneDrive\Documents\ChatGPT\final powernext\powernxt-ai-transformer-sentinel`
(Windows, not WSL). The separate Downloads project is unrelated and was untouched.
The earlier implementation was located intact and reverified before publication.
Original documents record the pre-publication snapshot; this file records the
authorized publishing/integration continuation on 9 October 2026.

## Reviewed branches and PRs

Main is the integration base required by CONTRIBUTING. A/B/audit PRs target main.
C's base dashboard PR1 targets main; its follow-up PR5 targets feat/frontend-setup.
There was no existing persond PR at initial inspection.

| Branch | Reviewed SHA |
| --- | --- |
| main | f35d268cda49d81fac7463d8a5082cb5b1c1bc98 |
| feature/normal-operation-simulator | 55a9c54f44f9f7dc6cdc437438bce9fcc11c1bba |
| feature/personb-twin-analytics | 35a8c64b5a2b5eaf37b84e6cd1308a7a3576fe28 |
| feat/frontend-api-integration | a55478654d5cb945ccf4d7134add131314e5a7cd |
| audit/correctness-fixes | 429fbc761b89731738027656882fd164173d76d3 |

A's simulator is now merged. B adds a deterministic stored-reading worker and
schemas, but not database-backed analytics/alert persistence. The new worker
emits configured-limit checks without incident lifecycle IDs; the older adapter
still emits incident observations. These contracts must not be conflated or
labeled genuine persisted alerts. C's current maintenance screen is still
browser-local; it has not connected the versioned maintenance API.

Pending audit PR8 introduces ce21c3b8140a with parent 84b8976a7d0d, a sibling of
D001. Merging audit and D without reconciliation would produce two Alembic heads.
Once both are present, A/D must add a merge revision with parents ce21c3b8140a
and d002_task_workflow before using `upgrade head`. Do not rewrite applied
D001/D002. This is an unmerged integration dependency, not a main migration bug.

## Backend verification and publishing

125 backend tests and six mapper/client tests passed using Windows Python3.13
and the preserved isolated PostgreSQL18 cluster on loopback port55432. Tests
include original task persistence and atomic history/versioning. Docker reports
the Linux-engine named pipe is missing. No volumes were removed or working tools
reinstalled. Native PostgreSQL remains the verification path.

Publishing completed to origin/persond with draft PR9 against main. The PR
remains unmerged pending A/C review of prototype identity, sample alert contracts
and integration dependencies. Only intended source, migrations, tests, fixtures,
mapper and docs are staged; credentials, environments, databases and review
checkouts are excluded.

## Published work and dashboard review

Backend commit `94d3656` was pushed normally to `origin/persond`.
Draft PR [#9](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/9)
targets `main`; it has not been merged. The subsequent UI commit adds these
reviewable files without copying C's dashboard implementation:

- `frontend/src/components/BackendMaintenance.jsx`: registered asset selection,
  paginated tasks/history, sample task creation, assignment and status/notes edits.
- `integration/frontend/maintenanceClient.mjs` and its tests: real HTTP calls,
  mapper reuse, versions, pagination and visible failures.
- `integration/frontend/dashboard-integration.patch`: a small mounting patch
  against C's reviewed App.jsx, preserving its existing screens.
- `integration/frontend/verifyDashboardBrowser.cjs`: actual browser verification.

PATCH sends the saved `expected_version` and caller-entered `X-Demo-Actor`.
On 409, the UI fetches the latest task, preserves the operator's draft, displays
both and blocks saving until explicit review. It never automatically retries.
Completed/cancelled tasks are read-only. No browser-local fixture fallback is
used for this screen. Sample alerts and untrusted demo identity remain clearly
labelled; genuine alert provenance and production authentication are unfinished.

The mount patch was applied only in an isolated combined checkout containing
latest main, D and C's tracked frontend. Person D alone does not contain C's
App/package setup, so this is a tested integration proposal, not a merged or
deployable dashboard. Review the patch after C's frontend is available.

## Checks actually completed

| Check | Result |
| --- | --- |
| Person D backend against native PostgreSQL | 125 passed |
| Latest main + D backend + current B analytics in isolated checkout | 227 passed |
| Audit + D backend with local preview-only merge migration | 166 passed |
| D mapper and HTTP client Node tests | 6 passed |
| C telemetry adapter Node tests | 6 passed |
| Combined C+D frontend lint and production build | Passed |
| Original persistence and workflow HTTP verifiers | Passed |
| Actual installed Chrome, headless, Playwright workflow | Passed |
| Browser with backend stopped | Visible API failure; create disabled; passed |
| Browser after backend restart | Persisted completed task/history; passed |

The browser created a PostgreSQL task, assigned an owner, started it, verified
completion without notes was rejected, completed with notes, displayed four
history records and verified persistence after refresh. A competing API update
then exercised 409: the draft survived, retry required explicit review and the
competing server note was preserved until that review. Restart verification
retrieved completed task `fc1e3620-a86b-4ce4-a55e-fe002d95d9bc` at version 4.
These are real browser checks, separate from HTTP-only tests. Production
containers, genuine alerts and authenticated operators were not tested.

The audit test used a no-op merge revision with parents `ce21c3b8140a` and
`d002_task_workflow` in a separate checkout only. That revision is NOT in PR9.
A reviewed permanent merge revision is still needed if both branches land.

The browser harness requires Playwright as a development dependency and an
installed browser. This run installed it under ignored `.venv/browser-check`,
used `NODE_PATH` pointing to its node_modules and `MAINTENANCE_BROWSER_PATH`
pointing to installed Chrome. It ran workflow, offline and saved modes against
the combined Vite dashboard and native PostgreSQL backend. Database state and
logs remain in ignored local directories; none are committed.

## Merge order and next milestone

1. Main already contains A's simulator. Review/land C's base dashboard PR1,
   then incorporate its API follow-up PR5 (currently targeting C's setup branch).
2. Review/land D's PR9 with D001 then D002 migrations. Review the small App mount
   patch against the resulting C frontend and apply it as an integration change.
   Set VITE_API_BASE_URL to the reachable backend and register the sample asset
   using the documented fixture; runtime requires both backend and frontend.
3. If audit PR8 also lands, add the reviewed Alembic merge revision for the two
   heads before `upgrade head`. Do not rewrite applied migration history.
4. Repeat the browser workflow on the final merged revision. Docker deployment
   remains blocked by the missing Linux-engine pipe; no volumes were deleted.

Exact team questions: A/D, who owns the permanent merge revision when audit and
D land? B, what persistent alert ID, asset association and provenance contract
will the backend expose? C, can you review the mount patch after your frontend
PRs land and confirm API base URL/CORS settings? Do not substitute B's raw limit
observations for persistent incident identities. Genuine-alert integration is a
later milestone after that contract exists. Acknowledgement, incident summaries
and unrelated recommendations were not added.

## Ready-to-send teammate message (not sent)

Person D's work is pushed to persond in draft PR9 against main, not merged.
Tasks/history are PostgreSQL-backed, versioned and currently use labelled sample
alerts and X-Demo-Actor prototype identity. The new component/client and small
C App mounting patch were tested in an isolated combined checkout: create,
assign, start, completion notes, history, refresh/restart persistence and 409
operator review passed in actual Chrome. Person D alone is not a deployable
combined dashboard. C: please review the component/mount patch after your
frontend PRs land. A: review API/CORS and migrations; audit+D will need a merge
revision for ce21c3b8140a and d002_task_workflow. B: confirm the persistent alert
identity/provenance contract before genuine-alert integration. Backend tests
passed (D 125; latest main+D+B 227); frontend lint/build and mapper/client tests
passed. Docker deployment is still blocked by the missing engine pipe.

## 11 October 2026 combined application follow-up

The earlier publication notes above are historical. Current integrated source,
backend/frontend ancestry, genuine persisted incident/task Chrome execution,
migration/record comparisons, startup commands and review ownership are in
[the dated combined application report](app-integration-20261011.md),
[evidence manifest](app-integration-evidence-20261011.json) and
[isolated startup guide](app-review-startup.md). The new D draft is stacked on
A's unmerged backend candidate; no main merge, development migration or Docker
deployment is implied. C's rebuilt workspace remains the frontend authority.
