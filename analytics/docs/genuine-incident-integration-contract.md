Audit update: this branch regenerates synthetic fixtures with B model `1.0.2` and detector `1.0.1`. A's deployed model remains `1.0.1`; storage/API sections below remain proposals.

# Genuine analytics incident integration: B -> A -> D

**Status: reviewed B proposal, awaiting A/D acceptance.** This document does not claim agreement by absent teammates, implemented incident storage, delivered alerts or genuine-alert maintenance support. It can be reviewed alongside D's backend PR without changing the sample workflow. No existing shared contract, A/D backend, database or deployment is modified.

Reviewed 9 October 2026: main9d2f9cd, B564b174, Dpersond f293ef9, Dcurrent-main fix13cbb80. No applicable AGENTS.md was found. Current source code, not earlier runbook statements, determines the implementation status below.

## What exists today

| Component | Implemented behavior | Missing boundary |
|---|---|---|
| A main worker/model1.0.1 | Stores each reading's analytics and state; result API references immutable configuration, measurements, prediction/residual, quality and provenance | Does not run B's sustained detector or persist incidents |
| payload.anomaly_observations | Instant configured_limit_check records, including breached true/false/null and evidence | A breach on one reading is **not** a persistent incident or fault probability |
| B optional evaluate_persistent_rules, sustained-threshold1.0.1 | Pure endpoint-based persistence/recovery; stable candidate episode keys, evidence, active history; tests and synthetic examples | Still unmerged/not invoked by A; no backend persistence/publication |
| Older B prototype adapter | Earlier heuristic lifecycle demo exists on B's branch | Not the adopted deployed interface; its scores/IDs are not authoritative for this integration |
| D maintenance PR | Sample-only task creation, assignment/status/notes/history; optimistic task versions and permanent sample identity | SampleAlert source=sample and sample-* IDs; genuine incidents are rejected by schema and DB constraint |

Reviewed branches/PRs: [B analytics PR7](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/7), [D maintenance PR9](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/9), [D main registration/join PR13](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/13). This proposal is on `feature/personb-incident-contract`, based on current main. D's existing sample contract remains intact; do not relabel computed alerts as sample to bypass it.

## Incident identity proposed for A/D acceptance

An episode means one sustained rule breach for an explicit `(asset_id, measurement_source, run_id, rule_identity)` until observed sustained recovery. Different runs/sources/rules must not share state or incident IDs. This is per-rule evidence, not a declaration that simultaneous rule breaches have one common physical root cause.

1. B's detector currently returns a string named incident_id: `SHA256(binding):rule_name:episode_sequence`. Binding includes stream, configuration, model/parameter versions and policy fingerprint; the same episode's opened/resolved candidate uses the same key. Reopened episodes increment sequence.
2. At the persistence boundary, rename that string **detector_episode_key**. It remains the deterministic detector replay/idempotency key; it is not a reading/result ID or a transport event ID.
3. **Canonical incident_id is a server-issued UUIDv4**, allocated by A once on first committed opening. Create a mapping unique on `(asset_id, detector_epoch, detector_episode_key)` and fetch the existing UUID on retry/conflict. Reject contradictory stream/rule/asset bindings. Updates, acknowledgement, recovery and D's task FK all retain that UUID for the episode.
4. detector_epoch is a durably recorded UUID assigned once for a fresh operational detector-state namespace. It survives restarts/retries. Fresh resets with restarted sequence require a new epoch; same-epoch replay reuses mappings and must not notify/create tasks twice. B's raw detector does not presently carry an epoch; A supplies this persistence namespace outside the pure function.
5. Reading ID, stored-result ID and message UUID are **evidence references only**. They never become canonical incident IDs. An event_id identifies a specific published transition, also not an incident ID.

Configuration/model/policy changes need an explicit handover decision. The current B detector rejects incompatible state and can generate a different key after reset. Do not automatically mark an active incident recovered or silently create a second incident for a continuing abnormal episode. Proposed conservative behavior: keep the old incident active with unavailable evidence and block automatic same-rule replacement until A/D authorize a recorded handover or establish observed recovery. Reviewed handover may map a successor epoch/key to the **same canonical UUID**, recording changed versions in each evidence snapshot. A/D must agree and implement that policy; it is not present in B's code. Never reuse a historical UUID for a genuinely reopened recovered episode.

## Evidence D must retrieve

Proposed typed read model: `analytics/contracts/incident-proposal.schema.json`, version incident-proposal-1.0.0. The labelled [example](../examples/incident-contract-proposed-example.json) shows opened/update/recovery snapshots with one canonical UUID. Quantities come from B's actual synthetic detector execution; canonical UUIDs and result IDs are illustrative, unpersisted references. This example is not an accepted backend response or a genuine detected field incident.

Each persisted evidence snapshot must include:

- incident asset/source/run/category, detector epoch/episode key and condition/acknowledgement state.
- immutable reading_id, exact stored result_id and message_id; UTC measurement time. Database processing/publication/ack timestamps are separate and are not model time.
- measured top-oil, predicted top-oil and observed-minus-predicted residual, all inC; null and availability reasons when unavailable. Measured quantities retain measurement_source device/simulator/file_replay; predicted quantities are estimates. Bootstrap measurement is not an independent prediction.
- selected rule quantity/value/unit, trigger/recovery thresholds, persistence/recovery seconds, availability reasons and gap/endpoint continuity assumption. Preserve opening evidence plus later updates/recovery; current missing evidence must not disguise older evidence as a current observation.
- data_confidence.score=null, status=not_estimated and no_calibrated_confidence_model reason; channel usability/reasons/counts describe coverage, not a percentage/probability. No new confidence number or health score is inferred.
- model_id/version, result schema version, configuration version and immutable parameter fingerprint; detector version, policy version/fingerprint and policy provenance. Exact dotted parameter provenance comes from the bound config. Each snapshot stores its own versions, especially after an authorized handover.

Additional investigation values—currents/voltages/loading/ambient with units and quality—remain available through the corresponding stored result and normalized reading. D should fetch the referenced record rather than synthesize a value. Raw original_payload, generator scenario labels and ground-truth fields are excluded from detector inputs and incident evidence. Source=simulator is a provenance/isolation field, not a scenario label.

The incident read model includes a positive incident_version for optimistic updates and
policy-supplied severity; neither is derived from task status or a fabricated fault score.

Implemented retrieval today: `GET /api/v1/telemetry/{reading_id}/analytics`, and stream-scoped `/api/v1/assets/{asset_id}/analytics/latest?source=...&run_id=...`. The reading API selects its most recent stored result; a latest endpoint is not an incident's immutable opening evidence. Persist snapshots and exact result IDs so evidence stays reproducible even if more results exist later.

**Proposed, not implemented endpoints:**

| Endpoint | Intended guarantee |
|---|---|
| GET /api/v1/incidents/{incident_id} | Transformer-bound condition and separate acknowledgement, exact version/last-evaluated time and evidence summary |
| GET /api/v1/incidents/{incident_id}/evidence?cursor=... | Immutable, paginated opening/update/recovery/unavailable evidence; retains exact result references |
| GET /api/v1/incidents/{incident_id}/events?cursor=... | Durable lifecycle and acknowledgement history; stable server cursor for catch-up |
| POST /api/v1/incidents/{incident_id}/acknowledgements | Explicit reviewed/authenticated actor, expected incident version/idempotency key; cannot change recovery or tasks |

Application validation must enforce asset/stream/result binding, FK existence, UTC/time ordering, finite JSON, threshold consistency and residual semantics; JSON Schema cannot enforce database relationships. Unavailable snapshots keep null values/reasons; no old prediction is relabelled as current. Schema confidence is intentionally null for this model version. These routes do not exist yet.

## From computation to persistent storage

**Proposed A transaction:** under the existing fenced per-stream ordered worker ownership, obtain the normalized reading/immutable configuration and prior twin/detector state. Run pure analytics and eligible detector evaluation without DB I/O. In one fenced commit persist analytics result, twin state, detector state/watermark, incident mapping/header, immutable evidence/history, transition outbox entries and job completion. If implemented as a separate consumer of committed results instead, require its own durable offset, lock/ordering, unique result-consumption keys and atomic detector-state/incident/outbox transaction; do not run an uncoordinated callback that publishes before commit. Choose and record one orchestration design with A.

Creation consumes opened candidates only after persistence duration. For already active candidates, append evaluated available/unavailable evidence and update last-evaluated status without allocating another incident. B currently emits events only on opened/resolved; its evidence/active_incidents arrays supply updates, so the integration must not wait for an update event that B never emits. Resolved maps to condition_status=recovered for the same canonical UUID only on detector-observed sustained recovery. Missing evidence, no packets, gap, task completion and acknowledgement never produce recovery.

Unique proposed keys: mapping `(asset_id, detector_epoch, detector_episode_key)`; evidence `(incident_id, result_id, detector_version, policy_fingerprint)`; outbox `(incident_id, incident_version, event_type)`; processed result/detector namespace key. Equal/late/historical/error results cannot advance live detector state or emit forward transitions. Concurrent workers/retries must resolve uniqueness under the same fencing check; rollback reloads committed state. Store the event UUID once and reuse it for redelivery.

Publish only after commit using a durable outbox. Proposed incident.opened/updated/recovered/acknowledged event types require A/D adoption; existing shared event types are proposals, not working transport. Envelope should retain event_id, incident_id, asset_id, source/run, measurement_time, publication_time, incident_version and immutable evidence references. Different events share incident_id but have distinct event_id. Redelivery retains event_id. Consumers deduplicate by event_id and use incident_version/server cursor; measurement-time polling alone cannot reliably recover concurrent updates. No publisher/outbox or new incident table is implemented here.

## D maintenance binding and independent lifecycles

Proposed genuine task create reference: `{ "source": "analytics", "incident_id": "<canonical UUID>", "asset_id": "<bound transformer>" }`. D resolves the persisted incident server-side and checks transformer/source/run and evidence; it must not trust a client-supplied summary as proof of an incident. Genuine task identity/foreign key is separate from current SampleAlert. Add reviewed schema/migration support while retaining existing sample rows/constraints semantics. Do not truncate B's episode key into D's100-character sample alert field.

Preserve D's one-task-per-incident idempotency with a unique canonical incident FK; retries return the existing task, not a new task per reading/update. A reopened recovered episode has a new UUID and can have a new task. D/A should decide explicitly whether task creation is operator-only; **this proposal defaults to operator creation**, not automatic maintenance recommendations.

Three independent axes:

| Axis | Owner / state | Must not implicitly alter |
|---|---|---|
| Physical condition | B evidence via A storage: active/recovered | Acknowledgement or task state |
| Operator acknowledgement | A/D reviewed actor: unacknowledged/acknowledged | Physical recovery or task completion |
| Maintenance task | D: open/in_progress/completed/cancelled | Incident acknowledgement or physical recovery |

A completed task can coexist with an active unacknowledged incident. A recovered incident can have an incomplete task. Acknowledgement does not hide continuing abnormality. Recovery never erases evidence/tasks; task completion notes/history remain D's existing workflow. D's demo actor header is not authenticated identity; real acknowledgement identity requires an explicit A/D decision.

## Validation and review decisions

Only proposal artifacts are added. `analytics/contracts/requirements-test.txt` declares test-only JSON Schema validation; runtime backend dependencies are unchanged. Actual command `.venv/bin/python -m pytest analytics/contracts/test_incident_contract.py -q --tb=short`:9 passed. Tests check UUID rather than reading/result identity, stable episode identity over three snapshots, changing evidence references, distinct task/recovery/acknowledgement states, residual sign/units/null confidence/provenance and rejection of sample/scenario/task-state substitutions. They validate schema/example consistency, **not** backend persistence, delivery or end-to-end maintenance integration.

The example builder ran on B564b174's exported executed detector fixture without switching/merging that branch. Regenerate with `python -m analytics.examples.build_incident_contract_example --detector-example <B persistent-rules-test-example.json> --output <new example path>`. Synthetic threshold evidence does not establish physical fault accuracy; policy thresholds remain assumed and calibration/independent measured validation is outstanding.

A/D acceptance required before implementation: canonical UUID mapping and detector epoch, transition/handover policy, worker-integrated versus ordered-result-consumer transaction, tables/constraints/outbox/cursor, exact incident/evidence/ack APIs and trusted identity, and genuine task schema/FK. B recommends the concrete design above but has not received teammate acceptance. Existing BPR7 contains tested detector logic; DPR9/13 remain sample maintenance. This branch/PR shares the reviewable contract only; no automatic teammate messages/review comments or merge are performed.
