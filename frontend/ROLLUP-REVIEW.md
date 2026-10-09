# Frontend roll-up and PR16 publication review

## Current state after authorized retarget

PR18 has merged. Main `7b19626` contains both `ff6918d` and `f0b3572` by
ancestry. PR16 now targets main; C merged this main into its branch without
conflicts at `de5fed97`. The resulting net diff is 16 analytics UI/client/test
and supporting documentation files, with no backend, analytics-model,
integration, CI, environment or maintenance-mount diff.

34 frontend tests, lint/build, 222 backend tests in the separate test database,
and actual Chrome/current-main API checks passed. The browser used temporary
ports 3001/8001 and a separate copied demo database upgraded to D004; existing
environment files, original database/servers and Date.now()) were preserved.
See ../docs/person-c-analytics-integration-verification.md for current evidence.
The remaining gates are current-head CI and human review/approval before merge.
What-if stays illustrative and phone testing remains deferred.

Everything below records the earlier pre-merge inspection, not current status.

Inspected9 October2026; no GitHub mutation performed.

## Exact references and ancestry

- main:090d5ee5fdb85ab1c59368cc05c1d009d4469f19
- frontend API branch:ff6918d300b79a83023f2b10e937f45e2f034b9f
- PR18 head:fdec6e3a03e7623d2fb836d33b366ec53b997efa
- PR16 published head:82e36e03791aa02e815ccd711b036706e24e0ccf
- PR16 actual source:codex/personc-analytics-comparison
- PR16 actual base:codex/personc-maintenance-integration atf0b3572

PR5/PR12 landed in their stack branches; neither head is in main yet. Relative
to main, frontend API has11 unique commits and main has14 unique commits. The
API branch contains PR5/PR12 and its full history. The read-only merge-tree
assessment against current main is conflict-free. No actual branch merge made.

## Equivalent roll-up already exists

[Draft PR18](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/18),
codex/persond-combined-verification → main, includes ff6918d as an ancestor.
It is mergeable and its exact-head Backend Test Suite(Python3.12) passed.
No duplicate PR or extra roll-up branch should be created.

Its diff is27 files, +2497/−33: the23-file C frontend roll-up below, plus D's
integration verification document, integration README, independent persistence
verifier and labelled seeder. C's MAINTENANCE-INTEGRATION.md gains a current
verification preface; all other frontend files exactly match the API branch.
Backend files exactly match main: no backend implementation/schema diff.
D's superseded PR10 frontend mount is not included. D's claimed combined
backend/browser results are reported PR evidence, not newly rerun here.

Review finding: two historical Unicode labels in PR18's maintenance document
have mojibake (limit1–100 and the review-snapshot dash). Correct those as a
small documentation change with appropriate authorization; no D branch edited.

## Exact standalone C roll-up diff

Git three-dot main...feat/frontend-api-integration: **23 frontend files,
2176 additions,33 deletions**. Full reviewed patch retained locally outside Git
at integration-work/frontend-rollup.patch. No analytics comparison/PR16 code
is bundled into this prerequisite roll-up.

| File | Added/deleted lines |
| --- | --- |
| frontend/.gitignore | +5 / −0 |
| frontend/COVERAGE.md | +110 / −0 |
| frontend/MAINTENANCE-INTEGRATION.md | +232 / −0 |
| frontend/README.md | +217 / −21 |
| frontend/package.json | +2 / −1 |
| frontend/src/App.jsx | +22 / −10 |
| frontend/src/components/BackendMaintenance.jsx | +183 / −0 |
| frontend/src/components/BackendReadings.jsx | +386 / −0 |
| frontend/src/components/StoredAnalytics.jsx | +22 / −0 |
| frontend/src/data/telemetryResponseSample.json | +90 / −0 |
| frontend/src/services/analyticsAdapter.js | +35 / −0 |
| frontend/src/services/api.js | +1 / −1 |
| frontend/src/services/maintenanceAdapter.js | +63 / −0 |
| frontend/src/services/maintenanceApi.js | +51 / −0 |
| frontend/src/services/telemetryAdapter.js | +42 / −0 |
| frontend/src/services/telemetryApi.js | +104 / −0 |
| frontend/src/styles/dashboard.css | +49 / −0 |
| frontend/tests/additionalBrowserChecks.cjs | +67 / −0 |
| frontend/tests/analytics.test.js | +55 / −0 |
| frontend/tests/browserIntegration.cjs | +197 / −0 |
| frontend/tests/maintenance.test.js | +104 / −0 |
| frontend/tests/paginationBrowser.cjs | +55 / −0 |
| frontend/tests/telemetryAdapter.test.js | +84 / −0 |

The standalone C diff and existing PR18 differ only in the maintenance document
within frontend; use PR18 for the combined integration review rather than
publishing an overlapping PR. Existing rollout checks and human approval still
need assessment; mergeable and passing backend CI do not imply frontend CI.

## PR16 scope and next steps

Current published PR16 has14 files, +761/−242, focused on thermal history charts,
separate latest-completed/telemetry status, bounded cancellable stream polling,
shared telemetry/analytics client, tests and documentation. No backend diff.
The newly reviewed metadata/availability corrections are a local follow-up on
that actual source branch, not changes on feat/frontend-api-integration.

1. With explicit publication authorization, push the local contract-fix commit
   normally to codex/personc-analytics-comparison and update PR16's description
   with34-test/lint/build and real-browser results. Keep it draft as appropriate.
2. Review existing PR18's exact net diff and CI, resolve any feedback, obtain
   human approval and have a human merge it to main. No duplicate roll-up PR.
3. Fetch main after that merge and prove ff6918d/f0b3572 ancestry (or compare
   equivalent content if a squash/rebase merge was chosen). PR16 should be
   retargeted to main only once its frontend prerequisites are actually there.
4. With explicit base-change authorization, retarget PR16 from the old maintenance
   branch to main. Refresh its diff to ensure it contains only comparison/polling
   and contract corrections, excluding prerequisite/backend or duplicate mounts.
   Normally merge updated main into C's branch if integration is needed; avoid
   force-push. Run appropriate final checks and obtain human review before merge.

Dependency order: #1(already main) → #5/#12(roll-up through#18) → #16.
The closed #5/#12 cannot be retargeted as open PRs. Publishing a follow-up to
PR16 can precede PR18's human merge; retargeting should follow it.

## Local validation and preserved scope

34 declared tests, lint/build and actual Chrome/API checks passed for the
contract changes. Browser evidence timestamp2026-10-09T17:06:20.706Z
(22:36:20 IST), originhttp://localhost:3000, APIhttp://127.0.0.1:8000.
Confirmed metadata source/units/provenance, null health/confidence, coverage
counts, six-reading thermal values/gaps, unavailable coefficient-free results,
source isolation, CORS, offline/recovery and stale-response cancellation.
Actual backend is the preserved isolated preview; not current-main deployment.
Fixtures/unit assertions are distinguished from real browser requests.

What-if stays illustrative until a supported HTTP contract is deployed. No
Python callable is executed by the browser. Phone/LAN work remains deferred.
Environment files, Date.now()), original checkout, database and other worktrees
are preserved. No push, PR creation/base change, merge or teammate message.
