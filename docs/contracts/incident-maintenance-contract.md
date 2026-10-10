# Genuine incident-linked maintenance — D draft contract 1.0.0

Depends on A's unmerged `feature/persona-incident-registry` at
`4bfe3ed4ca6798d4f1c3b836ffde6fe33e3b5420`. This is a tested isolated integration,
not deployed main. A's [incident API](incident-api-contract.md) supplies the
canonical registry, exact evidence and authenticated actor. D does not implement
another registry, detector, credential service or acknowledgement operation.

## Requests and authorization

Existing `/api/v1/maintenance/tasks` accepts a strict discriminated `alert` union.
Sample payloads retain their original shape. Genuine explicit operator creation:

```json
{"alert":{"source":"analytics","incident_id":"193f8ed2-16c0-4430-85a3-01452edbf6e4","asset_id":"d-genuine-test-a28aa7cd708b46f5a110df9a60a9e913"},"action":"Inspect actual worker overload evidence"}
```

This UUID/asset is from an isolated synthetic worker execution, not a universal
production example. No client summary, actor, condition, evidence, stream or
incident_version field is accepted. The server resolves canonical incident and
asset binding, source/run and persisted opening evidence; summary is generated
from the stored category/severity. Incident UUID is never a reading/result ID.

Creation and PATCH for genuine tasks require A's valid Bearer credential with
operator/admin role. Genuine GET task/history and `GET .../tasks?source=analytics`
require reader/operator/admin. Default list is sample-only, even with a credential;
explicit analytics source is required to browse genuine tasks. Direct genuine ID
access cannot bypass authentication through legacy/sample routes. Global role
scope follows A's implementation; per-asset tenants, SSO and browser storage are
not implemented. X-Demo-Actor confers no genuine authority and is ignored there.
Sample PATCH continues to require that explicitly untrusted display label.

Authentication errors reuse A's `incident-error-1.0.0` and WWW-Authenticate:
missing/invalid/expired/revoked401; reader mutation403; missing incident404;
asset mismatch422. Other maintenance validation/conflict/database errors retain
the existing `detail` shape/status (422/409/503). Clients must support both error
shapes and never log credentials. Genuine identity comes only from A's dependency.

## Responses, audit, retry and independent lifecycles

201 creates a new task; 200 returns the current existing task on an equivalent
retry. Both carry Location pointing to the task. Stored creation intent compares
the normalized source/UUID/asset/action/original owner. Omitting owner and null
normalize equally; later assignment does not alter this intent. Another authorized
operator can retrieve that same equivalent result; attribution stays with the
original creator. Different action or original owner yields409, never an overwrite.
One task remains per canonical UUID even after completion/cancellation/recovery.
A reopened episode has a new UUID and may support a new task.

An actual opening task response includes:

```json
{"alert":{"source":"analytics","incident_id":"193f8ed2-16c0-4430-85a3-01452edbf6e4","asset_id":"d-genuine-test-a28aa7cd708b46f5a110df9a60a9e913","summary":"overload (warning)","measurement_source":"simulator","run_id":"synthetic-fbb384f66a6444d59c03654575c031f7","evidence_id":1},"status":"open","version":1}
```

This is the relevant subset of the executed response; standard id/action/owner/
notes/created_at/updated_at fields remain. Evidence ID references an immutable
opening snapshot in A's evidence page; follow its exact result_id to A's stored
result API. Do not substitute latest analytics. Persisted synthetic evidence is
not a calibrated field fault; preserve measurement_source/run provenance.

PATCH uses only the task's expected_version. Incident_version belongs to A's
operations and never substitutes for a task version. Existing transitions,
required owner/terminal notes, atomic history, conflict review and terminal
read-only behavior remain. History adds nullable actor_id; genuine rows require
identity_source=authenticated_operator and actor equal to the server actor UUID.
Sample/history UUID columns stay null; existing attribution labels remain honest.

New creation for recovered or interrupted incidents currently returns409
`incident_creation_policy_required`. A's contract delegates that policy to D;
no team agreement exists for expanding it. Proposed future policy: allow explicit
operator creation for historical investigation with a recorded reason and visible
recovered/interrupted state. A/D/C must review the request/UX before enabling it.
This draft deliberately supports only new active+monitoring incidents. Existing
retry is evaluated first and remains allowed in every later incident/task state.
Acknowledged active monitored incidents can still have tasks; ack does not create
one, and task actions do not change acknowledgement/condition/monitoring.

C calls A's acknowledgement API separately, with incident_version and UUID
idempotency key. Neither create nor complete implicitly invokes it. After a409,
retrieve the current incident/task independently and require operator review.
There is no atomic distributed create-plus-ack operation.

## Migration and release ordering

D005 `d005_incident_tasks` follows `a001_incident_registry`, which follows D004.
Keep prior migrations. Nullable incident_id remains null for every existing
sample. Composite FK `(incident_id,asset_id)` targets A's UNIQUE incidents(id,
asset_id), with RESTRICT; unique incident_id permits only one task per incident.
Opening evidence and creator/audit actor also have RESTRICT FKs. Source/reference
checks prevent sample rows masquerading as genuine or missing genuine references.
No sample backfill, truncation or record/history replacement occurs. Downgrade
refuses populated genuine tasks/trusted history rather than deleting them.

Merge A's reviewed registry first, then retarget/reassess D's stacked draft against
main and check the net diff contains only D contributions. Deploy registry then
D005 then backend then C's UI. Do not merge this draft into A's branch. Recheck the
actual graph if either prerequisite changes. C's authoritative sample screen stays
intact; its future genuine mode needs explicit authenticated browsing/creation,
source-aware response parsing and separate acknowledgement controls.
