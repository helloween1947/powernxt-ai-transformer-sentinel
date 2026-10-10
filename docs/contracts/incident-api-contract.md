# Incident registry API — implemented contract 1.0.0

This extends merged PR15's proposal with A's runtime persistence, identity,
version and error choices. It retains the proposal artifacts as historical design
material rather than changing their `incident-proposal-1.0.0` version. B's concrete
f668a21 handover is adopted as described in [A/B handover](../incident-worker-handover.md).
This branch needs human review and CI before adoption into main. It is not deployed
to the preserved development API and does not implement D's genuine task FK.

## Identity, authority and asset mapping

`incidents.id` is a server-issued PostgreSQL UUIDv4. The public field is
`incident_id`; `incident_version` is an integer starting at 1. Canonical mapping
is UNIQUE `(asset_id, detector_epoch, detector_episode_key)`. Episode keys are
never truncated into sample alert IDs. Reading/result/message/event IDs are
evidence identities, not incident identities. Reopened recovered episodes have
new canonical UUIDs. Source is always `analytics`; `measurement_source` separately
retains device/simulator/file_replay provenance and run isolation.

D's future migration can use composite FK
`(incident_id UUID, asset_id VARCHAR(100)) -> incidents(id, asset_id)` with
`ON DELETE RESTRICT`; target UNIQUE name is `uq_incident_asset`. Single UUID FK
alone does not bind a task to its transformer. Registry epoch stream/configuration
FKs and an evidence binding trigger reject contradictory asset/run/result/config
references. No incident delete endpoint is provided. Evidence, events and operation
receipts are append-only in PostgreSQL; epoch bindings/policies are immutable.

All incident endpoints require `Authorization: Bearer <credential>`. The server
looks up the SHA256 hash of a random 256-bit opaque credential in
`incident_operators`, checking active status and expiry against database time.
Actor UUID/role is server-controlled; request bodies cannot specify an actor.
`X-Demo-Actor`, asset IDs and asserted role headers confer no incident authority.

Roles: reader can retrieve incidents/evidence/events and self identity; operator
also acknowledges; admin also records handovers. Authorization currently applies
to the whole repository deployment, not individual assets or tenants. There is no
public user signup/token minting/login endpoint. A server administrator issues,
rotates or revokes credentials through `python -m backend.app.operators`. Rotation
retains the actor UUID and invalidates the old token. Lifetimes are 1–24 hours
(default 8); revocation serializes with requests through the actor row lock.
Credentials are written exclusively to a new private file, not stdout/database
plaintext. Use a protected per-user directory outside Git; Windows administrators
must ensure the directory ACL restricts access to the intended operator. Deliver
credentials securely and use HTTPS outside loopback. SSO/OIDC/MFA, tenant RBAC and
browser credential storage are separate integrations, not implemented claims.

Existing sample maintenance keeps its original prototype actor and payloads.
Existing legacy asset/telemetry endpoints are not secured by this new incident
dependency. D must explicitly use the trusted dependency for genuine mutations;
do not relabel sample actors as authenticated operators.

## Endpoints and versions

| Operation | Result / authorization |
| --- | --- |
| GET `/api/v1/analytics/results/{result_id}` | `incident-stored-result-1.0.0`, exact immutable stored result (not latest) |
| GET `/api/v1/operators/me` | `incident-operator-1.0.0`, actor UUID/name/role/expiry |
| GET `/api/v1/incidents?asset_id=...&source=simulator&run_id=...` | `incident-page-1.0.0`, exact stream required, optional condition filter |
| GET `/api/v1/incidents/{incident_id}` | `incident-1.0.0`, authoritative asset/stream, condition, monitoring and acknowledgement |
| GET `/api/v1/incidents/{incident_id}/evidence?cursor=0&limit=20` | `incident-evidence-page-1.0.0`, immutable exact-result snapshots |
| GET `/api/v1/incidents/{incident_id}/events?cursor=0&limit=20` | `incident-event-page-1.0.0`, durable lifecycle/ack/control journal |
| POST `/api/v1/incidents/{incident_id}/acknowledgements` | Operator/admin; `incident-acknowledgement-1.0.0` request, incident result |
| POST `/api/v1/assets/{asset_id}/detector-handovers` | Admin; `incident-control-1.0.0` request, `incident-control-result-1.0.0` result |

The response's `source=analytics` is distinct from the list query's `source`, which
selects the measurement source. Device requires absent run_id; simulator/replay
require a nonblank run ID. Unknown registered assets/incidents return 404.

All page sizes are bounded 1–100, default 20. Incident browsing is UUID ascending
with an exclusive UUID cursor; it is not a global change feed or snapshot across
concurrent inserts. Evidence/events use exclusive **incident-version** integer
cursors and ascending versions. `next_cursor` is null when no extra row existed
at retrieval. For ongoing per-incident polling retain the highest seen version
even when next_cursor is null, so later appends can be retrieved safely. Incident
row locking allocates event versions in commit order for that incident; global
sequence/time ordering is not claimed. Acknowledgement/handover events need not
have a new measurement snapshot, so evidence versions may have gaps.

Opening time/recovery/last-evaluated time are UTC measurement times. Evidence/event
`recorded_at` and acknowledgement time are separate UTC database clocks. Events
are durable records with stable event UUIDs; they are not already published
WebSocket/queue notifications and have no invented publication_time. Future
publishers use A002's durable `incident_deliveries` checkpoint and the separately
fenced post-commit dispatch interface. Delivery is at least once with `event_id`
deduplication and per-incident version ordering; no transport is wired. No `/api/v1/events` or
automatic maintenance recommendation is introduced.

## Acknowledgement and conflicts

```json
{"schema_version":"incident-acknowledgement-1.0.0","expected_version":1,"idempotency_key":"50000000-0000-4000-8000-000000000002"}
```

New acknowledgement returns 201; an identical `(incident_id, idempotency_key,
request content, authenticated actor)` retry returns 200 with the **original
persisted result**, even after later detector updates. The current incident can
be retrieved separately. Reuse with different content/actor returns 409
idempotency_conflict. Receipt lookup precedes expected_version comparison.
Successful acknowledgement atomically increments incident_version, records actor
and database timestamp and appends an event/receipt. It cannot recover the physical
condition, complete a task, or erase evidence. Different-key repeated acknowledgement
with current version returns already_acknowledged. No unacknowledge operation.

## Error contract

All incident-route errors use `incident-error-1.0.0`:

```json
{"schema_version":"incident-error-1.0.0","code":"version_conflict","message":"Incident version changed","current_version":4}
```

| HTTP | Stable code / meaning |
| --- | --- |
| 401 | `unauthenticated`: missing, invalid, expired or revoked credential; WWW-Authenticate: Bearer |
| 403 | `forbidden`: authenticated role cannot perform this operation |
| 404 | `asset_not_found`, `configuration_not_found`, `incident_not_found`, `result_not_found` |
| 409 | `version_conflict`: stale expected version; current_version provided |
| 409 | `idempotency_conflict`: same operation key, different content/actor |
| 409 | `already_acknowledged`: new-key repeat of completed acknowledgement |
| 409 | `stream_busy`: handover conflicts with an unexpired worker lease |
| 422 | `invalid_request`: malformed JSON, nonfinite numbers, unknown fields, unsupported schema/model/detector version or invalid typed input |
| 422 | `invalid_stream`: source/run pairing invalid |
| 503 | `database_unavailable`: database operation failed; transaction rolls back |

Strict request schemas forbid extra fields and boolean expected_version values;
policy quantities, units, thresholds, rule names, durations and provenance are
validated. No raw request/exception/credential is echoed in errors. OpenAPI declares
security, request/response versions and error response schemas. Existing legacy
routes retain their earlier errors. After 409, retrieve current state and ask the
operator to review; do not silently overwrite/retry with an updated version.

## Evidence and limitations

Each snapshot retains exact reading/result/message IDs, UTC measurement time,
observation kind, measured/predicted/residual temperatures in C, rule quantity/
thresholds/durations/availability/continuity, channel coverage, null numerical
confidence, model/configuration/parameter/detector/policy versions and provenance.
It follows PR15's evidence field shape inside `payload`; canonical headers use the
new API version. Thermal initialization gaps and observed-minus-predicted residual
sign remain intact. Missing values stay null. Coverage counts are not confidence.
Unavailable evidence and interrupted monitoring cannot imply recovery. Use the authenticated exact-result endpoint for supporting electrical values; do
not substitute a reading/latest result that could later select another model. Original
payload and simulator ground-truth labels do not enter the detector or snapshots.
Synthetic inputs can generate persisted analytics incidents; this does not make
them field faults or prove detector calibration.

Examples, credential provisioning and isolated verification commands:
[backend usage](../../backend/docs/incidents.md). Actual executed evidence:
[verification](../incident-registry-verification.md).
