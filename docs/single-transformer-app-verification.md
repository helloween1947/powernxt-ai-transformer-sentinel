# Single-transformer application verification

**PASS** for the bounded isolated Windows demonstration. Tested application source: `ffbdfbb81d00af0fb89f397ae4c00b55991f7506` on `feature/single-transformer-app-20261011`. Verification recorded 2026-10-10T21:11:51.683Z (Asia/Kolkata: 2026-10-11 02:41:51 GMT+5:30). Publication commits after this source add evidence only. See [structured evidence](single-transformer-app-evidence.json) and [startup guide](single-transformer-app-guide.md).

## Actual source and isolation

PR36 remains open/draft at493092ee1fbca71245c8f4e3e01f81df134bded5, targeting feature/backend-completion-20261011. The owned worktree started at this exact commit, then incorporated current backend dependencyfae21510c83e2595708078df39f6468b70cfb2a0. Both are ancestors. Its backend runtime matches52053168475aac45a112bc122b1fa8fe87cfd775; that dependency advancement adds three reports only. No backend/model/migration/contract equation was changed. Inherited sign-off attribution remains unendorsed and requires owner review.

The original checkout stayed on main744c76538235e7d04da250fcfdcf4f7a8d6e9218, with its local/untracked work preserved. Existing development assets were inventoried read-only; no supported all-record provenance-preserving copy procedure was used. The separate application database was seeded fresh with exactly one deterministic transformer through supported APIs. Other development transformers and records were untouched.

Project: `powernxt_single_71a55838`; frontend http://127.0.0.1:18300; API http://127.0.0.1:18301; retained PostgreSQL on loopback18302. The normal development API8000, database and worker were never restarted or migrated. The complete isolated stack remains running for review. Private settings and prototype credentials are ignored under data/generated/single-transformer; they are excluded from this evidence.

## Executed checks

| Check | Actual result |
|---|---|
| Backend/analytics contracts, separate test database |354 passed;393 warnings; exit0;182.50s |
| Frontend tests |100 passed,0 failed/skipped; exit0 |
| Frontend lint |exit0 on final source |
| Host production build and final Docker production frontend build |exit0; ordinary Dockerfile builds, cached layers allowed |
| Independent sample maintenance mapper |3 passed, exit0 |
| Fresh migrations/current/check |Sole d006_combined_integration; exit0; no new upgrade operations |
| Documented Windows startup helper |Actual execution exit0; seeded six identical retries without extra default records |
| Durable worker QA |6 completions,6 identical retries; final QA8 readings/jobs/results; state advances1,7; abandoned claim completed on attempt2; worker restart preserved exact hashes |
| Actual installed Windows Chrome154.0.8037.99 |Final exit0;7 workflow groups; no injected responses; no page errors |
| Documented full-stack shutdown/startup |Both exit0;19 table counts/hashes unchanged after retained-volume restart; application left running |
| API stop/restart |19 table counts and explicit-column SHA256 hashes exactly unchanged; browser offline error and recovery |

Backend tests use single_transformer_contract_test, separate from application data. Logs/checks.json record actual commands/exits; final frontend/startup/browser logs supersede initial runs where relevant. Database totals are **one asset, one configuration,21 readings/jobs/results**, two incidents, two genuine tasks and one immutable What-if snapshot. The21 records comprise six default readings, seven retained readings from the interrupted first worker QA attempt, and eight from the successful QA run. No records were deleted to tidy a failed verifier attempt. QA runs remain isolated from the default chart.

## Default stored thermal results

Asset `powernxt-single-transformer`, source `simulator`, run `single-transformer-demo-v1`, configuration1, model `stored-reading-top-oil-1.0.2`. All six electrical results preserve exact model/parameter/stream/reading/time provenance. Thermal residual is measured minus predicted oil.

| Reading | UTC measurement time | Measured oil (C) | Predicted oil (C) | Residual (C) | Elapsed (s) |
|---|---|---:|---:|---:|---:|
| 1 | 2026-10-10T12:00:00Z | 55.000000 | Unavailable | Unavailable | Initialization |
| 2 | 2026-10-10T12:01:00Z | 55.000000 | 55.253752 | -0.253752 | 60 |
| 3 | 2026-10-10T12:02:00Z | 55.000000 | 55.506098 | -0.506098 | 60 |
| 4 | 2026-10-10T12:03:00Z | 55.000000 | 55.757047 | -0.757047 | 60 |
| 5 | 2026-10-10T12:04:00Z | 55.000000 | 56.006605 | -1.006605 | 60 |
| 6 | 2026-10-10T12:05:00Z | 55.000000 | 56.254780 | -1.254780 | 60 |

Initialization reason: initialized_from_measurement_prediction_not_independent. Latest analytics references reading6. Ratings, operational limit and thermal parameters are assumed; telemetry/detector policies are synthetic. Residuals are not fault labels or physical calibration. Missing oil level/unsupported health/confidence remain unavailable.

## Actual browser workflows

Monitoring/condition/trends/reports consistently show the fixed asset and shared stream; electrical/thermal values come from actual stored responses. Bootstrap prediction is a chart gap. Configuration/model grouping has a mixed-provenance regression. Historical records remain individually inspectable. Fleet navigation is absent.

Chrome created genuine incident-linked tasks through the UI, assigned an owner, started/completed with required notes, validated cancellation reason, and acknowledged independently. Those operations completed in the trace browser-lifecycle-partial.json; that run subsequently failed only because the verifier incorrectly expected the UI to include the literal401. The final browser run verifies the retained terminal tasks and their exact incident/asset bindings, rather than rewriting them. This partial trace is explicitly labelled FAIL, with its completed checks retained; it is not presented as an overall passing run.

Final Chrome verifies actual HTTP401 plus visible authentication errors, reader mutation controls, session/stream refresh, real API stop/restart and browser network-offline recovery. What-if uses eligible immutable state, reuses the exact state reference and clears stale results on changed inputs; all reading/job/result/state/stream/configuration hashes are unchanged. Empty device selection has no fabricated telemetry/forecast and returns state_unavailable, then reselecting the default simulator restores six records. Light/dark screenshots and390px reduced-motion navigation were executed; no horizontal page overflow or page errors were observed. This is headless actual Chrome/responsive emulation, not a physical phone or visible manual-browser check.

## Corrections and limits

Initial isolated frontend readiness failed because localhost resolved to IPv6 for an IPv4-only Nginx listener; the health probe now uses127.0.0.1. Seed-helper assumptions about UUID format and configuration retrieval were corrected against actual schemas/OpenAPI. Rejected requests created no readings; subsequent retries used stable identity. A blocking Docker operation exposed a stale verifier HTTP keep-alive socket; Connection:close corrected only the verifier, and the seven already accepted readings were retained. Locator/401/snapshot-reuse assertions were corrected to the actual response/control semantics, without changing application/model behavior to manufacture passing results. A final Windows encoding edit was caught by lint and repaired before the final source build/Chrome pass.

No credentials, full database URLs, auth headers, secret files or development backups are in published evidence. The publication inventory was checked against every private token/password without printing them. No deployment, main/teammate branch change, merge of PRs or review message occurred. The owned integration branch contains a dependency merge only; no teammate branch was modified.

Physical validation/calibration, production SSO, review of backend/integration dependencies and coordinated A/C/D adoption remain required. Existing recovered/interrupted incident task creation policy is unchanged. Hosted CI status must be assessed for the exact published head and is not inferred from predecessor PR36.
