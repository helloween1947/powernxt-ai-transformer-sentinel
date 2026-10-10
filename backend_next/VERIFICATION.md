# Replacement backend verification · 11 October 2026

Built independently in `backend_next/`, on local branch `feature/powernxt-clean-backend`. No imports from, or edits to, the existing backend, analytics or integration modules.

## Automated checks

- Backend: 28 tests passed, zero failed/skipped. One dependency warning recommends httpx2 for newer Starlette TestClient; HTTP tests passed with the pinned httpx version.
- The tests cover ratings/configuration validation and persistence, SQLite restart, immutable older configuration results, run/source/asset isolation, simulator background advancement and stopping, seeded generation, all five injected conditions, zero/missing inputs, threshold boundaries, thermal bootstrap/reset, CSV atomicity, XLSX mapping/Excel dates, active-sheet preview, corrupted files, invalid mapping, nonfinite/out-of-range values, duplicate/future/DST timestamps, request/file size limits, history pagination/date filtering and duplicate device identities.
- A 205-row import with 205 overheating breaches verifies entire-dataset counting beyond the 100-row API page and 200-item preview cap.
- The cross-language test creates actual API responses and executes the existing frontend telemetry/analytics adapters, capability discovery and four-factor condition policy against them. All four factors bind to the correct reading/configuration/source.
- Frontend: all 79 existing tests pass. ESLint and production Vite build pass. `git diff --check` passes.
- Build sizes: CSS 71.95 kB / 14.61 kB gzip; initial JS 579.14 kB / 181.81 kB gzip; lazy scene JS 937.17 kB / 249.16 kB gzip.

## Running-browser checks

Used the actual backend at localhost:8001 and frontend at localhost:5173, not the earlier frontend contract test double.

- Set the connection through the UI and registered transformer TX-01.
- Started the normal synthetic feed; the frontend retrieved completed real backend results without provenance/adapter errors. Later readings had new IDs and changing electrical values.
- Changed the feed to overload and observed capacity loading about 150%, with retained source/run identity.
- Uploaded `examples/transformer-readings.csv` through the file chooser. All ten canonical columns mapped automatically. The frontend imported six rows and showed exactly five findings: overload, overheating, low oil, phase imbalance and undervoltage, each with its measured value, configured limit, time and explanation. The whole uploaded run, rather than a recent-time filter, became selected.
- Refresh testing found that registry/capability reloads could unmount the controls and clear the upload report. Matching scopes now retain their data during refresh; changing origins/assets/streams still invalidates prior data. Retested import and manual refresh: the report stayed visible with no errors.
- Restarted the actual server and refreshed the frontend. Registered asset, saved uploaded run, measurements and findings remained available.
- Selected the oldest retrieved synthetic reading while the background feed continued beyond its history window. The header, inspector, measurements and chart stayed on that reading. Returning to latest resumed the advancing feed. Inspection pins only the bounded retrieved snapshot and resets when its asset/stream/query scope changes. Background polling retains the page layout rather than inserting a loading row on every interval.
- Checked the 390×844 mobile viewport: no document horizontal overflow; mapping inputs fit the page and result tables scroll inside their container. Restored normal desktop viewport.

Evidence screenshots are stored in the task's visualization directory, separately from runtime/source data. Physical sensors, authenticated multi-user deployment, independent fault-label evaluation and measured frame-rate/load benchmarks have not been tested.
