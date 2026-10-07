# Person C frontend starter

React + Vite dashboard. Scaffold the app first with `npm create vite@latest frontend -- --template react`, then copy the supplied source files into it. Keep the generated package.json, package-lock.json, index.html and Vite configuration.

## Run

From frontend: `npm install`, then `npm run dev`. To verify the production bundle: `npm run build`. The generated template also supplies `npm run lint`.

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
