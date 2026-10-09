# Person C frontend starter

Existing React + Vite dashboard. The scaffold and dependency files are already committed; do not recreate the project.

## Run

From frontend: `npm ci`, then `npm run dev`. To verify the production bundle: `npm run build`. The generated template also supplies `npm run lint`.

## Screens

Fleet, Transformer, Alerts, What-if, Maintenance. All screens are currently defined in src/App.jsx. You do not need a pages folder yet.

## Mode and limits

Default mode is demo. Readings, analytics, alerts and future curves are fixed illustrative fixtures. No detection or thermal model runs in the frontend. What-if curves are independent of the selected sample condition. Maintenance tasks persist only in this browser's localStorage, not in a database. Sample acknowledgements reset when data reloads. There is no authentication, audit trail, downloadable report, WebSocket or SSE integration yet.

Create `.env.local` from `.env.example` to customize the mode. Restart the dev server after changes. VITE variables are visible to the browser; never put secrets in them.

## Proposed live API contract — agree before using

These routes are proposals, not verified team endpoints. The frontend expects the exact shapes illustrated in src/data/demoData.js. Change src/services/api.js or add adapters to match the real services.

- GET /assets returns [{id, name, rating}].
- GET /dashboard?assetId=... returns the dashboard object from makeDemoDashboard. Include source, sensor timestamp, quality, staleAfterSeconds, readings, analytics, history and alerts.
- POST /what-if receives {assetId, alternative}. Alternatives currently use identifiers lower-load and restore-cooling. Returns {assetId, assumptions, explanation, points:[{timestamp, baseline, alternative}]}.
- POST /alerts/:id/acknowledge saves acknowledgement; does not resolve the incident.
- GET /maintenance/tasks returns a task array.
- POST /maintenance/tasks receives {title, owner, assetId, alertId, evidence, recommendation}; returns the saved task.
- PATCH /maintenance/tasks/:id receives {status, notes}; returns the saved task.

Task statuses: Open, In progress, Completed. Live mode polls the selected dashboard every 5 seconds. A must allow the actual frontend origin through backend CORS. Adjust authentication together if needed.

## Next integration work

Confirm individual service contracts with A/B/D. Wire supported what-if inputs and explanations from B. Use D's shared task storage and acknowledgement lifecycle. Add fleet-wide condition snapshots, forecast uncertainty when available, configured limits, report downloads and incident history. Add live streaming only after its contract is agreed. Document units and source labels. Verify stale data, sensor loss, reconnect, failed requests and service restart.

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
