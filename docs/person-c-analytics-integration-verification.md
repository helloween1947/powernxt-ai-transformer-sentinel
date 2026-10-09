# Person C stored analytics browser verification

## Current-main validation after PR18 merge

Final freshness check: main advanced to `6289ed1` through PR20 while CI was
running. Its only change is 55 lines in `docs/integration-verification.md`.
Backend, analytics-model, frontend, integration and CI code are identical to
the tested main `7b19626`. This documentation-only advance was integrated
without conflicts at `b71896b`; the same 16-file analytics net diff is retained.
No additional test run is needed for unchanged application code. Current-head
hosted CI is checked after publishing this final follow-up.

PR16 now targets main. Main `7b19626ca49b81e99fc66bdba76fc55d305b8777`
was merged without conflicts into the C branch at
`de5fed97cf687e66a4eb3f5e503c43d3e63aca31`. Backend, analytics-model,
integration and CI code exactly match that main; the PR net diff contains only
analytics frontend/client/tests and supporting review documentation (16 files).
No maintenance implementation or duplicate mount is introduced.

Verified on 9 October 2026 at **22:56:13 IST**:

- Frontend: **34 tests passed**, lint and production build passed.
- Current-main backend: **222 tests passed** in the separate
  `sentinel_c_integration_test` database on Windows/Python 3.14. Existing
  dependency deprecation warnings were reported (223); no failures.
- Actual Chrome used `http://localhost:3001` and current-main backend code at
  `http://127.0.0.1:8001`. A new database copy of the preserved demo was upgraded
  to D004 for this run. Original environment files, demo database, original
  servers and unrelated work were preserved; temporary servers were stopped.
- Six stored thermal readings 7–12 showed the bootstrap gap and five finite
  predictions/residuals with elapsed_s=60. API/table values, units, provenance,
  null health/confidence, channel coverage and CORS passed. Coefficient-free
  electrical results, empty/source-isolated streams, offline/manual recovery,
  delayed actual-response cancellation and 390px emulation passed. No invented
  API payloads or uncaught page errors. These are browser checks against current
  main's backend code, not a shared deployment or physical-phone test.
- Current OpenAPI still exposes no scenario/What-if HTTP route; What-if remains
  illustrative. The previous real-worker polling run below is historical
  evidence; it was not repeated by creating new readings in this validation.

Local evidence is retained outside Git under
`integration-work/main-retarget-results/` (`verification.json`,
`current-main.json`, screenshots and temporary-server logs). The cloned database
is retained for diagnosis. Review and CI remain required before any human merge.
All sections below are the earlier pre-retarget verification snapshot.

Tested source commit: `1fdd8c246a971eb6f69c10f7fcd39a926b972c35`.
Final actual-browser verification: **2026-10-09 22:13:48 IST**.
Branch: `codex/personc-analytics-comparison`, based on published PR12 commit
`f0b3572e75ce920dc340af6922deeb60d8a6f660`. Documentation-only follow-up does
not alter the tested source. Draft review is stacked after PR12; frontend order
remains #1 → #5 → #12 → this comparison PR. Human review is required; no merge.

## Access and preserved setup

- Actual API: `http://127.0.0.1:8000`, local-machine access only.
- Actual Vite/Chrome origin: `http://localhost:3000` (loopback listener).
- Readiness200, database connected. Actual OpenAPI includes both analytics GETs.
- Existing CORS allows this origin; actual browser responses include matching
  Access-Control-Allow-Origin. No backend CORS, firewall, tunnel or LAN edits.
- Process-local frontend settings: `VITE_DATA_MODE=demo` and
  `VITE_API_BASE_URL=http://127.0.0.1:8000`. The existing checkout/environment
  files and unrelated Date.now()) file are preserved; no secrets committed.
- Local backend is the isolated combined preview at `676dcbc`, not merged-main
  maintenance verification. Analytics code matches main `9d2f9cd`. Existing
  database heads d003_audit_maintenance/d730a91b4c22 are retained; no migration
  changes, data deletion or teammate-branch merges in this task.

## Actual local streams

Asset: `demo-normal-76a8f79580bc4e95a490396989282be8`.
Source: `simulator`.

| Stream | Configuration/readings | Verified behaviour |
| --- | --- | --- |
| `thermal-9947eba4bdf34071ad87356461b812ab` | Configuration2, readings7–12 | Six completed. Reading7 initializes with null prediction/residual and initialized_from_measurement_prediction_not_independent. Readings8–12 have finite predictions/residuals at elapsed_s60. Latest telemetry/completed analytics both12. |
| `normal-76a8f79580bc4e95a490396989282be8` | Configuration1, readings1–6 | Completed electrical results; four missing thermal coefficient reasons, unavailable prediction/residual; health/confidence unsupported. |
| `thermal-poll-40a49a4da20448c29c5146d90b0338ec` | Configuration2, readings13–14 | Separate new two-reading demo. One worker step completed13 while14 remained pending; browser showed lag. Another step completed14; automatic five-second refresh rendered its result and stopped polling. Bootstrap gap preserved. |

The six-reading run already existed from the documented B overlay/simulator
procedure and was reused. The polling run was generated with the actual saved
configuration2, seed42, duration61s, interval60s, January start and initial oil45C.
Two bounded worker --once calls processed its two jobs; no daemon was started.
Original configurations and existing telemetry/results remain preserved.

## Supplied Person A evidence is separate

User supplied A's successful Windows run for asset
`demo-normal-85203b1018bc498c8b90873f383cc740`, simulator run
`thermal-144c79522cbd4cd092b7718fea4b05fe`, configuration2, readings20–25.
A's reported evidence paths are docs/thermal-demo-windows-20261009-214345-summary.txt
and data/generated/thermal-144c79522cbd4cd092b7718fea4b05fe/. These are reported
checks, not locally inspected artifacts. That asset returns404 on C's local API.
Loopback8000 does not connect to A's laptop. No remote URL was invented.

## Implementation and bounded requests

Backend readings extends the authoritative existing screen/client; it does not
add a second dashboard adapter or maintenance implementation. telemetryApi now
binds one injectable telemetryClient for both telemetry and analytics.

GET /api/v1/telemetry/{reading_id}/analytics uses envelope1.0.0 and stored result
schema stored-reading-result-1.1.0. GET /api/v1/assets/{asset_id}/analytics/latest
retains independent latest telemetry/status and latest completed reading/time.
Every telemetry/analytics request uses the same asset/source/run selection.
Device omits run_id; simulator/file_replay require one. Wrong-stream or reading
identity responses are rejected, rather than joined into selected data.

History is paginated20 at a time. Analytics requests deduplicate IDs and run
at most four concurrently, at most22 IDs for one page plus distinct latest and
completed readings. Charts cover the selected page and join by reading ID,
sorting UTC measurement time then ID. Available measured thermal values come
from result.payload.thermal_assessment; before processing, the measured curve
uses normalized telemetry. Prediction/residual are availability-gated, never
filled by zeros or fixtures. Residual is observed minus predicted, with explicit
sign and °C. Charts use elapsed measurement-time spacing, draw gaps for nulls
and expose exact values/UTC measurement and storage clocks in the table.

Each fetch times out after10s. Stream changes abort requests and invalidate late
responses even if a client ignores cancellation. Unmount cleans up requests and
timers. For pending/processing/retry, polling starts after a successful load,
every5s after completion of the prior load, at most six additional refreshes.
It stops on terminal states, error, stream/page change, unmount or the limit.
At the limit the operator can refresh manually. Polling errors retain the last
successful snapshot with a visible error and retrieval timestamp; no overlap or
WebSocket/event-recovery claims. The historical measurement clock remains
separate from API connectivity, retrieval clock and job processing status.

## Validation

- npm test: **30 passed** (6 telemetry,8 maintenance,6 analytics,10 stream tests).
- npm run lint and npm run build: passed. git diff --check: passed.
- Unit/client tests: null bootstrap, zeros/nonfinite values, partial availability,
  UTC ordering, ID joins, independent latest-completed lag, stream isolation,
  four-request concurrency, page offset, cancellation/generation guards,
  bounded polling/cleanup, failures and manual recovery. Unit inputs are fixtures.
- Actual Chrome: asset selection, six real thermal responses/chart/table, signed
  residuals, null initialization and five curve points, exact stored values and
  clocks, assumed provenance, CORS, device/replay/wrong-run empty streams,
  completed coefficient-free electrical output/thermal gaps, browser offline
  failure/recovery and stream switching during a delayed actual API response.
  No invented API response payloads. Delay/offline are explicit fault injection.
- Actual worker/browser: pending14 versus completed13, polling to completed14,
  stopping after terminal result. Separately retained generated evidence.
- 390px responsive emulation: no page-level horizontal overflow, internally
  scrollable tables. This is not a physical-phone check. No uncaught page errors.

Optional real-browser runner: frontend/tests/analyticsBrowser.cjs. It requires
Playwright installed separately and Chrome; no production dependency added.
Supply real DEMO_ASSET_ID/DEMO_RUN_ID, optional COEFFICIENT_FREE_RUN_ID,
FRONTEND_ORIGIN/BACKEND_URL and BROWSER_ARTIFACT_DIR. The standard unit test
script remains independent of a running backend/browser.

Retained local workspace evidence, excluded from Git:

- integration-work/analytics-comparison-results/verification.json
- integration-work/analytics-comparison-results/thermal-desktop.png
- integration-work/analytics-comparison-results/thermal-mobile-emulation.png
- integration-work/analytics-comparison-results/coefficient-free.png
- backend-local/data/generated/thermal-poll-40a49a4da20448c29c5146d90b0338ec/
  browser-poll-verification.json, browser-pending-lag.png, browser-completed.png
- backend-local/data/generated/thermal-9947eba4bdf34071ad87356461b812ab/
  original packets/configuration/stored results and verification artifacts

## Limits and remaining work

January timestamps and assumed coefficients are synthetic historical evidence.
The simplified uncalibrated predictor differs from the generator's equations
and time constant. Residuals are not fault labels or maintenance instructions.
Health/risk, numerical confidence, winding forecasts, fault diagnosis, RUL and
computed what-if contracts remain unsupported. No genuine alerts or trusted
identity are claimed. Continuous device streaming, WebSockets, shared deployment,
physical calibration and physical-phone/LAN checks were not performed.
CI and team review remain necessary. This PR depends on PR12; retain D PR10's
existing base pending backend/C prerequisites and review the replacement.
