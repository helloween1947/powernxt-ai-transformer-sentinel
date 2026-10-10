# Backend completion matrix — 11 October 2026

Scope is the agreed executable local/demo contracts below, including the adopted
A/B/D unmerged designs explicitly requested for this candidate. It excludes
illustrative health/confidence/fault/SSO/transport/cooling proposals. 'Verified'
means the recorded checks, not physical accuracy, production hardening or peer
approval. Deployment is a separate gate. See `backend-complete-audit.md` for
source/runtime identity and `backend-complete-audit-evidence.json` for actual exits.

| Requirement | Agreed contract | Existing implementation | Missing/defective work | Acceptance check | Implemented | Verified | Unmerged | Undeployed | Blocked |
|---|---|---|---|---|---|---|---|---|---|
| Registered assets/physical configuration | backend/docs/asset-registry.md; explicit units/side/convention, finite numbers | schemas/assets, services/assets, registry migrations | Reused; no new registry implementation | test_assets; test_audit_regressions; live invalid-input rollback | Yes | Yes | No (baseline) | No (baseline) | No |
| Immutable configuration/provenance | Version append only, bound historical parameters | DB immutable trigger; configuration history | Reused | DB update/delete rejection; old rows/hash preservation; live unchanged config | Yes | Yes | No (baseline) | No (baseline) | No |
| Telemetry identity/validation | contracts/telemetry-contract.md 1.0.0 | Strict request, explicit asset/config/source/run/time | Reused | Boolean/string/nonfinite/time overflow/unknown identities; strict JSON; test_telemetry | Yes | Yes | No (baseline) | No (baseline) | No |
| Retry/conflict/atomic admission | 201 new,200 identical,409 changed content; one reading/job | Asset lock, composite unique keys, transaction | Reused | Live concurrent1x201+5x200; changed-content409; DB rollback/concurrency suite | Yes | Yes | No (baseline) | No (baseline) | No |
| Retrieval/pagination/isolation | Time/ID order, explicit stream; latest measurement time | History/latest services | Reused | Live two pages, source isolation/latest; full DB query tests | Yes | Yes | No (baseline) | No (baseline) | No |
| Reproducible simulator | normal-operation-simulator.md; synthetic profiles/seed/provenance | simulator CLI/generator/client | Reused; no tuning | test_simulator; real six-packet worker verifier and retained JSONL | Yes | Yes | No (baseline) | No (baseline) | No |
| Durable worker/atomic completion | analytics-worker.md; leases/fences/retry bounds/forward-only state | analytics_worker service, opt-in worker | Existing model barrier reused | Live6+6 retries/final8/advances1,7/recovery2/restart; transactional rollback and terminal-failure tests | Yes | Yes | Adoption changes: Yes | Adoption changes: Yes | No |
| Electrical/thermal calculation | analytics-contract.md and person-a-model-102-adoption.md | Vendored B1.0.2, preserved1.0.1 | Already implemented in adoption ancestry; equations unchanged | 30 AST definitions,14 original hashes,26 adapted/historical hashes; cadence/gaps/extreme finite suites | Yes | Yes | Yes | Yes | No |
| Bootstrap/residual/units/provenance | Measurement time, observed-minus-predicted, unavailable reasons | Model/result schemas/adapters | Reused | Cold-start null prediction/residual; full model tests and actual worker results | Yes | Yes | 1.0.2: Yes | 1.0.2: Yes | No |
| Historical dispatch/admin handover | Exact captured model, explicit trusted adoption, no relabeling | historical_v101, allowlist, detector/model controls | Fixed model-handover OpenAPI201/200 declaration | Old implementation computes real Docker fixture; busy/expired fence, two attempts, new cold start, identical historical replay | Yes | Yes | Yes | Yes | No |
| Worker-backed incidents/lifecycle | contracts/incident-api-contract.md; explicit assumed policy | Incident registry/epoch/evidence; atomic persist_plan | Reused A implementation | Live open/update/recovery; exact evidence bindings; unavailable/gap/interrupted/persistence DB tests | Yes | Yes | Yes | Yes | No |
| Independent acknowledgement | Trusted identity, version/idempotency; condition unchanged | incident operations/receipts/event journal | Reused | Live equivalent retry; concurrent version conflict; ack/task/condition independence | Yes | Yes | Yes | Yes | No |
| Durable outbox | A002 supplied-callback, per-incident order, at-least-once/fencing | incident_outbox; immutable event/delivery records | Added real local receiver acceptance | Lost-receipt retry stable event ID/data; all receipts committed; stale claim/order/rollback suite | Yes | Yes | Yes | Yes | No |
| Genuine maintenance | contracts/incident-maintenance-contract.md; one task/incident, active monitored creation | D005 services/schema/routes/history | Reused; retained current creation policy | Live genuine assign/start/complete; retry after recovery; role/binding/conflict/cancellation/history tests | Yes | Yes | Yes | Yes | No |
| Supported sample maintenance | Existing sample contract; untrusted demo label | Existing maintenance routes, D005 compatibility | Reused | Full workflow/migration suite; sample rows preserved; 3 independent mapper tests | Yes | Yes | Baseline: No | Baseline: No | No |
| What-if selection/capture/replay | what-if-api-contract.md; bounded constant load comparison, eligible state | W001 snapshots, server version dispatch, pure B forecast | Removed weak verifier acceptance of unavailable/error as success | Actual200 initialized scenario, points/limit/delta/exact replay; capture binding/immutability and unavailable tests | Yes | Yes | Yes | Yes | No |
| No worker mutation/concurrency | Snapshot insert permitted; no reading/job/result/state edits | Shared stream lock, immutable capture trigger | Added strict live table equality/concurrent actions | Worker/scenario/ack/task concurrency suite and live real HTTP/Docker operations | Yes | Yes | Yes | Yes | No |
| Trusted identity/credential lifecycle | incidents.md CLI; reader/operator/admin, rotation/expiry/revoke | Server token hash/expiry/active lookup | Fixed new file cleanup on database commit failure | Commit failure/no-overwrite regressions; actual Docker CLI/revoked401; full role/expiry/rotation suite | Yes | Yes | Yes | Yes | No |
| Errors/readiness/CORS/log hygiene | Existing versioned incident/What-if and legacy detail shapes | Exception handlers, health DB probe, settings/CORS/logging | OpenAPI correction; removed URL-printing verifier | Actual OpenAPI/live ready; status/role/CORS/sanitization suites; sanitized Compose/log artifacts | Yes | Yes | Candidate routes: Yes | Candidate routes: Yes | No |
| Migration/preservation/recovery | Additive D006 join, sole head, populated graph; retain history | A001/A002/D005/W001/D006 | Added actual dump/restore acceptance; no new migration | Fresh upgrade/check; 9 populated combinations; D004 nine-table hash rehearsal; full public-table restored hash equality | Yes | Yes | Yes | Yes | No |

## Explicitly proposed or outside this accepted scope

| Proposal | Status/decision | Why it is not a missing agreed backend feature |
|---|---|---|
| Global /events, shared queue/WebSocket, configured production publisher | Proposed generic event contract; supplied callback only implemented | No accepted transport or recipient contract; local receiver verifies implemented outbox semantics |
| Production OAuth/SSO, producer credentials, asset tenancy/operator directory | Outside local trusted-operator contract | No approved provider/tenant policy; registry/telemetry remain existing local API |
| Health/confidence/fault probability/RUL/calibrated fault classification | Unavailable, explicitly not estimated/assessed | No reviewed validated model or physical calibration; residuals are not faults |
| Cooling intervention forecasts/multisegment optimizer | Outside reviewed constant-load healthy-model scenario | No accepted cooling/control equation or intervention policy |
| New task creation from recovered/interrupted incidents | Precise unresolved optional policy: current implementation returns409; equivalent existing-task retry still200 | D handoff proposes authenticated historical investigation with reason/audit/UX; A/C have not accepted it; current contract is preserved |
| Physical field accuracy/calibration and production readiness | Not established | Synthetic assumed coefficients and representative local tests do not establish accuracy or operational readiness |
| Genuine frontend browser E2E | Separate C review gate | This backend task ran affected frontend contracts/lint/build; it does not certify new UI browser workflows |

No outstanding implementation blocker was found within the bounded contracts
above. Combined-source approval, exact-head hosted checks and any deployment
remain separate open gates; no earlier phase percentage or reviewer-attribution
claim substitutes for those gates.
