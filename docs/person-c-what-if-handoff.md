# Person C — initial backend What-if handoff

Model adoption follow-up: [A’s version dispatch and handover contract](person-a-model-102-adoption.md) supports immutable 1.0.1 and 1.0.2 states. Earlier verification below remains tied to its original tested source; see the separate adoption evidence for fresh checks.

A's branch `feature/persona-what-if-api` starts at main
f52f56515c38fce55451fd499be81ef2508e6677. Reviewed B scenario source:
f668a21dcf88605d7fcff4996282185bc796740c. No teammate branch, development
service/database, environment file or frontend source was changed.

POST `/api/v1/assets/{asset_id}/what-if` now implements only **Baseline** and
**Reduced load** constant-input conditional healthy-model top-oil estimates.
The current main prototype client `/what-if` with `{assetId, alternative}` does
not match this API. Do not claim the existing What-if screen is already wired.

Exact schema, state rules, errors and numerical semantics:
[contract](what-if-api-contract.md). Full actual isolated request/response/error
examples: [verified synthetic execution](../data/sample/what-if-verified.json).
They contain real test-generated references; those IDs are not production defaults.

## C's implementation steps

1. Select a registered asset and explicit measurement source/run. Keep device
   live (null run), simulator and replay runs separate. The initial POST omits
   state_ref and the server captures the current committed worker watermark
   state. It does not select the latest registered configuration or pending
   telemetry. Display the returned measurement timestamp/config/model and avoid
   implying the snapshot is current wall-clock physical truth.
2. Send exactly baseline/reduced_load objects with duration_s, thermal_load_pu
   and ambient_temperature_c. Use equal durations in (0,86400], load0–10 pu,
   ambient−50–80 C; reduced load <= baseline and equal ambient. Bounds are model
   computational bounds, not approved operating ranges. Booleans/nonfinite values,
   numeric strings, future measured oil, cooling factors, state JSON, coefficients
   and other unsupported fields are rejected. Remove/disable Restore cooling for
   this API; no fault-aware intervention is available.
3. For an intentional repeat/change of inputs from the same origin, send the
   returned opaque state_ref. Both curves always share the same immutable state
   and configuration. To explicitly refresh the origin, omit it again and display
   the newly selected timestamp. Do not use reading/latest result IDs as substitute
   state references; do not reconstruct historical state from current cache.
4. Plot estimated_top_oil_temperature_c against elapsed_s. Both point arrays
   align, include t=0 and the horizon and have at most97 points each. The reference
   [browser-compatible client/adapter](../integration/what-if-client.mjs) shows
   request/error handling and maps points to the existing TrendChart shape.
   Rendering timestamps are origin+elapsed; label them **projected time** rather
   than measurements. JavaScript Date display has millisecond precision; keep
   backend elapsed seconds for exact values and crossing display.
5. Display final/peak and final_temperature_difference_c as estimates. Negative
   difference means reduced_load_final minus baseline_final is lower, not that
   risk/fault severity decreased. Peak includes time zero and is exact for the
   model's monotonic constant segment. Crossing is analytic rather than the first
   plotted point; do not infer it from chart samples or round before comparison.
6. Keep all three crossing statuses distinct: crossing (including time0),
   no_crossing_within_horizon (null time), unavailable (null time/reasons, e.g.
   missing configured limit). Never coerce null to zero. Only the bound registry's
   explicit top-oil limit is used, with provenance; no default warning threshold.
7. On versioned 404/409/422/503 errors, show the bounded code/reasons and clear or
   explicitly retain any old chart as historical. Do not fabricate successful
   curves. Missing model coefficients, invalid latest state, identity mismatch or
   arithmetic failure are errors. Missing limit still permits temperatures, with
   unavailable limit checks. Do not add health/confidence/fault/maintenance claims
   or genuine task creation based on this response.

The adapter is a reference module, not a modification of C's frontend ownership.
Copy/adapt it into C's reviewed client when wiring the UI. It accepts a cancellation
signal and preserves machine-readable error and null crossing statuses. Avoid
the old prototype's demo fallback for a failed backend calculation.

## Actual verification

Executed on Linux/Python3.12/PostgreSQL16, using a new isolated database/container,
not the preserved development API. Tests migrate private schemas/databases only.

- 268 backend tests passed, including46 new PostgreSQL What-if HTTP tests. Existing
  sample maintenance/worker tests remain passing. No skips;272 dependency warnings.
- Fresh database and all existing main migration paths passed. A populated D004
  worker dataset survived W001 unchanged. Alembic reports one W001 head and no
  model/schema drift. Snapshot UPDATE/DELETE and contradictory origins are
  rejected; populated downgrade is refused.
- Actual HTTP API on dedicated port15445 plus fenced worker verification passed:
  common initial state, exact result/config reference, calculation crossing,
  unchanged worker/result/job rows around forecasts, immutable reference after
  worker advancement, missing limit/null semantics, and seven bounded error cases.
- Node fetched those actual responses and rendered C's unchanged React TrendChart
  through the reference adapter. It checked aligned two-series values, endpoints,
  null/crossing status preservation, unsupported-unit rejection and HTTP errors.
  This is server-side React rendering, not a browser run or completed UI wiring.
- Current frontend suite35 passed; lint and production build passed. Lockfile and
  frontend source unchanged. npm initially failed because its default cache was
  unwritable; retry with a writable cache succeeded with integrity checks intact.
- Targeted Ruff, B scenario-function AST equivalence and final whitespace diff
  checks passed. B's forecast bodies/formulas are unchanged; imports/constructor
  extraction adapt to existing model1.0.1, with source hashes recorded.

The verifier initially used the registry sample without thermal coefficients;
it correctly returned409. Verification then reused the existing worker test's
explicit assumed coefficients40/180/5/0.8, without changing or tuning a live asset.
The no-limit sample also needed matching provenance removal; this was corrected.
All final examples come from the successful final run. No field accuracy,
Windows/browser checks, cooling intervention or deployed UI is claimed.

Structured run/source fingerprints: [evidence](what-if-verification.json).

## Repeat on an isolated test environment

Create a separate PostgreSQL test database, ending in `_test`, and set TEST_DATABASE_URL
to that database for tests. Use backend/requirements-dev.txt and the repository's
Python version. Do not run these migrations against preserved development data
without the normal reviewed rollout.

```powershell
$env:TEST_DATABASE_URL = '<isolated PostgreSQL *_test URL>'
python -m pytest backend/tests -q
# Dedicated API: use a DIFFERENT loopback port and DATABASE_URL for the test DB.
$env:DATABASE_URL = $env:TEST_DATABASE_URL
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini check
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 15445
# In a second shell with the same isolated database value, repository root:
python -m integration.verify_what_if --base-url http://127.0.0.1:15445 --database-url $env:TEST_DATABASE_URL --output "$env:TEMP\what-if-verified.json"
Push-Location frontend
npm ci --cache "$env:TEMP\powernxt-npm-cache" --no-audit --no-fund
npm test
npm run lint
npm run build
Pop-Location
node integration/verify-what-if-client.mjs http://127.0.0.1:15445 "$env:TEMP\what-if-verified.json"
```

The verifier creates unique synthetic test assets/configurations/readings and
retains them. It performs no migrations or restarts and rejects the development
API ports and non-test database names. Test URL/credentials are local environment
bindings; do not commit `.env` or credential values. Windows commands are supplied
for C/D; they were not executed on Windows by A.

## Review and remaining integration decisions

Model bounds, continuous behavior and immutable retrieval were established from
code and implemented; there is no unresolved computation dependency blocking this
initial API. Human B/C review should confirm A's documented product choices:
equal ambient, eligible bootstrap, explicit historical captures and96-interval
sampling. Deployment and C's UI wiring remain separate, with model1.0.1 pinned.

W001 extends D004 on current main. The independent unmerged A incident branch
adds A001/A002 from D004; before combining both, inspect the graph/schema and add
a reviewed join. This What-if branch does not rewrite those migrations or include
the incident implementation. No merge, deployment, messages or changes to live
parameters were performed. Repository policy still requires teammate approval
and passing hosted CI before merge.
