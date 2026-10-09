# Frontend coverage — 9 October 2026

This update is local on `codex/personc-maintenance-integration` (published base
4941d2f / draft PR #12). This frontend update is committed locally for review;
it has not been pushed or added to PR #12. No merge, deployment or teammate
message was made. Personal environment settings remain local.

| Area | Evidence and remaining work |
| --- | --- |
| Local backend telemetry | User manually confirmed six chronological simulator readings, matching latest/final reading, configuration1/1000kVA, voltage/current/oil/ambient and missing oil level. January timestamps are synthetic; analytics was pending. |
| Local backend maintenance | User manually confirmed16 tasks, assignment/start/completion, readonly completed/cancelled tasks, version1→4 history, prototype demo_header attribution and persistence after reload. Prior isolated-combined-checkout verification is documented in MAINTENANCE-INTEGRATION.md; this is not merged-main maintenance verification. |
| Demo-only | Fleet/Transformer/Alerts fixtures, confidence assessment, two fixed what-if curves and browser-storage Maintenance. User confirmed scenario comparison and demo task prefill/assignment/completion persisted in that browser. None establishes production analytics, cross-browser storage or backend identity. |
| Frontend supported now | Backend readings retrieves analytics for its exact latest reading through GET /api/v1/telemetry/{id}/analytics. No older completed result or fixture is substituted for pending/failed latest data. Model/result versions, UTC measurement/storage clocks, availability/reasons, units and parameter provenance are visible. Reload checks status; API errors leave readings usable. |
| Contract still needed | Health/risk, numerical confidence, winding/oil forecast horizons, fault/RUL and computed what-if API. Current main supports electrical metrics and simplified uncalibrated top-oil estimate/residual only. B's thermal-demo branch supplies assumed coefficients/fresh-run instructions, not new output APIs. |
| Deferred | Phone backend connectivity/firewall, shared deployment, production identity and independent physical calibration. No LAN address or machine setting is shared here. |

## Contract decisions

Reviewed main's docs/contracts/analytics-contract.md, backend API/Pydantic
schemas, worker-output.schema.json and executed sample. Also inspected remote
feature/personb-twin-analytics and feature/personb-thermal-demo, including B's
thermal-demo handoff. Envelope1.0.0/result stored-reading-result-1.1.0 are the
supported frontend versions. Actual zero is preserved; null, nonfinite and
non-available values stay unavailable. Bootstrap and missing coefficients do
not become predictions. Residual is observed minus predicted, in °C; it is not
a fault diagnosis. Assumed coefficients remain visibly assumed.

The authoritative backend maintenance implementation remains C's
BackendMaintenance with maintenanceApi/maintenanceAdapter, mounted as the
Backend maintenance screen. D's five-file #10 mount must not be installed
alongside it; retain #10 on persond until backend and required C changes reach
main, then reconcile/replace that proposal in review. Task list uses items/limit/
offset (20 per frontend page), history is separately paginated. UI labels map
to open/in_progress/completed/cancelled; returned version/updated_at are retained.
Owner is a display name; X-Demo-Actor is prototype identity. Terminal states
are readonly, completion/cancellation require notes. HTTP409 refreshes the
saved task, preserves the draft and requires explicit review before retry.

Merge order from the 9 October repository inspection: #1 frontend starter → #5 telemetry API follow-up → #12
C maintenance integration. #5 is required for #12's registry/telemetry services,
not superseded by #1. D #9 is a separate backend prerequisite for maintenance
browser integration; it can be reviewed in parallel. #9 conflicted at that inspection
with main and needs D's resolution. No PR is merged here. #1's previous README
conflict is already resolved; #1/#5/#12 were mergeable at that inspection. #10 remains
draft on persond. This local analytics update is not yet in #12.

## Validation boundaries and next improvement

20 frontend unit tests, lint and production build passed for the reviewed local
analytics change. Analytics tests use the repository's labelled stored sample;
they establish mapping, not fresh model execution. The subsequent actual API
verification is recorded below. Earlier database/workflow results and user
manual evidence remain separate. Headless browser checks with labelled API
fixtures passed: demo wording, completed metrics/provenance, pending clearing
a previous result and HTTP503 leaving telemetry usable. No database was mutated
by those fixture checks.

Stored-analytics browser verification against the fresh thermal demonstration
is complete. A practical next improvement is history navigation (scroll/focus
the opened history),
which addresses the user's observed below-list discoverability issue. Report
export is optional scope to agree later; no export implementation is added.

## Unsent request for Person B

The stored electrical/top-oil API is connected locally. Please confirm whether
you plan supported health/risk, oil/winding forecasts, fault diagnosis or RUL.
For each supported output, provide the route/envelope, units, UTC measurement
and forecast times, provenance/confidence meaning and pending/unavailable/error
semantics. For computed what-if, please supply the POST route, exact asset/run/
configuration references, scenario inputs (units/ranges), response time grid and
baseline/alternative fields. Until agreed, those dashboard views stay labelled
demonstrations. No message has been sent.


## Follow-up actual thermal verification

The isolated backend was restarted without environment or migration changes.
Current main's stored analytics implementation is present. B's documented helper
was run as an exported generated artifact, preserving original ratings and
configuration1 while adding returned configuration2 and a fresh simulator run.
Six completed results were verified: bootstrap null prediction/residual, five
subsequent finite predictions/residuals, measurement dt60s. Baseline configuration
and old telemetry were preserved. The worker also processed the old six pending
jobs, retaining their data. Actual Chrome Backend readings at the documented
loopback5173 origin showed the exact API values, clocks, units and assumed
provenance; reload passed without page errors. This supersedes the previous
port8000-unavailable observation, which describes the earlier check only.

This is isolated combined-backend verification, not merged-main maintenance
verification, production forecast validation or independent calibration. The
existing5174 process/settings were preserved. No phone troubleshooting or
teammate message was performed. Local details/evidence are in ignored
LOCAL-INTEGRATION.md. Review added mismatched-reading rejection and an unavailable
result test that retains usable electrical metrics without inventing thermal
values. This reviewed frontend change is committed locally; no push or merge made.

## Completed manual browser and provenance checks

The user confirmed completion of the manual browser and provenance checks on
9 October 2026. These are recorded separately from the automated Chrome/API
checks above: Backend readings displays the stored thermal result for the fresh
simulator run, while synthetic measurement timestamps and assumed thermal
parameter provenance remain explicit. Completion confirms local presentation;
it does not establish calibrated model accuracy or production functionality.

Final review is scoped to frontend source, tests, package test script and portable
documentation. Environment files, ignored local integration notes, generated
backend evidence/database files and the unrelated Date.now()) file are excluded
from the commit. Phone testing and shared deployment remain deferred.
