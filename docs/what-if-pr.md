Add server-resolved immutable What-if state and constant-load top-oil API

The frontend's prototype What-if request has no supported backend endpoint, and
the worker cache is mutable. Add POST /api/v1/assets/{asset_id}/what-if with strict
named Baseline/Reduced load segments and server-selected current state, plus an
opaque immutable state reference for repeatable comparisons.

W001 extends main's D004 and adds protected snapshots without rewriting existing
records. Capture the current fenced watermark state only when its exact stored
result/config/model bindings agree. Reuse B's pure healthy-model scenario functions
with model1.0.1 pinned; support equal horizons up to24h, equal ambient and reduced
load <=baseline. Return bounded aligned points, initial-inclusive peaks, analytic
explicit-limit crossings, null availability reasons and reduced-minus-baseline
final difference. No worker advancement, jobs, alerts, cooling intervention,
health/confidence or model upgrade. Failed calculations roll back captures.

Validation:268 backend tests passed, including46 isolated PostgreSQL API tests;
fresh/populated upgrade preservation and metadata checks passed. Actual dedicated
HTTP verification and Node fetch/React chart rendering passed. Current frontend
35 tests, lint and build passed without frontend source/lock changes.

See docs/what-if-api-contract.md, docs/person-c-what-if-handoff.md, structured
evidence and exact synthetic request/response/error examples. The prototype UI
still requires C's wiring. Independent incident migrations need a reviewed join
if combined. Draft for teammate review; no deployment or automatic merge.
