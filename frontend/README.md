# Transformer Sentinel — Frontend

**PR19 reconciliation:** main `7f5aad7` already contains merged PR16.
See [new Linux verification](../docs/pr19-main-reconciliation.md) for the resolved merge and its
limits. Windows/browser results below remain historical evidence for their
listed revisions; they were not rerun for this merge.

Person C's operator dashboard, built with React and Vite.

Telemetry and sample maintenance were verified in an isolated combined checkout.
See [MAINTENANCE-INTEGRATION.md](MAINTENANCE-INTEGRATION.md) for frontend
authority, contracts, PR dependencies, validation and remaining deployment limits.

## Current status

The dashboard includes:
- Fleet overview.
- Transformer detail.
- Alert investigation.
- What-if comparison.
- Maintenance.
- Backend readings.
- Backend maintenance (separate PostgreSQL-backed sample tasks).

The original five screens use illustrative fixtures by default.

The separate Backend readings screen uses request functions matching
Person A's asset and telemetry APIs. Its local browser connection is verified.
Backend maintenance also connects to D's published sample workflow API using
a separate local backend preview. Shared deployment remains pending review.

## Requirements

- Node.js LTS and npm.
- Git for repository collaboration.
- A reachable backend for actual asset and telemetry requests.

## First-time installation

Open a terminal inside the frontend folder:

```cmd
npm ci
npm run dev
```

Open the Local address printed by Vite.

## Reopening the dashboard on a Windows laptop

1. Open VS Code.
2. Select File > Open Recent > powernxt-ai-transformer-sentinel.
3. Open a Command Prompt terminal.
4. Run:

```cmd
cd /d "<your-checkout>\frontend"
npm run dev
```

Open the Local address printed in the terminal, usually:

http://localhost:5173/

Keep that terminal running while using the dashboard.
Press Ctrl+C to stop the server.

There is no need to clone or recreate the application each time.

## Verification commands

Run these from the frontend folder in another terminal:

```cmd
npm run lint
npm run build
npm test
```

Confirmed during development:
- ESLint passed.
- Production build passed.
- Thirty-four declared tests cover telemetry, maintenance, stored analytics and bounded stream loading/metadata identity.

The adapter tests verify:
1. Asset, source/run, timestamps and configuration preservation.
2. Use of normalized readings.
3. Missing channels remain null.
4. Quality flags and pending status are preserved.
5. Genuine zero readings remain zero.
6. Absent readings and unknown statuses are handled.

Unit tests alone do not establish a live connection. The separate real Chrome
checks and their exact scope are recorded in MAINTENANCE-INTEGRATION.md.

## Demo screens

Fleet, Transformer, Alerts, What-if and Maintenance use sample data
when VITE_DATA_MODE is demo or unset.

- Readings and condition assessments are fixtures.
- Temperature predictions and what-if curves are illustrative.
- What-if curves do not depend on the selected sample condition.
- Sample alerts are not produced by a running detector.
- Sample acknowledgements reset when fixture data reloads.
- Maintenance tasks are stored in this browser's localStorage.
- Tasks are not shared with teammates or stored in a backend database.

Keep the demo labels visible when demonstrating these screens.

## Backend readings screen

This screen supports:
- Paginated registered assets.
- Asset details and current configuration.
- Latest telemetry.
- Paginated history, oldest first.
- Explicit device, simulator or file-replay selection.
- Required run IDs for simulator and replay sources.
- Measurement and arrival timestamps.
- The configuration version attached to a reading.
- Missing values and per-channel quality information.
- Out-of-order indicators.
- Analytics and processing-job status.
- Loading and request-error messages.

Requests occur when the operator clicks the loading buttons.
This screen does not automatically poll or subscribe to live events.

It does not calculate loading, health, confidence, predictions,
forecasts, or maintenance recommendations.

## Documented backend routes

```text
GET /api/v1/assets?limit=20&offset=0
GET /api/v1/assets/{asset_id}
GET /api/v1/assets/{asset_id}/telemetry/latest
GET /api/v1/assets/{asset_id}/telemetry
```

Asset and history pages return objects containing:
- items
- limit
- offset

Assets use asset_id.

Simulator and replay telemetry requests include source and run_id.
History requests can include start and end timestamps with explicit
timezone offsets.

## Backend configuration

Obtain these details from Person A:
- A backend address reachable from this laptop.
- A registered asset ID.
- The telemetry source.
- A run ID for simulator or file-replay readings.
- Confirmation that CORS allows the actual frontend origin.

Create frontend/.env.local and set VITE_API_BASE_URL to that address.

Leave VITE_DATA_MODE as demo for now. The separate Backend readings
screen can request actual data without switching the original
fixture screens into their unfinished live mode.

Restart the Vite server after changing environment variables.

VITE-prefixed configuration is visible in the browser.
Do not place passwords or API secrets in it.

## Data-display rules

- Use normalized telemetry for displayed measurements.
- Keep null values unavailable; never convert them to zero.
- Preserve backend quality flags.
- Display source and run identity explicitly.
- Keep current registry configuration separate from the version
  attached to a reading.
- Show pending analytics as pending.
- A pending processing job is not a completed analytical result.
- Do not substitute demo predictions for missing backend results.

## Important files

```text
src/App.jsx
src/components/BackendReadings.jsx
src/components/ReadingCard.jsx
src/components/TrendChart.jsx
src/services/api.js
src/services/telemetryApi.js
src/services/telemetryAdapter.js
src/data/demoData.js
src/data/telemetryResponseSample.json
src/styles/dashboard.css
tests/telemetryAdapter.test.js
```

telemetryResponseSample.json is a documentation fixture.
It is not evidence of current backend readings.

## Manual checks completed

- Sample electrical readings and temperature charts displayed.
- Sample alert and maintenance workflow exercised.
- Browser-local task status and notes survived refresh.
- Sample what-if curves displayed.
- Sample sensor-loss alert displayed.
- Run ID hidden for Device and visible for Simulator/File replay.
- Narrow-screen controls checked and layout overflow improved.

Local backend browser checks are now recorded in MAINTENANCE-INTEGRATION.md.
Physical-phone backend access and final shared deployment remain unverified.

## Remaining work

- Review and deploy the final shared A/D/C integration; local requests passed.
- Repeat local asset/stream/history checks against the final team deployment.
- Repeat verified source/run isolation and errors on the final team deployment.
- Agree and display stale-data status.
- Connect Person B's genuine analytical results when available.
- Review D's backend PR9 with the latest main worker migration; reconcile their
  new dual heads and router/model registrations before shared deployment.
- Agree genuine persisted alert provenance before real-alert task creation.
- Agree live-update and reconnection behaviour.
- Address teammate review feedback.
- Verify the complete system and rehearse the final demonstration.

Local browser telemetry and sample backend maintenance persistence are verified.
Stored electrical/top-oil results from the isolated synthetic thermal run are
verified in Backend readings. Physical-phone backend access, production identity,
independent model calibration and final shared deployment remain unverified. See MAINTENANCE-INTEGRATION.md.

---

## Shared frontend scope and backend development reference

**Owner**: Person C (Frontend Engineer)

### Planned Scope & Responsibilities
- Real-time transformer telemetry monitoring dashboard.
- 3-Phase electrical waveform & load balance visual charts.
- Thermal behavior and anomaly indicator views.
- "What-If" scenario simulator interface (load manipulation, ambient stress testing).
- Alerting & maintenance notification views.

### Backend Development Reference
- **Local API Base URL**: `http://localhost:8000` (only when the backend runs on the same computer as the browser).
- **Interactive Documentation**: `http://localhost:8000/docs`
- **Health Verification**:
  - `GET /health/live`: Server process check.
  - `GET /health/ready`: Database connectivity check.
- **CORS Configuration**:
  - Development ports `http://localhost:3000` (React/Next) and `http://localhost:5173` (Vite) are pre-configured in `backend/app/config.py`.

The scope list describes intended team responsibilities, not a claim that the
starter implements real analytics or backend maintenance. Confirm the actual
frontend origin and backend contract before enabling live routes.

Current local analytics scope, manual evidence and deferred work: [COVERAGE.md](COVERAGE.md).


## Stored thermal comparison and processing lag

Backend readings now displays separate latest telemetry/latest completed analytics,
per-reading availability, model/version/configuration references, assumed parameter
provenance and measured/estimated/residual curves for the selected history page.
See [actual verification](../docs/person-c-analytics-integration-verification.md)
for tested commit, local identifiers, browser results and limitations.

Use a reachable backend with the stored analytics API/migration installed and
its worker available. Keep `.env.local` local, e.g. VITE_DATA_MODE=demo and
VITE_API_BASE_URL=http://127.0.0.1:8000 when browser/backend run on this laptop.
The original fixture screens remain demo views. In the isolated review checkout,
these values were passed as process-local settings; existing environment files
were not copied or overwritten. Vite ran at http://localhost:3000, an origin
already permitted by the local backend. Check readiness/CORS for your actual
origin. Localhost/127.0.0.1 never refers to a teammate's laptop.

For the preserved isolated native setup, follow LOCAL-INTEGRATION.md in the
original frontend checkout and its local start-local-demo.ps1. For the shared
backend, use reviewed [worker startup](../docs/analytics-worker-windows.md) and
[worker policy](../docs/analytics-worker.md). Do not rerun migrations blindly
against a teammate database. Worker startup may process retained pending jobs.

To create a thermal demonstration in a checkout containing B's reviewed
`integration.prepare_thermal_demo` helper and overlay, follow the handoff on
`feature/personb-thermal-demo` at dbe6a426916fab5c9a4d0c5544f68a14240a1cfd:
retrieve the exact existing configuration through its paginated history; save it;
run `python -m integration.prepare_thermal_demo --configuration-json SNAPSHOT
--output NEW_PAYLOAD`; review preserved ratings and four assumed coefficients;
POST the new configuration and capture its returned version; generate/send a
NEW labelled simulator run bound to that version. Duration301s/interval60s gives
six chronological samples. Execute the reviewed worker, then retrieve each
reading result and latest analytics. Preserve old configurations/results and
generated artifacts. Never reuse A's asset/run IDs without checking your API.

The read API routes are:

```text
GET /api/v1/telemetry/{reading_id}/analytics
GET /api/v1/assets/{asset_id}/analytics/latest?source=simulator&run_id=RUN
```

Source/run isolation also applies to telemetry latest/history. Per-reading
envelope1.0.0/result stored-reading-result-1.1.0 are supported. Thermal fields
are under result.payload.thermal_assessment. A completed job may have unavailable
metrics; bootstrap prediction/residual remain null. The chart preserves gaps,
zeros and signed residuals and separates UTC measurement/storage/retrieval clocks.
The latest completed result can lag telemetry and is labelled separately.

Each history page has20 readings; ID requests are deduplicated and concurrency
is capped at4. Requests have10s timeouts. Pending/processing/retry trigger at most
six five-second refreshes after the initial load, without overlapping requests.
Terminal states, errors, changes of stream/page and unmount stop polling. Filters
remain usable during loading; cancellation plus generation guards prevent late
responses repopulating another stream. At the limit, refresh manually. There is
no WebSocket transport or automatic event recovery. Historical synthetic values
remain historical even when API connectivity and processing are healthy.

Run `npm test`, `npm run lint` and `npm run build`. For optional actual Chrome
verification, set DEMO_ASSET_ID/DEMO_RUN_ID to the six-reading local demo, optional
COEFFICIENT_FREE_RUN_ID and FRONTEND_ORIGIN/BACKEND_URL, then run
`node tests/analyticsBrowser.cjs` with separately installed Playwright/Chrome.
Its output identifies actual API checks and explicit offline/delay injection.
Generated evidence is ignored. Phone testing remains deferred.


## Latest B contract clarification (local review)

Metric units come from metadata.units; metadata measurement_source/time and
parameter provenance are explicit. Missing/incompatible units cannot become
Celsius chart values. Health is unavailable/not_assessed; numerical confidence
is unavailable/not_estimated. Usable channel counts are coverage, not confidence
percentages. Metadata and telemetry identities/configuration/time are checked.
Existing null/zero/gap and latest-completed lag behaviour is retained.

B's compare_worker_scenarios is a tested Python callable on unmerged PR7; no
scenario HTTP route appears in the actual backend OpenAPI. What-if remains a
fixture view. COVERAGE.md records the answered stored-field request and a short
unsent request for HTTP schemas, binding/assumptions/units/validation/availability.

PR18 has merged the #5/#12 roll-up into main. PR16 now targets main, integrated
without conflicts at de5fed97. 34 frontend tests, lint/build, 222 current-main
backend tests and actual Chrome/API checks passed. Browser validation used a
separate copied database upgraded to D004 and temporary ports 3001/8001;
environment files and the original demo database/servers were preserved.
See ../docs/person-c-analytics-integration-verification.md for current evidence.
Human review and current-head CI remain required before merge. What-if remains
illustrative and phone testing remains deferred; no teammate message was sent.

Historical pre-PR18 inspection (retained as evidence, not current status):

The latest review inspection found #1/#5/#12 already merged by D without recorded
formal reviews/comments; #5/#12 landed in stack branches and have not reached
main. An authorized reviewed roll-up to main is still needed. No merge, push,
PR-base change or teammate message is performed for this local update.
