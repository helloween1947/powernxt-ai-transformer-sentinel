# Executed Windows integration verification — 9 October 2026

**PR19 reconciliation:** main `7f5aad7` already contains merged PR16.
See [new Linux verification](pr19-main-reconciliation.md) for the resolved merge and its
limits. Windows/browser results below remain historical evidence for their
listed revisions; they were not rerun for this merge.

**Latest contract refresh:** fresh Windows verification of Person C `fa12a9bfccee4731246ea84fe516f58a1fe1490b` passed with **35 tests** and updated real Chrome checks. See [the refresh evidence below](#contract-refresh--9-october-2026-22552259-ist). The original 30-test/browser/reliability execution is preserved below as history, not treated as verification of the newer source.

**PASS for the real stored electrical/thermal demonstration.** Windows Chrome exercised the actual React application and backend. This is not a deployment, physical-model accuracy claim, maintenance deployment, or review approval. [Repeatable Windows procedure](integrated-demo-windows.md).

## Exact revisions and PR dependencies

| Component | Tested revision / observed state |
|---|---|
| Preserved original checkout | `main`, `9d2f9cda817bc6312d00a4fc001050b04b85a2cb`; unrelated untracked evidence preserved |
| Initial remote main incorporated in worktree | `090d5ee5fdb85ab1c59368cc05c1d009d4469f19`, includes Person D #9/#13 and starter #1 |
| Concurrent main update also incorporated | `7b19626ca49b81e99fc66bdba76fc55d305b8777`, #18 adds the C prerequisite frontend and D verification documentation/helpers |
| Person C comparison branch | `82e36e03791aa02e815ccd711b036706e24e0ccf` |
| Person C maintenance ancestor | `f0b3572e75ce920dc340af6922deeb60d8a6f660` |
| C telemetry ancestor | `e87a8856e9323c88854147c5ed7d4f54c336ba9e` |
| Combined local merge | `e1edce480067587b35ca622742a9e2bf27cfca36`, parents remote main090d5ee and C82e36e0 |
| Person B offline helper used for existing thermal creation | `dbe6a426916fab5c9a4d0c5544f68a14240a1cfd`; helper/worktree remains separate |
| Development backend/worker and fresh isolated reliability source | `9d2f9cda817bc6312d00a4fc001050b04b85a2cb`; analytics/worker code diff against combined main is empty |

The later documentation/browser-check commit is identifiable in Git history. No self-referential commit hash is invented here. Primary frontend runtime source remained unchanged from the combined merge throughout verification.

GitHub observed #12 **merged**, base `feat/frontend-api-integration`, head `codex/personc-maintenance-integration` f0b3572, merge commit `ff6918d300b79a83023f2b10e937f45e2f034b9f`. #16 is **open draft**, base `codex/personc-maintenance-integration`, head `codex/personc-analytics-comparison`82e36e0, mergeable against that base at inspection. Initially its #12 dependency and #5's feature-branch merge were absent from remote main. **At final delivery, concurrent #18 has incorporated the prerequisite frontend into main7b19626.** An ancestry check now confirms f0b3572 is in main; comparison82e36e0 is not. The integration branch was reconciled with7b19626 without conflict; additions are D's existing documentation/seed/verifier and updated maintenance documentation, with no changes to the tested frontend runtime/package files. Preserve these contributions. Retarget/reassess #16 against main now; draft [#19](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/19) offers the comparison plus Windows verification documentation/checks against current main. Choose the review route without double-applying #16.

Authenticated GitHub queries returned **no review submissions, no inline review threads, no head status contexts, and no PR-triggered workflow runs** for #12/#16. Thus there are no returned unresolved inline discussions; no approval or successful hosted frontend CI is claimed. #16's clean mergeability is against its current base, not a promise about a future main retarget. Public REST initially worked then hit rate limits; the connector supplied the remaining evidence.

## Environment and actual application

- Microsoft Windows NT10.0.26300.0; Node24.14.1, npm11.11.0; host virtual-environment Python3.14.3; normal Dockerfile Python3.12 image; Docker Desktop client/server29.8.2, Compose5.5.1.
- Integration branch `feature/integrated-demo-windows`, worktree `.worktrees/integrated-demo-windows`. No applicable AGENTS.md found. Original main was not switched, reset, pulled or modified.
- Frontend `http://localhost:3000`, API setting `VITE_API_BASE_URL=http://127.0.0.1:8000`, `VITE_DATA_MODE=demo`, started with `npm.cmd run dev -- --host localhost --port 3000 --strictPort` from frontend. CORS returned the exact3000 origin already configured. No CORS edit or development restart.
- Normal backend/worker remain running with their pre-task image IDs and start times. Actual `alembic current` is `d730a91b4c22 (head)`. No development migration/build/recreation took place. Remote main's maintenance join exists in source but is not in the deployed image; maintenance GET returned404 and is outside this stored-analytics demonstration.
- The native browser-control surface failed during Windows sandbox initialization. Optional Playwright operated installed Windows **Google Chrome**, navigating/clicking/filling actual application controls. HTTP-only checks and screenshots were not treated as browser integration by themselves. Headless browser interaction was verified; no physical phone/manual visible-browser session is claimed.

## Development stream — actual backend records

| Field | Value |
|---|---|
| Asset | `demo-normal-85203b1018bc498c8b90873f383cc740` |
| Source | `simulator` |
| Run | `thermal-144c79522cbd4cd092b7718fea4b05fe` |
| Configuration | 2, created in the previous actual Windows thermal demonstration |
| Readings | 20–25, measurement2026-01-01T00:00–00:05Z |
| Original coefficient-free stream | `normal-85203b1018bc498c8b90873f383cc740`, configuration1 |
| Latest telemetry/completed analytics | Both reading25; model `stored-reading-top-oil-1.0.1` |

Identifiers above are observed **development database records**, not universal setup IDs and not records from the isolated test database. This task reused them; it did not append another development configuration or submit development telemetry.

| Reading | Measured°C | Predicted°C | Residual°C | elapsed_s |
|---|---:|---:|---:|---:|
|20|45.000000|null|null|null|
|21|44.907440|45.009608|−0.102168|60|
|22|44.829156|45.022382|−0.193226|60|
|23|44.765094|45.038749|−0.273655|60|
|24|44.715045|45.058314|−0.343269|60|
|25|44.678637|45.080790|−0.402153|60|

Browser table values were compared at full API precision. The first reason is `initialized_from_measurement_prediction_not_independent`; chart has six measured points, five prediction points and five signed residual points. Negative residuals remain negative. Reading-bound configuration, model version, measurement/storage/retrieval clocks and explicitly assumed thermal provenance are visible. Data are joined by reading_id and sorted by measurement_time. January values are labelled historical synthetic evidence, not live readings or fault alerts.

## Checks actually executed

| Check | Actual result |
|---|---|
| Locked dependencies `npm.cmd ci` | Exit0;143 packages; npm reported0 vulnerabilities |
| Declared `npm.cmd test` | Exit0;30 passed,0 failed/skipped |
| `npm.cmd run lint` | Exit0 |
| `npm.cmd run build` | Exit0;Vite8.3.3 production bundle |
| C's `node tests/analyticsBrowser.cjs` | Exit0; real six-row API/CORS/Chrome comparison, chart gaps, provenance, empty device/replay/nonexistent run, offline/manual recovery, delayed actual-response stream cancellation, coefficient-free original stream |
| Added `node tests/integratedDemoBrowser.cjs` | Exit0; actual electrical metrics/model, historical wording, reload; labelled HTTP503 injection retains telemetry while predictions unavailable; labelled pending injection separates latest/completed and stops after exactly6 refreshes (7 total loads) |
| `node tests/analyticsPaginationBrowser.cjs` | Exit0; actual isolated22 readings paginate20/2 by correct IDs and return to page1; no fixture response |
| Page errors | None in all passing Chrome runs |
| Responsive | Desktop1280/1440 and390px narrow emulation; no page-level horizontal overflow; tables scroll internally; screenshots visually inspected |
| Integration merge / diff whitespace | No conflict; whitespace check passed; no backend modifications relative to remote main |

Error/processing injections are explicitly browser-local test conditions, **not** proof that normal jobs were actually pending or that the backend returned503. Offline toggling and delayed actual API responses exercised the application rather than replacing the thermal evidence with fixtures. The existing30 tests separately cover cancellation even for clients ignoring AbortSignal, wrong-stream identity, deduplication, four-request concurrency, bounded polling, terminal stops, page offset and manual recovery. No reproducible application defect was found; no model equations, parameters, or unrelated UI design were changed. Added browser checks make previously unrecorded integration boundaries repeatable.

## Fresh isolated worker reliability — separate from browser evidence

Executed at22:33:54–22:36:04 IST on9d2f9cd using the existing Windows execution harness and documented integration module. Test project `analytics_worker_test_8110c031`, API18002, database `worker_integration_test`, unique retained volume `analytics_worker_test_8110c031-postgres_data`.

Normal repository `backend/Dockerfile` builds with `--pull --no-cache` passed for backend/worker (exit0). Migration, integration module, Alembic current/check, stack stop and container-status check all exited0. Initial six completions, six identical retries without count/state changes, final8 readings/jobs/results across independent runs, stream advances `[1,7]`, abandoned lease recovery attempts2 and restart persistence passed. Revision `d730a91b4c22 (head)`; no new upgrade operations. All guide environment values restored in `finally`; test volume retained. Normal development worker was never stopped.

Isolated integration asset `demo-worker-3ae4e076f12f4dfeb5560edc197dee85`, run `worker-3ae4e076f12f4dfeb5560edc197dee85`. For supplemental real pagination this stopped stack was briefly restarted, with a **separate** run `pagination-c31f9599c6224198a5712a464cbffafb`, configuration1,22 synthetic readings9–30. A temporary frontend at`http://localhost:5173` used API`http://127.0.0.1:18002` with the same actual VITE settings. Pagination Chrome evidence passed20/2. This append happened **after** the8-record reliability assertions; the retained test asset now has30 readings, not8. Test services and temporary5173 process were stopped again; data/volume retained and process-local variables restored. Its IDs9–30 are unrelated to development IDs20–25 even where the numbers overlap.

## Evidence and remaining limits

Portable sanitized summary accompanies these guides. Complete local browser logs/screenshots/JSON are under ignored `data/generated/integrated-demo-20261009/` in the integration worktree. Optional Playwright installation is under ignored `data/generated/integrated-browser-tools/`. The original repository retains `docs/analytics-worker-windows-20261009-223354.log` and `.json` plus generated isolated worker artifacts; these are not included in the review commit. No `.env`, credentials, database URLs, volumes or large generated datasets are staged. The existing untracked Windows evidence scripts remain intact.

Development frontend3000 is left running for the presentation. Isolated services and temporary pagination frontend are stopped. No teammate message, PR merge, approval, force-push, public deployment, or database deletion occurred. The authorized branch push/draft PR submission is reported separately at delivery.

Remaining review/CI: human review of C's incorporation and #16, applicable frontend CI (no success observed), and resolution of the stacked merge route. Maintenance deployment is separate; no maintenance workflow verification is claimed against the currently deployed9d backend. Physical phone/LAN access, production identity, WebSockets/automatic reconnect, independent thermal calibration and field accuracy remain unverified. Browser polling is bounded and recovery manual. Fixture health/confidence/forecasts and browser-local sample tasks remain clearly labelled illustrative screens.

## Contract refresh — 9 October 2026, 22:55–22:59 IST

PR #19 was open/draft at prior head `e0db8d3486114e3e62413e762472b632b89208b2`; its exact-head Backend CI run37965401940 was independently confirmed **completed/success**, rather than merely repeating supplied history. PR #16 is now open/draft **against main**, at `fa12a9bfccee4731246ea84fe516f58a1fe1490b`. Neither proposal has merged. Main remained `7b19626ca49b81e99fc66bdba76fc55d305b8777` at this refresh.

Ancestry and source differences showed exactly one missing Person C commit after the previously integrated `82e36e03791aa02e815ccd711b036706e24e0ccf`. It was incorporated with a normal, conflict-free cherry-pick, retaining C's author, as `2f8a9b2738d3aead590437e8f708fbc38148ae31`. Integration guides/runners and D's already incorporated source/evidence remain present. Runtime files match Person C's fa12a9b; the integration adds only regression/browser evidence and documentation. No backend/model/application equation change.

Included fixes:

- Reject present metadata whose reading/configuration/stream/source/time differs from the analytical envelope.
- Join stored results by reading_id and reject conflicting configuration/time references against joined telemetry.
- Read units from supported metadata; absent or incompatible units retain unavailable values/reasons, never unsupported Celsius chart values. Model-bound measured oil is also unit-gated.
- Display metadata measurement source/time and preserve model/parameter/configuration provenance.
- Keep health/confidence null and visibly unavailable. Required-channel coverage remains a count, not a score or percentage. Initialization/null/genuine-zero behavior is preserved.

Actual localhost3000 process command points to this integration worktree's Vite; its served `analyticsAdapter.js` includes the updated unit guard. Vite picked up source changes, so no frontend restart was needed. Fresh Chrome pages loaded the new source. Backend readiness remained ready; backend/worker retained their original image IDs and start times. No configuration/telemetry/job writes, restart, migration, environment-file edits, or volume operations occurred.

| Fresh check | Executed result |
|---|---|
| `npm.cmd test` after C incorporation | Exit0,34 tests passed |
| `npm.cmd test` with additional chart-unit regression | Exit0,**35 passed**,0 failed/skipped |
| `npm.cmd run lint` | Exit0 |
| `npm.cmd run build` | Exit0, Vite8.3.3 production bundle |
| Updated `node tests/analyticsBrowser.cjs` | Exit0; real six-row/units/provenance/metadata coverage, initialization, five finite signed predictions/residuals, empty device/replay/nonexistent run, offline/manual recovery, delayed-response cancellation, desktop and390px layout |
| Extended `node tests/integratedDemoBrowser.cjs` | Exit0; exact electrical values; unavailable health/confidence and coverage wording; labelled HTTP503, pending/lag and F-unit injections; seven total loads then polling stops; actual C-unit recovery |
| Read-only metadata comparisons | All6 reading/message IDs, configuration/time, model ID/version and parameter version agree with actual telemetry/envelopes; oil/residual unitsC; usable/required coverage8/8; assumed provenance retained |
| Browser page errors | None |

The added regression tests the complete chart join with incompatible oil/residual units and requires all three thermal series values to remain null. The extended browser injection similarly makes one reading's model unitsF and verifies unavailable measured/predicted/residual table values and missing Celsius points, then restores real responses. It does not transform stored Celsius data into Fahrenheit or claim the backend ever returnedF. The actual backend thermal stream remains asset `demo-normal-85203b1018bc498c8b90873f383cc740`, source simulator, run `thermal-144c79522cbd4cd092b7718fea4b05fe`, configuration2, readings20–25. Historical synthetic labelling and the six-row values above remain unchanged.

Fresh artifacts are under ignored `data/generated/integrated-demo-contract-20261009/`: npm/browser logs, served adapter source, actual-metadata-checks.json, desktop/narrow/detail screenshots and browser JSON results. Earlier artifacts were not overwritten. Updated sanitized `integrated-demo-evidence.json` adds this refresh separately from the earlier30-test browser run and isolated pagination/reliability history. No unrelated backend suites were rerun; frontend contract changes do not justify reprocessing development data.

Final pushed-head CI is checked after the documentation/regression commit and reported in PR #19 and local final-head evidence; a successful run for old e0db8d3 does not validate the new head. Review #19 as the combined route, or merge #16 first and reassess #19's net Windows checks/docs diff. No retarget/close/review mutation of #16 was performed. Maintenance deployment, physical-phone access and independent calibration remain outside this refresh.
