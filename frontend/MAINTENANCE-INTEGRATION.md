# C frontend maintenance integration

**Current combined verification:** see [D integration report](../docs/integration-verification.md).
The backend now has permanent D004 and passed combined checks. The graph and
PR-status statements below retain C's earlier review snapshot. C's component
and services remain the authoritative maintenance implementation.


## Review and merge sequence

1. Review and merge **PR1** (`feat/frontend-setup`) into main. Its README
   conflict is resolved by retaining starter guidance plus shared scope,
   backend health and CORS documentation. The original scaffold is reused.
2. Retarget **PR5** (`feat/frontend-api-integration`) to main after PR1 lands,
   recheck its net diff, then review and merge it. PR5 remains the telemetry/API
   follow-up: Backend readings, asset/stream/history adapters and tests,
   responsive fixes, HTTP-mobile demo task-ID fallback and frontend documentation.
   It is not independent of PR1, does not supersede PR1 and is not required to
   merge PR1. Keep its existing base `feat/frontend-setup` until PR1 lands.
3. **PR12**, this focused C maintenance follow-up, is stacked on
   `feat/frontend-api-integration`. After PR5 lands, retarget it to main and
   inspect the net diff again, especially after squash merges. Merge it only
   after the needed C frontend is in main and D's backend **PR9** has landed
   with a migration graph compatible with current main. Frontend review can
   proceed before backend deployment.
4. Keep D's **PR10** targeting `persond` until both PR9 and the required C
   frontend reach main. C has not changed that base or any D branch. Coordinate
   with D before retargeting or revising that proposal; never merge it into
   persond merely because it is temporarily stacked there.

No PR was merged as part of this work. Shared browser testing must use the
final reviewed combined revision rather than assuming these drafts are main.

## Authoritative component and mount

Person C selects the existing C implementation as the frontend proposal:

```text
src/App.jsx
  import BackendMaintenance from './components/BackendMaintenance.jsx'
  screens includes 'Backend maintenance'
  screen === 'Backend maintenance' renders <BackendMaintenance />

src/components/BackendMaintenance.jsx
src/services/maintenanceApi.js
src/services/maintenanceAdapter.js
```

It mounts directly under `main`, independently of fixture dashboard loading.
Fixture transformer/scenario controls and fixture dashboard details are hidden
on backend screens. **Maintenance** continues to mean browser-local demo
tasks; **Backend maintenance** requests the backend and never falls back to
localStorage. Keep `VITE_DATA_MODE=demo` for the original dashboard.

This is C's documented choice for review, not a claim that D has approved it.
The handover asks D to acknowledge the replacement before final integration.

D's five-file PR10 was reviewed against this dashboard:

| D proposal file | Disposition in C implementation |
| --- | --- |
| frontend/src/components/BackendMaintenance.jsx | Replaced by C's existing component at the same path, including failed-conflict-reload recovery and creation beyond a full page. Do not copy both versions. |
| integration/frontend/maintenanceClient.mjs | Replaced for the browser by src/services/maintenanceApi.js. No frontend import outside frontend/. |
| integration/frontend/maintenanceClient.test.mjs | Replaced by tests/maintenance.test.js and browser checks. |
| integration/frontend/verifyDashboardBrowser.cjs | Replaced for C verification by tests/browserIntegration.cjs, additionalBrowserChecks.cjs and paginationBrowser.cjs. |
| integration/frontend/dashboard-integration.patch | Its import/navigation/render mount is already implemented in App.jsx. Do not apply this patch again. |

D's `integration/frontend/maintenanceAdapter.mjs` can remain for D's standalone
backend verifiers. It is not imported or duplicated as another runtime browser
adapter. C's single runtime adapter additionally validates sample provenance,
version, actor, pagination, transitions and required notes. D's mapper uses
capitalized UI statuses; C deliberately keeps exact API statuses internally and
maps them to labels only when rendering. Both map to the same backend contract.

## Contract and operator behaviour

All requests use the same `VITE_API_BASE_URL` as Backend readings, with no
`/api/v1` suffix in that base. Restart Vite after changing it. Use a URL the
browser can reach and allow its exact origin in backend CORS, including PATCH,
Content-Type and X-Demo-Actor.

- POST/GET `/api/v1/maintenance/tasks`, GET/PATCH `/api/v1/maintenance/tasks/{id}`,
  GET `/api/v1/maintenance/tasks/{id}/history`.
- **Both task list and history** return `{items, limit, offset}`. Actual D route
  definitions accept limit 1â€“100 (default 20), offset >=0 (default 0). Task lists
  optionally filter by `asset_id`; history does not use an asset filter. The UI
  uses 20-item pages and keeps backend ordering. With no total count, a full
  page permits Next; the next page may be empty.
- Registered asset selection uses the backend registry, not fixture asset IDs.
  Title/action maps to `action`, assigned person to `owner`, sample summary to
  `alert.summary`, and asset identity to `alert.asset_id`/response `asset_id`.
- Creation requires explicitly selected sample provenance and a `sample-...`
  alert ID. Real detector alerts and forecast-generated recommendations are not
  accepted. Blank initial owner becomes null; new tasks are open at version 1.
- Response `owner`, `notes`, `version`, `created_at`, `updated_at` are retained.
  PATCH uses the saved `expected_version` and retains the returned version.
  Action/title is not sent as a mutable PATCH field.
- Exact statuses are `open`, `in_progress`, `completed`, `cancelled`. Display
  labels are Open, In progress, Completed, Cancelled. Starting needs an owner;
  in-progress tasks cannot be unassigned. Completion requires nonblank notes in
  that request; cancellation from open/in_progress requires a nonblank reason.
  Direct open-to-completed and reopening are blocked. Terminal tasks are read-only.
- PATCH alone adds `X-Demo-Actor` and JSON content type. Actor is a trimmed
  nonblank display name, <=100 characters, without control characters. It and
  owner are prototype display names, not authentication or a user registry.
- On 409 the editor retrieves GET task detail, shows latest saved fields and
  retained draft together, blocks saving and requires an explicit review action.
  There is no automatic retry. If detail retrieval fails, retry retrieval without
  losing the draft. If the latest task is terminal, the draft cannot be submitted.
- Loading, empty pages, validation, network/API errors and success messages are
  visible. New creation remains visible even beyond the first oldest-first task
  page. Explicit page reload/navigation discards unsaved page drafts and is labeled.
  Task completion never recovers or acknowledges an alert.

## Checks and current shared backend blocker

Run from frontend:

```text
npm ci
npm run lint
npm run build
npm test
```

Optional browser scripts require separately installed Playwright, an installed
Chrome browser (`BROWSER_PATH` where supported), and a reachable demonstration
backend. Set `NODE_PATH` to that development package location, `FRONTEND_ORIGIN`,
`BACKEND_ORIGIN`, `DEMO_ASSET_ID`/`DEMO_RUN_ID` from that backend and
`BROWSER_ARTIFACT_DIR` outside tracked source. Never copy a teammate's IDs without
checking them. They create labeled sample records; repeat runs retain them.

Browser checks cover real workflow requests, versions, competing-write 409,
explicit review, required notes, terminal rejection, history/pagination and
refresh persistence. Intercepted fixture checks are separately labeled and cover
null/zero, failed 409 retrieval and network errors. Mobile viewport emulation
does not establish physical-phone reachability. See the PR description and
handover for results on the exact reviewed revisions.

Current main `9d2f9cd` added analytics worker migration `d730a91b4c22`, with parent
`ce21c3b8140a`. D `087a884` has `d003_audit_maintenance`, joining that audit parent
and D002. The new combination again has **two heads**, d730a91b4c22 and
d003_audit_maintenance, plus router/model registration conflicts. In the local
verification checkout only, both registrations are retained and existing heads
are applied to a dedicated demo database. These are compatibility experiments,
not a published backend fix or merged-main verification. A/D must reconcile and
publish this newer graph and resolve registrations before shared deployment.
C's frontend PRs contain no D backend files or backend conflict resolution.

Completed analytics are not consumed by these screens. Main now has a worker,
but C does not claim that it ran for the demonstration or that its output,
genuine incident delivery or trusted identity is connected to maintenance.

## Verified review snapshot â€” 9 October 2026

| PR | Current base / branch | Review state |
| --- | --- | --- |
| [#1](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/1) | main / feat/frontend-setup | Open, conflict-free, backend CI passed at 72acc3b. |
| [#5](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/5) | feat/frontend-setup / feat/frontend-api-integration | Open, conflict-free, nine-file telemetry follow-up at e87a885. |
| [#9](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/9) | main / persond | Draft, conflicted against current main at 087a884; A/D reconciliation required. |
| [#10](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/10) | persond / codex/persond-dashboard-mount | Draft, five-file proposal at 094c364; base and branch unchanged. |
| [#12](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/12) | feat/frontend-api-integration / codex/personc-maintenance-integration | Draft, focused C maintenance alternative; source commits 708ab13 and 3aaedcc. |

All C PR diffs contain frontend files only; main is an ancestor of the updated
C branches, and D backend code is absent from their diffs. No force-push or PR
merge occurred. Local environments and browser records were preserved; the
accidental Date.now()) file and machine-specific local notes/helper were excluded.

Checks actually rerun on the resolved branches:

- Starter: npm ci, lint and build passed. GitHub Backend Test Suite (Python 3.12)
  passed at 72acc3b ([run](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/actions/runs/37915848879)).
- API-only branch: npm ci, lint, build and all six telemetry adapter tests passed.
- Maintenance branch: lint, build and npm test passed, 14 tests total (six
  telemetry and eight maintenance). C/D mapper comparison passed: assigned
  creation/PATCH payloads are identical; unassigned creation uses explicit null
  in C and omitted optional owner in D, both supported by TaskCreate.
- Actual Chrome against current main 9d2f9cd plus D 087a884, with local-only
  registration resolutions and dedicated demo database: telemetry, maintenance
  workflow, owner/required-note validation, 409 review, terminal rejection,
  history, refresh, actual offline/restart persistence and CORS passed.
- Real task/history browser pagination: 22 records paginated 20/2 and newly
  created tasks remained visible beyond the first page. Separate intercepted
  fixtures passed null/zero, failed 409 retrieval and terminal-latest checks.
- 390px touch-browser emulation passed demo UUID fallback, saving/persistence
  and layout; the physical phone was not tested. No uncaught browser page errors.

PR5/PR12 have no reported GitHub check runs on their temporary stacked bases;
local checks are evidence, not a claim of frontend CI. Recheck CI when retargeting
to main. Current combined backend's normal upgrade head is blocked by its new
two-head graph; the earlier 45-test backend result was on the previous main/D003
combination and is not a result on this newer graph.

## Ready-to-send handover to D

I resolved C's frontend prerequisites and published normal updates. PR1's
README conflict is fixed at 72acc3b while retaining shared scope/health/CORS
guidance; it is now conflict-free and backend CI passed. PR5 remains the separate
nine-file telemetry/API follow-up at e87a885, based on the corrected starter.
New draft PR12, codex/personc-maintenance-integration, contains C's tested
maintenance screen/service/adapter and documentation. No PR was merged and your
branches/PR10 base were not changed.

Exact sequence: PR1 into main; retarget/review PR5 to main and merge; retarget
PR12 to main and inspect its net diff; merge/deploy PR12 once PR9 is landed with
compatible migrations. PR9 can be reviewed in parallel. Keep PR10 targeting
persond until PR9 and the necessary C frontend have reached main.

C selects App.jsx's separate Backend maintenance mount with C's component and
src/services/maintenanceApi.js plus maintenanceAdapter.js as the authoritative
browser implementation. It replaces your five-file proposal. Do not apply the
mount patch or duplicate your component/client alongside it. Your standalone
mapper can remain for backend verification. Please acknowledge this replacement
and revise/drop redundant PR10 content on your branch before final integration.

The contract is title->action, display owner, retained notes/version/updated_at,
lowercase API statuses with display labels, items/limit/offset for both lists,
20-item UI pages and optional task asset filter. PATCH sends expected_version
and X-Demo-Actor; 409 retrieves the latest task and retains the draft, blocks
save, then requires explicit operator review. Failed refresh can be retried;
terminal tasks cannot be resubmitted. Start needs an owner; completion/cancel
need notes; no direct completion/reopening. Alerts are labeled samples and actor
identity is explicitly prototype. Browser-storage tasks and forecasts stay demo.

Starter/API lint/build passed; API six tests passed; maintenance lint/build and
14 tests passed. Chrome workflow, conflict review, real 20/2 pagination, refresh
and actual backend offline/restart checks passed in an isolated combined
checkout, not merged main. Fixture and mobile-emulation evidence is identified
separately; physical phone and final shared deployment remain unverified.

Main has now advanced to 9d2f9cd with worker migration d730a91b4c22. PR9 is
conflicted in backend/app/api/__init__.py and backend/app/models/__init__.py, and
the combined graph has heads d730a91b4c22 and d003_audit_maintenance. A/D must
publish registration resolutions and a reviewed graph merge before shared
upgrade head/browser testing. Local preview resolutions are not in C's PRs.
Frontend PRs are ready for human review; shared testing is ready once that
backend revision is published, dependencies land and the reachable API URL/CORS
origins are confirmed. No completed analytics or trusted identity is claimed.
