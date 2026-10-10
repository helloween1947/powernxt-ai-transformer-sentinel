## Replacement backend integration · 11 October 2026

A new independent backend is available in [backend_next](../backend_next/README.md), serving localhost:8001. Connected mode now supports transformer registration/configuration, live synthetic feeds, saved run selection, CSV/XLSX column mapping, dataset import and whole-dataset configured-condition findings through the Data inputs panel. Existing browser connection preferences may need updating to port 8001. Backend setup, units, upload limits, method and current validation are documented there. The earlier frontend-only verification below records the 10 October rebuild and is not a statement that this newer backend work was frontend-only.

# PowerNXT · Transformer Sentinel

React/Vite operator workstation rebuilt around an interactive distribution transformer. Navy/steel-blue light and dark themes, a collapsible rail, glass measurement callouts, a prominent unvalidated Condition Rating, synchronized record inspection, exact-value chart tables and accessible detail sheets are implemented. The Workspace view uses built-in fixed history. Display labels are concise; canonical mode, record identities and export provenance remain intact.

## Run

Use Node 22.12+ (compatible with the Vite version in the lockfile) and npm:

```sh
cd frontend
npm ci
npm run dev
```

Open the address printed by Vite. Verification: `npm test`, `npm run lint`, `npm run build`. To inspect the production build locally: `npm run preview`.

Copy `.env.example` to `.env.local` if needed. `VITE_DATA_MODE=sample` is the default; `live` selects the backend workspace. `VITE_API_BASE_URL=http://localhost:8000` applies when the browser and backend run on the same machine. Connection settings also save a browser-local API URL, which takes precedence over the environment setting. Confirm backend CORS for the actual Vite origin. Vite environment variables are public: do not put secrets in them.

## Workflows

| Page | Implemented behavior |
|---|---|
| Fleet overview | Paginated registry, bounded device-stream retrieval, measured timestamps, processing state and configured ratings; no fleet health/risk score |
| Digital twin | Original 3D transformer, camera-linked XYZ indicator, rounded category selector, semantic callouts, component selection, rotation/zoom opt-in, camera reset; full electrical/thermal/condition lists and data-quality/provenance view |
| Condition explorer | Eight dedicated oil, electrical, pressure/inventory, thermal, impedance, mechanical, health/life and maintenance/incident surfaces; unsupported values stay unavailable with their own contract requirements |
| Trends & history | Time filters, 20-record backend pages, measured/estimated temperature, residual, loading, apparent power, phase voltage/current and oil level; gaps and exact-value tables; click/drag timeline with shared reading selection and keyboard control |
| Alerts & incidents | Validated stored configured-limit evidence; persistent incident actions remain planned |
| Maintenance | Browser-local sample tasks; separate versioned backend **sample-alert** workflow with conflict review, required notes, terminal states and history |
| What-if analysis | Input preview, hypothetical 120% loading preset and explicit unavailable comparison state; no scenario execution or invented curve |
| Reports | CSV of only the retrieved history page, including units and provenance; separate labelled bench workbook comparisons |

Nine normalized channels are supported: R/Y/B voltage and current, oil temperature, ambient temperature and oil level. Compatible completed stored analytics can supply apparent kVA, capacity loading, worst-phase loading, magnitude imbalance, thermal load, simplified top-oil estimate and residual. The current reading's processing state is distinct from the latest completed result. Parameter units, finite values, availability, quality, reading/stream/time/configuration/model identity are checked before joining results. Contradictory analytics is withheld while valid telemetry stays available.

Device readings are labelled with their actual measurement time and age. The two-minute freshness indicator is an interface policy, not a sensor failure or electrical fault threshold. Simulator/replay records retain source/run identity and are labelled stored. Missing or bad/sanity-failed channels become unavailable, not zero. Suspect values retain their quality. A request failure does not establish asset failure.

## Condition Rating

`condition-rating-prototype-v1` is a pure, unvalidated display heuristic, separate from authoritative Health Index/RUL. Loading and measured oil temperature require good-quality, unit-compatible evidence bound to the inspected reading and its configured limits with provenance. No imbalance or oil-minimum rule exists in the current configuration contract; those groups are excluded. At least two groups and 50% intended weight coverage are required. Missing evidence reduces coverage without deducting physical-condition points. Limit breaches remain visible independently of the score; stale device evidence retains its time. Samples are isolated and labelled. The prototype is not persisted or included in telemetry exports. See the methodology and deterministic tests.

## Actual API integration and checkout limitation

Canonical clients/adapters are reused for these route families:

```text
GET /openapi.json
GET /api/v1/assets?limit=20&offset=0
GET /api/v1/assets/{asset_id}
GET /api/v1/assets/{asset_id}/telemetry/latest?source=...&run_id=...
GET /api/v1/assets/{asset_id}/telemetry?source=...&run_id=...&start=...&end=...&limit=20&offset=...
GET /api/v1/telemetry/{reading_id}/analytics
GET /api/v1/assets/{asset_id}/analytics/latest?source=...&run_id=...
GET, POST /api/v1/maintenance/tasks
GET, PATCH /api/v1/maintenance/tasks/{task_id}
GET /api/v1/maintenance/tasks/{task_id}/history
```

Device run IDs are null/omitted; simulator and file replay require a run ID. History is ordered by measurement time, with explicit UTC start/end filters. The analytics adapters support envelope `1.0.0` and stored result `stored-reading-result-1.1.0`; model and parameter versions come from the backend. No unmerged model-1.0.2 contract is adopted.

**This checkout is on `feature/personb-detector-orchestration` at `d86b210`; its backend implements asset/telemetry routes but lacks HTTP stored-analytics and maintenance routes.** Canonical frontend clients are retained, but optional requests are disabled until `/openapi.json` on the connected runtime advertises each complete implemented route family. The runtime's advertised routes do not prove worker health; returned payloads still pass strict identity/unit/schema/provenance adapters. No unmerged remote feature is assumed deployed. Incidents and persisted What-if remain planned interfaces; no proposed endpoint is called. This iteration changes only `frontend/**`.

History joins use at most four simultaneous per-reading analytics requests, 10-second request timeouts and deduplication. Completed/unavailable per-reading responses are cached up to 200 entries within a backend/asset/source/run scope. Changing source, run, asset, connection or page cancels outstanding work and discards obsolete responses. Pending jobs allow six five-second retries. Successful settled streams refresh after 30 seconds; errors or exhausted pending work require manual refresh. No overlapping refresh or WebSocket subscription is claimed. An absent latest-analytics route does not trigger an entire page of failed per-reading requests.

Backend maintenance is explicitly a sample workflow. `X-Demo-Actor` is a demo attribution header, not authentication. A 409 retains the local draft and requires operator review of the new version before retry. Completing/cancelling requires notes, and terminal tasks are read-only. Navigating away cancels outstanding maintenance requests. UI fixture tasks are saved only in this browser and are separate from backend tasks.

## Sample and reference data

`workstationSample.js` is independent, fixed-date UI illustration data (9 October 2026). No sensor, predictor or What-if model runs. Health, fault prediction and RUL remain unavailable even in sample mode. Bench comparisons in `workbookEvidence.js` were transcribed from the supplied workbook without adding timestamps, asset IDs or telemetry. Measurement comparisons use reference minus software; trip comparisons use software minus reference. Workbook blanks are not zero. No source material is uploaded.

## Design and files

- `src/App.jsx`: shared asset/source/run/page context, themes, navigation, export and connection settings.
- `src/components/layout/`, `src/styles/dashboard.css`, `src/index.css`: responsive shell and semantic design tokens.
- `src/components/ui/`: JavaScript shadcn-style Button and Radix Dialog primitives, with focus management and mobile sheets. Tailwind is configured with the Vite plugin.
- `src/components/digital-twin/`: lazy original R3F/Drei geometry, projected anchors and scene availability handling. See [geometry attribution](public/models/ATTRIBUTION.md).
- `src/data/capabilities.js`: tested capability/anchor registry and truthful availability mapping.
- `src/components/metrics/`, `src/components/charts/`, `src/components/workflows/`: measurements, exact-value charts and operator workflows.
- `src/hooks/useWorkstation.js`, `src/services/`: cancellation, bounded polling, canonical contracts, provenance validation and CSV export.
- `tests/`: 79 Node contract/state tests and a local contract fixture server, excluded from application runtime.

The scene renders on demand, caps DPR at 1.5 desktop / 1.2 mobile, uses a 1024 px desktop / 512 px mobile shadow map and no external textures, post-processing, automatic rotation or runtime model download. Semantic anchor regions are illustrative; physical sensor positions are unverified. Unsupported WebGL or scene/context failure shows a concise unavailable state. Metrics remain keyboard accessible without canvas interaction. Motion uses shared easing for controls, view fades and camera reset. Measurement callouts keep fixed positions and solid backgrounds, with a short opacity reveal when filtered. Inspection dialogs fade independently with a small vertical entry; their text is never scaled or warped. The unused ambient-animation control has been removed. Numeric figures remain stable, and chart dragging updates exact readings immediately. Motion respects reduced-motion preferences.

Named design resources were consulted during implementation: [shadcn Vite](https://ui.shadcn.com/docs/installation/vite), [Motion React](https://motion.dev/docs/react), [21st community](https://21st.dev/community/components) and [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill). The sidebar is original local code; no unverified licensed catalogue snippet was copied. Pro Max was not installed. The preferred CGTrader listing is paid and no owned/licensed asset was available; three Sketchfab download/licence checks could not be verified. The detailed original procedural model therefore remains local, with no runtime download. Dependencies retain their own package licences; this does not establish a repository-wide licence.

## Evidence and remaining integration work

See [verification](VERIFICATION.md), [frontend-only audit](docs/frontend-only-audit.md), [rating methodology](docs/condition-rating-methodology.md), and [future contracts](docs/future-capability-contracts.md). Historical `COVERAGE.md`, `MAINTENANCE-INTEGRATION.md`, `ROLLUP-REVIEW.md` and older `*Browser.cjs` scripts describe the previous starter and earlier revisions; they are not evidence for this rebuild and their old selectors do not represent the new UI. Legacy `api.js`/`demoData.js` and standalone components are retained for reference but are not imported by the new App.

Validation against a running integrated team backend/database, deployment/CORS/auth, physical touch devices, calibrated sensor placement and independent scientific model accuracy remain unverified. The current browser evidence uses an explicit local API test double; it does not claim database persistence or production readiness.
