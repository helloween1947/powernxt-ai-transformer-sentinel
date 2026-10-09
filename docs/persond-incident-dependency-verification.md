# Incident dependency verification after PR15/21 merge

Inspected main: `f2887902548212c4736ed69e9dd135c537c0d1c6`, 9 October 2026.
Both local checkouts safely fast-forwarded from clean states; existing branches,
sample records and databases were preserved. PR15 merged at this SHA; PR21 merged
at `b955118858ede8382e852f9ca3b96485ed1fd96c`. GitHub review/comment inventories
returned zero entries for each at inspection; the merge itself is confirmed.

## Contract decisions versus runtime readiness

PR15 is now a merged design baseline. Its text still calls itself a proposal
awaiting A/D acceptance and explicitly leaves choices open. We do not treat its
historical status header as proof that nothing was adopted, or merge status as
proof that unspecified decisions or runtime APIs exist. No later acceptance
record was found in the inspected code, PR reviews or issue comments.

The merged design provides a concrete direction: canonical server-issued UUIDv4,
asset/epoch/episode mapping; reading/result/message IDs remain evidence; one task
per incident; sample data retained; task, condition and acknowledgement independent.
It is sufficient to guide dependency checks and D's plan, but not to fabricate
A's physical registry schema, trusted actor or endpoint request/error contracts.

| Dependency | Observed implementation | Remaining action / owner |
|---|---|---|
| Asset/configuration/telemetry/analytics foundation | Present, explicit source/run and immutable result references | A retains ownership; D reuses it |
| Canonical registry and asset mapping | No incident table/mapping/FK target | A implements UUID/epoch/episode registry and authoritative asset/stream binding; B/D review |
| Detector orchestration | A's worker stores analytics, not sustained incident lifecycle | A/B choose worker-integrated versus ordered consumer; model/policy adoption and reset/handover semantics |
| Incident read/evidence/history APIs | No registered paths; local requests return404 | A implements accepted API shapes/errors/cursors and exact evidence references |
| Trusted identity and acknowledgement | No authenticated operator model; X-Demo-Actor explicitly prototype; no ack route | A/D settle actor/authz/version/idempotency contract; A backend; C integration |
| D genuine task migration | No registry revision/type to reference | D follows A's registry migration; agrees sample/genuine union/nullability and retry semantics with A |
| Task creation policy | Proposal defaults to operator creation | A/D/C confirm operator-only, recovered/terminal behavior and equivalent/conflicting retries |
| Incident UI | No completed genuine flow | C after A APIs and D backend; no duplicate screen/client |

Do not reinterpret the preview frontend acknowledgement as a persisted operation.
The existing event catch-up specification is also not an implemented incident API.
A's open integrated-demo branch has no incident/identity module in its backend
file inventory; B's audit branch has proposal/detector artifacts, not A runtime
storage. No teammate branch was modified or incident table invented.

## Completed D work and checks

Added `integration/inspect_incident_dependencies.py`: a read-only local inventory
of the actual Alembic graph, registered model tables and OpenAPI operations/security
declarations. It uses no database/network I/O and never certifies readiness from
names or OpenAPI security alone. Repeat from repository root:

```powershell
python -m integration.inspect_incident_dependencies
python -m pytest analytics/contracts/test_incident_contract.py -q --tb=short
```

Use an environment containing existing backend requirements and the contract's
`analytics/contracts/requirements-test.txt` dependencies. Verification reused the
preserved Windows virtual environment; no packages or databases were replaced.

Actual results against the fetched application source:

- Contract consistency tests: **9 passed**. These validate labelled synthetic
  proposal snapshots, not runtime incidents or detector predictive accuracy.
- Migration graph: exactly **d004_worker_maintenance**; no registry migration.
- Registered metadata: nine existing tables; no canonical incident registry.
- OpenAPI: existing health/assets/telemetry/analytics/maintenance only; no incident
  operations or declared security schemes. Source also identifies demo actor as
  untrusted; declarations alone would not prove auth even if present.
- FastAPI TestClient GET incident, evidence and events and POST acknowledgement:
  **four404 responses**, consistent with missing routes. These were in-process
  ASGI requests, not live HTTP/browser execution; no DB dependency was invoked.
- Current TaskCreate rejects the proposed genuine reference; sample-only guard
  remains intact. Diff whitespace validation passed.
- TestClient emitted an existing Starlette/httpx deprecation warning.

No new migration exists to test fresh/upgrade data preservation against. Existing
migration files/backend have zero diff across the newly merged contract/plan.
No database was started or altered. No genuine UI flow is complete, so no actual
incident browser run or substituted mock is claimed. Prior sample Chrome results
remain historical. Full unchanged sample/database suites were not repeated.

## Next concrete dependency and execution order

A: provide the registry migration (table/key/FK types and asset binding), persisted
incident read/evidence contract/API, selected detector orchestration/handover,
and trusted acknowledgement contract. B: confirm adopted detector/model/policy
and evidence behavior. D: then implement an additive sample-preserving FK/task
union and idempotent service, run the plan's isolated PostgreSQL fresh/upgrade/
record-preservation and API checks. C: integrate the genuine flow, then D runs
actual Chrome workflow/conflict/offline/refresh/restart verification.

Order: A registry migration -> D additive task migration -> A/D APIs -> C UI ->
combined verification. Reinspect the final graph; preserve applied D001-D004 and
A revisions, adding a join only if required after actual schema conflict review.
Acknowledgement remains an explicit independent action throughout.

This draft delivers readiness tooling/documentation only. It does not advertise
incident-linked task creation, trusted authentication or production deployment.
