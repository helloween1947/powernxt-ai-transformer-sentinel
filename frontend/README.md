# Transformer Sentinel — Frontend

Person C's operator dashboard, built with React and Vite.

## Current status

The dashboard includes:
- Fleet overview.
- Transformer detail.
- Alert investigation.
- What-if comparison.
- Maintenance.
- Backend readings.

The original five screens use illustrative fixtures by default.

The separate Backend readings screen uses request functions matching
Person A's documented asset and telemetry APIs. Its live connection
has not yet been verified.

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

## Reopening the dashboard on this Windows laptop

1. Open VS Code.
2. Select File > Open Recent > powernxt-ai-transformer-sentinel.
3. Open a Command Prompt terminal.
4. Run:

```cmd
cd /d "C:\Users\Akash Patil\OneDrive\Documents\powernxt-ai-transformer-sentinel\frontend"
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
node --test tests/telemetryAdapter.test.js
```

Confirmed during development:
- ESLint passed.
- Production build passed.
- Six telemetry adapter tests passed.

The adapter tests verify:
1. Asset, source/run, timestamps and configuration preservation.
2. Use of normalized readings.
3. Missing channels remain null.
4. Quality flags and pending status are preserved.
5. Genuine zero readings remain zero.
6. Absent readings and unknown statuses are handled.

These checks do not establish a successful live backend connection.

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

Request validation, backend tables and real-data behaviour still
need integration checks.

## Remaining work

- Verify requests against a reachable backend.
- Check actual assets, empty streams, history and pagination.
- Verify error handling and source/run isolation with real data.
- Agree and display stale-data status.
- Connect Person B's genuine analytical results when available.
- Connect Person D's shared maintenance and incident services.
- Agree live-update and reconnection behaviour.
- Address teammate review feedback.
- Verify the complete system and rehearse the final demonstration.

Live integration, genuine model outputs and backend maintenance
persistence have not yet been verified.

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
