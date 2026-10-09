Merged PR15/21 describe canonical incident identity, but main still has no registry,
trusted actor or incident operations. Add an additive A001 registry after D004,
server-provisioned expiring bearer identities, canonical UUID/asset/epoch mapping,
versioned read/evidence/event/exact-result/ack APIs and admin handovers.

Adopt B's f668a21 sustained1.0.1 planner in the existing fenced worker while retaining
model1.0.1. Result, twin/detector state, evidence, incident journal and job completion
commit atomically. Explicit policy opt-in, continuity barriers, cold-start handovers
and archived prior twin state prevent silent resets. Acknowledgement, condition
recovery and sample task lifecycle remain independent. D's sample tables/APIs are
unchanged; the composite FK target and next D work are documented.

Validation: 246 backend PostgreSQL16 tests, 9 merged proposal-schema tests, targeted
Ruff, fresh/legacy migration upgrades and record preservation, no Alembic metadata
diff, offline SQL and actual isolated HTTP/worker open/ack/recover/idempotency all
passed. Development services/data were untouched. No Windows/browser or hosted CI
pass is claimed.

Review focus: server-provisioned credentials/role scope; explicit policy/handover
control and compatibility; D's composite FK/independent version semantics; planner
runs after real-result flush inside the final lease-fenced transaction. Not deployed;
no task FK/GUI, external SSO, transport publisher or physical calibration claim.

Contracts/examples/evidence: docs/contracts/incident-api-contract.md,
backend/docs/incidents.md, docs/incident-worker-handover.md,
docs/incident-registry-verification.md and docs/incident-registry-evidence.json.
