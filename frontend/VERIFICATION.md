# Frontend-only rebuild verification · 10 October 2026

## Scope

Followed `PowerNXT_Codex_Frontend_Only_Master_Prompt.md` including the final navy/steel-blue design direction. This iteration modifies only `frontend/**`. SHA-256 comparison of all 144 monitored files outside frontend found zero changes. Existing earlier-turn and user untracked files are preserved. Local branch/HEAD remain `feature/personb-detector-orchestration` / `d86b210`. No backend, analytics, integration, environment, database, deployment or remote Git changes occurred in this iteration. See [audit](docs/frontend-only-audit.md).

## Final automated results

| Check | Result |
|---|---|
| `npm test` | PASS · 79 tests, 0 failed, 0 skipped |
| `npm run lint` | PASS · no errors or warnings |
| `npm run build` | PASS · production Vite output |

Tests cover rating boundaries for all four candidate factors, both coverage gates, genuine zero, missing/bad/suspect evidence, duplicate factors, unsupported units/rules/provenance, asset/source/run/reading/time/configuration binding, unknown sources/modes, future/stale timestamps, sample isolation, measured-versus-estimated thermal inputs, deterministic immutable policy, independent breaches with high/absent aggregate scores, historical record isolation, complete runtime route/method discovery, analytics request suppression, transport latency/clock ordering, solid theme/nav/state contrast, strict analytics/schema/model provenance, quality gaps, bounded concurrency/caching/polling, cancellation and stale response guards, pagination/date scope, safe CSV export, maintenance transitions and HTTP 409 behavior.

Production output: 70.41 kB CSS / 14.33 kB gzip; 566.85 kB initial JS / 178.17 kB gzip; 937.17 kB lazy scene JS / 249.16 kB gzip; 6.87 kB future-contract note. No external mesh or texture payload. Demand rendering and mobile quality caps are implemented; these sizes are not measured frame-rate claims.

## Actual browser checks

Motion refinement: unified 200 ms control easing, 240 ms view fades and 360 ms spatial motion; page navigation overlaps exit/entry instead of waiting on an empty view. Category backgrounds and tab indicators slide; condition-group content fades. Dialogs use a 240 ms opacity/8 px vertical entry and a 160 ms close fade; no shared bubble projection or text scaling remains. Numeric typography uses tabular figures and active controls keep the same font weight. Orbit damping and eased camera reset render on demand; the first reset frame ignores idle time. Sidebar resizing retains camera orientation and relative zoom. Chart cursor motion is immediate during dragging and short during discrete selection. Reduced motion disables CSS motion, inspection entry translation, camera damping/reset interpolation and rating arc animation. Values are never tweened through invented intermediate readings.

The earlier general motion pass verified all eight screens without overflow or application exceptions, all four callout filters, tab selection, measurement/rating dialog open/close and focus restoration, damped rotation and exact camera reset, sidebar expand/collapse preserving the axes, chart dragging synchronized to reading R-20 across header/inspector/time rail, confirmed CSV download with feedback, condition-group fading, and a 390×844 light-theme bottom sheet with 44 px category controls. Desktop dark theme was restored and the viewport override cleared. No OS reduced-motion preference was changed; reduced-motion entry and reset progression are covered by two additional unit tests.

Latest bubble correction: reproduced a transparent source shell while text kept floating, conflicting opacity transitions, corner-to-corner movement during category filtering, and a close/reopen race that dismissed the next inspection. Removed shared-layout morphing, ambient float, perspective transforms and the unused pause control. Bubbles now mount in fixed slots with one 160 ms opacity reveal and retain their native solid background. ResizeObserver measures each bubble edge for its connector. Closing dialog layers stop intercepting input; stale outside events cannot dismiss a reopened dialog. Focus restoration uses preventScroll, and backdrop clicks dismiss normally.

This correction passed eight consecutive category changes, twelve repeated measurement open/Escape cycles across all four desktop bubbles, three hide/show cycles (0/4 callouts), backdrop dismissal without vertical scrolling, and rating-dialog focus handling. No duplicate or overlapping callouts were found; bubble transforms were `none` and connector edge errors were 0 px, including after native 3D orbit. Camera reset restored all XYZ endpoints exactly after the eased transition completed. The mobile viewport override was 390×844; all four filters showed two callouts with no horizontal overflow and a readable light-theme bottom sheet. Desktop dark theme and the normal viewport were restored. Inspected browser error logs were empty. Two additional regression tests cover deferred outside events across reopening and absent/invalid clocks. Screenshots below are from the corrected implementation; no frame-rate benchmark or physical-device test is claimed.

Latest refinements: the XYZ indicator projects world directions into camera space, updating during orbit while remaining independent of zoom. Native browser drag changed its SVG axis endpoints; camera reset restored all three endpoints exactly and disabled rotation. Two new math tests check front/side directions and orbit, zoom, translation and reset behavior. The category selector uses a 16 px container radius and the shared 10 px control radius. All four categories were clicked and their corresponding callouts verified; the desktop page had no horizontal overflow.

Used the running app at `http://127.0.0.1:5173/` through the in-app browser. The final responsive matrix used exact DOM-reported CSS dimensions 360×800, 390×844, 768×1024, 1024×768, 1366×768 and 1920×1080 in both light and dark themes. All twelve checks showed zero document horizontal overflow; callouts were two on phones and four on larger viewports. Phone scene controls measured 44×44 px; tablet controls were subsequently enlarged to 44×44 px. Tables/evidence rails scroll inside their containers.

Two screenshot critique/refinement passes were completed. The first corrected crowded callout text and excessive vertical spacing at 1366×768. The second corrected modal overlay stacking, mobile density, tablet controls, inspector typography and stage framing. Current desktop composition keeps the model and scene controls visible at 1366×768. Mobile sheets fit the viewport, with internal content scrolling.

Verified in the browser:

- Light/dark shell, compact rail, meaningful unavailable/sample states and all eight condition capability groups, including pressure instrument inventory.
- Prominent sample prototype: steady 100/100, overload 25/100 with two separately disclosed breaches, missing oil channel with no numeric score and 35% coverage.
- Chart timeline follow-up: clicks and continuous drags snap to actual retrieved measurement times. Desktop and 390×844 responsive pointer checks synchronized the rail, callouts, inspector, summary and header timestamp. Home, End and ArrowRight, Return to latest, rating changes from 100 to 25 in the overload fixture and selection persistence into Condition explorer were verified. Four new unit tests cover irregular intervals, ties, endpoint clamping, invalid records, missing sensor values and shared measurement/rating identity. The three requested text lines were removed from the compact rating/toolbar; factor provenance remains in the explanation dialog.
- Static model removal: deleted StaticTransformer.jsx, its import, toggle, state and SVG styling. The 3D scene is the only transformer model; WebGL/context failures use a text availability state. At that revision, browser checks confirmed one canvas and four scene controls, label hide/show, pause/resume (the unused pause control was removed later), changed projected anchors after rotation, and exact anchor restoration with rotation disabled after reset. All 73 Node tests, lint and production build passed.
- UI copy cleanup: removed repeated sample/simulation/illustrative/prototype labels, measurement disclaimers, compact badges and empty secondary labels across all eight main views. Twin tabs and measurement/rating dialogs were scanned in the running browser; missing channels and overload breaches stayed visible. Both themes at 390×844 had zero document overflow. Timeline Home/End and shared reading identity still worked. Two presentation tests confirm clean labels retain canonical records, unavailable channels, breaches and raw CSV provenance. A transient HMR render error from a removed icon reference was corrected; the workspace was reloaded and the final views verified. Lint/build and all 73 Node tests passed.
- Time-strip follow-up: the selected record smoothly centers within the horizontal rail on selection changes, with reduced-motion preferences using an immediate scroll. Browser checks covered the final record and reverse chart dragging to sample-19; the selected button was fully visible and centered within 0.21 px, while the page stayed at the same vertical scroll position. Lint/build and all 71 Node tests passed.
- Historical sample selection changes the inspected measurements and rating; Return to latest restores current context. Real-shaped fixture selection binds its own completed result and displays explicit stale device evidence.
- Measurement/rating dialogs show identity, time, source, rule provenance, quality and factors. Escape and the close button restore focus to the source control; mobile measurements open in a bottom sheet.
- Arrow-right moves Electrical to Thermal; Data quality opens reading, processing, channel and configuration evidence.
- Label visibility controls work; the ambient pause control was removed in the latest bubble correction. Measurement callouts remain independent of the 3D canvas. Opt-in drag changes projected anchor coordinates; Reset exactly restores recorded initial coordinates and disables rotation.
- Fleet, incidents, What-if and reports navigation. The 120% preset changes an input only; comparison remains unassessed. Workbook references remain separate from telemetry.
- Actual CSV download was parsed: 25 records, all `Sample UI illustration` scope, with no prototype rating persisted/exported.
- Browser logs showed a dependency `THREE.Clock` deprecation warning; no application exception was observed in the inspected logs. No dependency monkey-patch or warning suppression was added.

## Integration evidence and honest limits

The frontend-only `tests/contractServer.cjs` is an explicit localhost test double, not a deployed backend. It advertises implemented fixture families through `/openapi.json`. Browser checks covered pending latest telemetry versus compatible completed historical analytics, empty stored streams, 404 analytics withholding, task creation, 409 latest-version reload with retained draft and explicit review, nonblank completion-note validation, completed read-only version 4 and its recorded history. Test tasks existed only in fixture memory.

The current workspace backend has asset/telemetry/health routes but no analytics, maintenance, incident or What-if HTTP router. Optional clients are therefore gated by the connected runtime's actual complete OpenAPI route families. Advertised paths do not prove worker health, and payload adapters still enforce supported provenance. Proposed future endpoints are never probed. Health Index, lifespan, ageing, RUL, fault prediction, pressure/leak sensors, authenticated incidents and computed What-if remain intentionally unavailable with dedicated evidence/contract views.

No purchased or third-party mesh was acquired. The detailed original procedural asset is used lawfully; asset research and payload considerations are in [attribution](public/models/ATTRIBUTION.md). Physical touch/keyboard devices, forced GPU context loss, deployment/CORS/auth, integrated team database persistence and independent scientific/sensor validation remain unverified. Reduced-motion handling is implemented in Motion/CSS and policy helpers; no OS accessibility preference was changed for testing.

## Screenshots

Evidence is stored in `/Users/vgnxh/.codex/visualizations/2026/10/10/01a1259d-b607-70b3-9137-c0d5163f11fb/`:

- `powernxt-timeline-scrubbing.jpg` (timeline interaction)
- `powernxt-smooth-timeline-scroll.jpg` (selected time centered in the rail)
- `powernxt-clean-workspace.jpg` (UI copy cleanup)
- `powernxt-3d-only-transformer.jpg` (static model removed)
- `powernxt-refined-bubbles.jpg` (current fixed-position callouts)
- `powernxt-refined-bubble-inspection.jpg` (current independent inspection dialog)
- `powernxt-refined-mobile-sheet.jpg` (current mobile inspection)
- `powernxt-smooth-workspace.jpg` (earlier general motion pass)
- `powernxt-smooth-mobile-sheet.jpg` (motion-refined mobile inspection)
- `powernxt-rounded-selector-linked-axes.jpg` (rounded category controls and camera-linked XYZ indicator)
- `powernxt-v2-desktop-light.jpg`, `powernxt-v2-desktop-dark.jpg`
- `powernxt-v2-mobile-inspector.jpg`, `powernxt-v2-pressure-inventory.jpg`
- `powernxt-v2-no-data.jpg`
- `powernxt-v2-stale-evidence.jpg`, `powernxt-v2-breach-factors.jpg`

See [rating methodology](docs/condition-rating-methodology.md) and [future capability contracts](docs/future-capability-contracts.md).
