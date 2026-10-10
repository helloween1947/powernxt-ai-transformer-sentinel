# Person A model 1.0.2 adoption review — 10 October 2026

This is a source adoption for review, not a deployment or application-database
migration. It is stacked on `feature/persona-incident-registry` at
`2e934c85098453db7342ea6ade570759ef4b9161`. Main inspected after explicit fetch is
`cbdd7c47f8cf5aa66d0277f5fa96d69bfb01ddda`. B's alignment head is
`d86b210a5ee3a0a62b926b134d1119abeb3ff1fd`; executable computation remains exactly
`f668a21dcf88605d7fcff4996282185bc796740c` (PR24 includes PR17 lineage).

## Accepted A decisions

- Current worker: `powernxt-electrical-top-oil` / `stored-reading-top-oil-1.0.2`.
  State `stored-reading-state-1.0.0`, result `stored-reading-result-1.1.0`, detector
  `sustained-threshold-1.0.1`, forecast `healthy-top-oil-scenarios-1.0.1` remain
  explicitly pinned. No equation, coefficient, tuning or registry rating changes.
- Adopt B's worker, normalization, validation, physical primitives and scenarios
  together. The manifest records all 14 original hashes, extracted functions and
  adapted file hashes. The conservative worker does not invoke prototype health,
  RUL, confidence or legacy engine orchestration. Scenario labels remain excluded
  by the normalized-channel whitelist and detector quantity whitelist.
- Historical What-if uses server version dispatch. `historical_v101` retains the
  original vendored 1.0.1 worker/core/normalization/validators/scenarios unchanged,
  including its arithmetic failures. Both scenarios use one immutable snapshot
  and exact immutable configuration. No relabelling, patched captures, fallback
  model, client-supplied callable or serialized worker state.
- A previously used model namespace must have an explicit, trusted admin handover
  before this worker can claim further jobs. Waiting jobs keep status/attempts;
  independent streams continue. A stale pre-adoption claim is also rejected before
  computation. A handover clears the lease fence, retains the measurement boundary,
  archives prior state, allocates a new durable UUID4 epoch and cold-starts context.
  The final worker transaction still atomically stores result/state/context,
  incident mapping/evidence/event/delivery checkpoint and job completion. Outbox
  publication remains separate, after commit; no transport was added.
- Existing active incidents remain active with monitoring interrupted. Existing
  acknowledgements, evidence, tasks, immutable snapshots and old namespace rows
  remain intact. Handover is neither observed recovery nor task completion.
- Newly encountered unmonitored streams use the current model from their first
  reading. Existing config-only behavior on streams with no control is retained;
  once a model/detector control is installed, changing its configuration/parameter
  identity requires another explicit handover. Model adoption never reprocesses
  terminal jobs, installs replay state or backfills history.

## Versioned handover APIs

`POST /api/v1/assets/{asset_id}/detector-handovers` keeps
`incident-control-1.0.0`, its required explicit policy and trusted admin identity.
It accepts known 1.0.1/1.0.2 identifiers so identical historical 1.0.1 retries can
return their original `200` receipt. A *new* 1.0.1 request returns `409`
`unsupported_model_version`; an unknown identifier returns `422 invalid_request`.
New accepted handovers select 1.0.2 explicitly. Nothing upgrades an old request.

`POST /api/v1/assets/{asset_id}/model-handovers` adds the same fenced, idempotent
control protocol for **unmonitored** streams, without inventing detector thresholds:

```json
{
  "schema_version": "model-control-1.0.0",
  "expected_version": 0,
  "idempotency_key": "50000000-0000-4000-8000-000000000001",
  "source": "device",
  "run_id": null,
  "configuration_version": 1,
  "model_version": "stored-reading-top-oil-1.0.2",
  "reason": "Reviewed model adoption; preserve prior history"
}
```

This is a sanitized illustrative request, not evidence that a production asset
was changed. `policy` must be absent/null. The optional `detector_version` is fixed
at `sustained-threshold-1.0.1` for the existing shared epoch representation; this
route does not run detection. Its stored policy is the explicit disabled marker
`{"schema_version":"model-only-control-1.0.0"}`, not an inferred threshold policy.
Moving a monitored stream to this mode interrupts its old active episodes.

Both routes require an active, unexpired local opaque Bearer credential with
admin role; `X-Demo-Actor` is not identity. Responses share
`incident-control-result-1.0.0`: UUID epoch, previous epoch, control version,
asset/source/run, model/configuration/parameter identities, actor reference and
boundary measurement time. New requests return `201`, identical retries `200`,
changed-content/actor reuse `409 idempotency_conflict`, stale expected version
`409 version_conflict`, live lease `409 stream_busy`, missing asset/configuration
`404`, malformed input `422`, missing credentials `401`, wrong role `403`, database
failure `503`. Errors use the existing flat `incident-error-1.0.0` envelope. No
SSO/tenant identity claim is added by this source change.

At bootstrap, prediction and residual are null with
`initialized_from_measurement_prediction_not_independent`. The next usable
forward reading within 300 seconds uses the previous sample's held load/ambient.
At 300 seconds it is eligible; beyond that continuity is invalid. Equal/late
boundary readings cannot become the new bootstrap. Failed/skipped evidence
barriers and epoch-isolated detector timers retain the existing fenced protocol.

## What-if compatibility for C

The public What-if request/response/error schema versions stay 1.0.0. No frontend
request changes are needed. An explicit old reference executes 1.0.1; a new 1.0.2
reference executes 1.0.2. Latest selection may still resolve a committed 1.0.1
namespace before handover; immediately after handover, no new state exists and
`409 state_unavailable` is correct. An old explicit reference remains usable.
Unknown model/state/result schema or identity/parameter mismatches fail closed
with `409 incompatible_state_identity`. Capturing a new reference checks result
schema 1.1.0 and state schema 1.0.0. Existing snapshots retain their original
version-bound state; execution never reconstructs them from mutable result rows.
Arithmetic failure remains `422 computation_unavailable`, without a numeric
success, committed new capture or worker writes.

Bounds and interpretation remain: equal duration in `(0, 86400]` seconds; load in
`[0,10]` pu; equal ambient in `[-50,80]` C; reduced load <= baseline; at most 97
points including zero and horizon. Peaks include the initial condition; configured
limit crossings use analytic >= semantics, distinct from unavailable/no crossing.
Final difference is reduced minus baseline. These are conditional healthy-model
estimates using provenance-labelled coefficients, not calibrated accuracy,
physical safety, cooling intervention or fault diagnosis.

## Verification and review gates

See `person-a-model-102-verification.json` for exact commands, hashes and fresh
results; `data/sample/model-102-adoption-verified.json` contains actual isolated
HTTP examples. Synthetic extreme inputs prove numeric behavior, not admissible
physical asset specifications. Earlier 1.0.1 verification files remain unchanged.

Only a new isolated PostgreSQL container/database and dedicated test API were
used. Development backend/database, volumes, .env and other worktree edits were
preserved. No Windows/browser/deployed-worker verification is claimed. The React
check uses actual HTTP responses and server-side rendering through the reference
adapter; C still owns the full interactive UI wiring.

The branch carries the registry/What-if/D task dependencies inherited from the
reviewed registry head. Human review of those dependencies, this adoption and CI
is required before merge or rollout. Deployment timing, trusted credential
provisioning and each asset/stream's policy/configuration handover remain operator
and team decisions. A rollout must replace/drain the worker fleet coherently and
wait for live leases before recording handovers; concurrent old/new worker fleets
are unsupported. This review did not switch the running worker or backend. No PR was merged and no teammate message was sent.
