Implement durable incident registry and complete Person B worker handoff

Person B's PR24 provides pure detector storage commands; main still has no
canonical incident registry, trusted acknowledgement API or durable detector
persistence. This branch carries A's existing registry implementation and corrects
its missing delivery checkpoints and incomplete result-binding validation.

Integrate the pure detector inside the fenced worker without upgrading model1.0.1.
Persist real result references, twin/detector state, UUID mappings, immutable
evidence/history, pending delivery checkpoints and job completion atomically.
Add bounded read/evidence/history APIs, server-verified operator credentials and
versioned, idempotent acknowledgement/admin handover. A002 preserves existing
journal records and enables ordered, leased, post-commit at-least-once dispatch
through a supplied transport interface. No transport is configured or deployed.

Validation: 265 backend tests passed; B's exact f668a21 exported analytics/contract
suite214 passed with three explicitly skipped separate-branch simulator cases.
Fresh and eight existing migration-state upgrades, populated A001 preservation/
backfill, metadata drift checks, isolated actual HTTP lifecycle/retries and four
local-receiver dispatch receipts passed. Sample maintenance remains unchanged.
See docs/persona-detector-handoff-review.md and its structured evidence.

D's future task FK targets incidents(id UUID,asset_id VARCHAR100) via composite
uq_incident_asset; migration parent is now A002. Genuine task integration, queue/
WebSocket wiring, external SSO/tenant scope and model1.0.2 adoption remain separate.
B/D should review handover/identity/task eligibility choices before deployment.
Requires teammate approval and exact-head hosted CI. Draft; do not merge automatically.
