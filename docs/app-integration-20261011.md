# Person D combined application verification — 11 October 2026

The integrated application passed independent native PostgreSQL, automated and actual Google Chrome verification. This is a review candidate on `codex/persond-app-integration-20261011`, not merged main or a deployed service. Docker verification remains unresolved.

## Exact source and adoption

| Source | Full SHA | Observed state |
| --- | --- | --- |
| Tested application | `2b140d70a2660830a7e7002a31f41621e2f5686d` | Final responsive integration source; backend/migrations/analytics identical to the backend runtime below |
| Backend runtime | `52053168475aac45a112bc122b1fa8fe87cfd775` | Includes registry, Model1.0.2, D005/D006, outbox, What-if and prior compatibility fixes |
| Latest A branch / draft PR34 | `fae21510c83e2595708078df39f6468b70cfb2a0` | Adds three reports only; no runtime difference from `5205316` |
| C authoritative frontend | `4b5709d9857350d405dc0de21c7af3b8d1f09a5e` | Only this frontend commit adopted, with conflicts resolved, as `2baf48768740709364667a9814cfa568a68ea7d5` |
| Fetched main | `744c76538235e7d04da250fcfdcf4f7a8d6e9218` | Does not contain the complete backend candidate |

C's branch also contains unrelated B computational ancestry. Merging the entire branch would adopt work outside this frontend integration. Its frontend commit was cherry-picked; no teammate branch or published revision was changed. There were 24 frontend conflicts: C's workspace/navigation/data presentation was retained, while A's `BackendMaintenance.jsx`, `maintenanceApi.js` and `maintenanceAdapter.js` were retained to preserve implemented genuine and sample task contracts. The D proposal from superseded PR10 is not mounted alongside a second maintenance screen. The independent sample mapper remains a verification tool.

PR26 is merged into main (`cbdd7c47f8cf5aa66d0277f5fa96d69bfb01ddda`). PR27 is merged into the registry branch (`2e934c85098453db7342ea6ade570759ef4b9161`) and is an ancestor of this backend. Their CI/docs fixes were inherited, not applied again. PR34 is draft, targets main and had no reviews at inspection. PR29/32/33 remain open despite their implementation being incorporated into A's candidate. Do not merge their overlapping patches again without inspecting net diffs.

Draft [PR36](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/36) targets `feature/backend-completion-20261011`, as explicitly permitted by this integration request, so its review contains the frontend integration and D verification only. Once A's exact prerequisite history reaches main, retarget D to main, inspect the resulting net diff, and obtain exact-head green CI and teammate approval. Do not treat a stacked PR as independently mergeable to main today. A and C should review the frontend adoption together rather than also merging the whole C branch.

Automatic approval review rejected merging A's documentation-only advancement into D, citing the restriction on merging A-owned work. That merge was not performed. This does not block the integration: the latest backend runtime is byte-for-byte identical, and the reports remain on A's branch. This report records independent observations; it does **not** endorse the incorrect audited SHA, `assigned` status, blanket deployment acceptance or attributed D sign-off in A's new `persond-qa-acceptance-final.md`. A should correct that report before PR34 is merged. No GitHub review was submitted by this task.

## What changed

- C's digital twin, fleet, reading/history inspection, condition explorer, theme and navigation remain authoritative. Missing `src/lib` helpers are now tracked; the root `lib/` ignore previously omitted them. Rendering/export tests preserve canonical identifiers and sample provenance.
- The workspace discovers implemented capabilities through the connected runtime's OpenAPI and mounts the existing incident, What-if and maintenance components. All clients use the selected API origin and asset/source/run context. A returned task opens in maintenance by its backend UUID.
- Local prototype bearer credentials are checked through `/api/v1/operators/me`; credentials are scoped to the API origin, kept in session storage, and cleared on expiry/revocation. Reader mutation controls are disabled. This is not production SSO.
- Selected stream context survives refresh. Incident and task conflicts require explicit review, retain drafts where applicable and do not automatically overwrite a newer version. Acknowledgement retries retain their idempotency key after transport failures. Incident list/events/evidence, maintenance/history and reading pagination use actual backend contracts.
- Previous forecasts clear when inputs/state change. Fatal pending analytics refresh clears stale derived estimates while retaining usable telemetry. Sample illustrations, simulator inputs, assumed coefficients and local identity are explicitly labelled.
- Final visual review found anonymous authentication form overflow on narrow screens. The form now wraps within the workspace; a settled anonymous390px Chrome check passes. Screenshots wait for the previous navigation view to detach rather than recording overlapping transition frames.
- The live incident verifier uses the runtime's supported `MODEL_VERSION` instead of hard-coded historical1.0.1 for newly selected streams. Historical dispatch remains covered by the backend/contract suite.

No backend API, computational model, database migration, shared contract or development environment file was changed. No acknowledgement is inferred from task completion, and no task status implies incident recovery.

## Executed checks

Raw logs, exact commands/exit codes and SHA256 file hashes are in [the evidence manifest](app-integration-evidence-20261011.json) and [dated evidence directory](evidence/app-integration-20261011). No credential files, token values or authorization headers are included.

| Execution | Result / scope |
| --- | --- |
| `python -m pytest backend/tests analytics/contracts -q --tb=short` | **354 passed**, 392 warnings, 137.28s; isolated PostgreSQL18, Python3.13.14 |
| `npm test` | **99 passed**, none skipped; Node24.19.0 |
| `npm run lint`; `npm run build` | Both exit0; production build configured for isolated live API |
| `node --test integration/frontend/maintenanceAdapter.test.mjs` | **3 passed**; independent sample compatibility |
| Alembic fresh `upgrade head`, `heads`, `current`, `check` | Exit0; soleD006; no new upgrade operations |
| Populated migration suite | Supported historic revisions and all combinations of A002/D005/W001; concurrency and metadata checks passed as part of the354-test execution |
| Dedicated populated D004→D006 rehearsal | Exact historical column/value hashes preserved across **9 tables**, one representative row per table |
| Live incident-maintenance verifier and `--resume` | Actual HTTP/worker, independent acknowledgement/recovery, sample compatibility, duplicate/terminal retries and post-restart task/incident/history equality: exit0 |
| Live What-if verifier | Snapshot immutability, state reuse, watermark advancement, missing limit/null reasons and versioned errors: exit0 |
| Normal separate worker CLI | Processed **22** appended labelled readings; no direct call to `run_once` in this check |
| Actual Google Chrome154.0.8037.98 | Full ten workflow groups on committed application source, plus four auth/error checks and historical/event/evidence pagination: exit0 |
| `docker info` | **Exit1**: Linux engine pipe unavailable. No Docker image build/runtime or shared deployment claimed |

The full backend/contract suite ran during integration against the unchanged backend tree at5205316. It was not rerun merely to change the enclosing commit hash: `git diff 5205316 -- backend analytics .github` is empty. Final frontend tests/build and the repeated full Chrome workflow use exactly the application code in2b140d7, including the responsive authentication correction. The earlier64c32cf run is retained as historical local evidence. Subsequent publication commits add only verification docs/evidence. Hosted PR CI is recorded separately in PR36 on its published head; it does not replace these browser executions. The earlier6c820c8 CI run passed both jobs and is not counted as CI for a later head.

Chrome used an owned fresh profile and the production preview at15882 with the real API at15881. The ten groups covered registered assets/readings/analytics/history; worker-created incident evidence; task creation from incident; assignment, start and required completion notes; required cancellation reason; task409 with retained draft/blocked saving/explicit review; incident409 refresh; reader permissions; sample task/history pagination; What-if capture/reuse and stale clearing; refresh/session restoration; actual offline error while the owned backend was stopped; restart persistence; and mobile navigation without horizontal overflow. Additional Chrome execution verified invalid credentials, actual404 unknown snapshot, expiry and revoked-token401. A separate read-only run traversed25 readings and more than20 incident events/evidence records, including historical inspection and return to latest. The workflow uses genuine persisted incident/task identities produced from **synthetic representative telemetry and assumed detector rules**, not field incidents or physical validation.

## Preservation and migrations

The unchanged migration graph has one head:

```text
a002_incident_outbox ────────┐
d005_incident_tasks ─────────┼── d006_combined_integration (no DDL)
w001_what_if_snapshots ──────┘
```

The9-table D004 rehearsal checks original columns explicitly, including configurations, telemetry, jobs, results, streams, states, sample tasks and history. Existing sample tasks retain null incident linkage. The combined suite also checks populated individual/combined parent states and concurrent operations. Neither published migrations nor historical records were rewritten; no extra merge revision was generated.

Before/after the final actual backend restart, **all19 database tables** had identical explicit-column row counts and SHA256 hashes. The earlier commentary count17 was incomplete; the committed snapshots are authoritative.

| Table | Before | After |
| --- | ---: | ---: |
| assets / asset_configurations | 7 / 10 | 7 / 10 |
| telemetry_readings / telemetry_processing_jobs / analytics_results | 47 / 47 / 47 | 47 / 47 / 47 |
| analytics_streams / analytics_states | 7 / 10 | 7 / 10 |
| incidents / incident_events / incident_evidence | 11 / 76 / 67 | 11 / 76 / 67 |
| maintenance_tasks / maintenance_task_history | 94 / 206 | 94 / 206 |
| what_if_snapshots | 6 | 6 |
| detector_controls / detector_epochs / incident_deliveries | 6 / 6 / 76 | 6 / 6 / 76 |
| incident_operations / incident_operators / alembic_version | 15 / 3 / 1 | 15 / 3 / 1 |

These are **synthetic QA database** comparisons. No development backup was read/restored, no development migration or restart was performed, and no claim is made about preservation of all development/production records. Credential expiry/revocation tests deliberately changed only owned QA operators outside the restart comparison.

For any later authorized deployment, A must first back up and inventory the actual target database, pin reviewed application/image identities, quiesce writers/workers, and rehearse its current revision in a separate restored database. Apply the complete immutable graph with `upgrade head`, checkD006/schema consistency and compare original fields. Resume only after checks pass. On failure retain logs/database/backup; stop new writes and have A approve recovery. Do not downgrade blindly, restore over a live database, delete volumes, or substitute representative QA hashes for a real backup comparison. No deployment/recovery action was executed here.

## Remaining gates and owner decisions

| Gate | Owner / next action |
| --- | --- |
| PR34/backend prerequisites unmerged | A: reconcile overlapping PRs, correct attributed blanket sign-off, review exact source and merge only through team policy |
| Frontend adoption / D draft | C+A: review C commit adoption, conflict choices, context/auth UX and actual integrated workflow; one authoritative frontend adoption |
| Recovered/interrupted **new** task policy | A/C: retain current409 fail-closed. Equivalent retry of an existing terminal task is allowed; a new historical investigation requires an explicitly reviewed actor/evidence/reason/lifecycle contract before implementation |
| Docker / shared deployment | A/D: provide an available engine and rerun isolated build/runtime/preservation with separate ports/database/volume; current native proof is not Docker proof |
| Production identity / physical validation / shared transport | A and relevant owners: production SSO, physical calibration and shared ingestion/delivery acceptance remain separate; prototype credentials/synthetic streams do not satisfy them |
| Fresh merged-main verification | D: repeat appropriate integrated smoke/CI once the exact prerequisite history actually reaches main |

## Ready-to-send handover (not sent)

Person D's combined app candidate in draftPR36 retains C's rebuilt workspace and connects it to the implemented backend incident, What-if and maintenance contracts. Backend354, frontend99 and sample mapper3 tests pass; lint/build, migrations and populated preservation pass. Actual Chrome completed incident-linked tasks, independent acknowledgement, owner/status/required notes, conflicts, pagination, expiry/revocation/error handling, refresh and real backend restart. All19 isolated table hashes/counts match across restart. Source2b140d7 uses backend5205316 (identical runtime to A's currentfae2151) and C frontend4b5709d. The draft is stacked on A's backend; review that dependency, then retarget only after it reaches main. C: review the frontend adoption and UX. A: review backend/migration prerequisites and correct the blanket D acceptance attribution in your new report. Docker/shared deployment, production SSO/physical validation and the new recovered/interrupted investigation policy remain unresolved. No teammate branch, main or development database was modified, and nothing was merged/deployed.
