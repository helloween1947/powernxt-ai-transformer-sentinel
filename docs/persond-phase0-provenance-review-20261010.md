# D evidence correction and independent provenance review — 10 October 2026

This is an additive correction, not a replacement for historical reports. Main
inspected is `cbdd7c47f8cf5aa66d0277f5fa96d69bfb01ddda`. Development maintenance
upgrade is reported complete by the supplied plan; its running source/database
identity was not available here, so no new deployment verification is claimed.
Portable executed/source evidence: [dated manifest](persond-phase0-provenance-evidence-20261010.json).

## Phase0: disputed thermal preservation claim is unresolved

The original [Windows demonstration](integrated-demo-verification.md) records
asset `demo-normal-85203b1018bc498c8b90873f383cc740`, simulator run
`thermal-144c79522cbd4cd092b7718fea4b05fe`, configuration2/readings20–25.
The portable audit supplied by the user names the same selection, but supplies no
complete stored-result response bodies or original-to-new record snapshots.

| Reading25 quantity (C) | Original 9 October report | New values quoted in the supplied plan |
| --- | --- | --- |
| Predicted top oil | 45.080790 | 46.351297 |
| Residual, observed minus predicted | -0.402153 | +0.648703 |
| Observed oil | 44.678637 (recorded) | 47.000000 (inferred from the quoted pair) |

The prediction differs by1.270507C, residual by1.050856C, and implied observed
oil by2.321363C. These cannot be identical envelopes under the documented residual
formula. The inference is arithmetic, not a new model execution or stored value.
The new quoted pair is in the supplied plan; it is not present as a full response
in the earlier supplied portable audit manifest.

Correction: **cross-report preservation has not been established**. The portable
audit's `development_preservation.status=PASS`, unchanged_paths and empty differences
describe its claimed within-audit before/after comparison. They do not establish
equality with the original saved9 October envelopes, and cannot independently
explain the new quoted values. No statement of “100% identical” should span those
two sequences. Preserve the original reports and qualify the claim with its exact
source snapshots, database/stream and comparison interval. Do not infer corruption,
changed data, a reporting typo or a different database without those artifacts.

Missing Phase0 evidence, owned by A: old/new complete GET envelopes for every
reading20–25 and latest-completed response; exact reading/result/message identities,
UTC measurement/storage clocks, configuration snapshot/provenance, source/run and
model/parameter versions; available before/after database snapshots or record
digests; API origin, database identity and snapshot/backup identity; running backend/
worker image/source SHA and current migration. B should compare the actual selected
inputs/previous-state/model identities; C should check the same selection's exact
API/UI values. Do not replay jobs, change evidence, relabel results or overwrite data.
The discrepancies cannot be closed from laptop-local numeric IDs alone.

## Phase1: independent PR28 review

Reviewed exact head `23ab1b6ff825bc46140d5994ee3e01ddc5aad9c5`, draft against
main. Net diff: five frontend files,+346/-1; no equivalent guard is on inspected
main. GitHub reports mergeable; submitted reviews and comments were empty.
Both hosted jobs passed on that exact head, independently observed through GitHub
([run38052359720](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/actions/runs/38052359720)).

Within this scoped guard no blocking defect was reproduced. Both adapters require
nonblank string model_id/model_version/parameter_version and exact outer/payload
metadata equality for stored result objects. They accept matching future identities;
they do not pin1.0.1 or relabel state. Pending/null remains usable. Existing stream,
reading/configuration/time and unit checks remain. This is not exhaustive untyped
payload-schema validation or proof of future backend model adoption.

Fresh independent execution on the exported exact source: `npm ci`, declared
`npm test` (**41 passed**), `npm run lint`, `npm run build` passed. No unsupported
watch flags, test-collection-only result or old CI run is counted as execution.

Actual installed Chrome ran C's unmodified `frontend/tests/provenanceBrowser.cjs`
against isolated API15451/preview15452, backend source matching main. Real GET
responses verified six chronological ID-joined values, signed residuals, bootstrap
nulls, C units and both endpoint identities. Screenshots were inspected. Eight
separately labelled fixture checks exercised contradictory/missing/blank identities
on both endpoints, rejected/stale analytics clearing, retained telemetry, matching
future identities, pending/null and recovery to actual responses. Fixtures are not
backend defects or real stored results. All public-schema record digests matched
before/after this browser execution; no writes were made by the browser.

This D run used a **new isolated synthetic** stream, not A's disputed stream or
C's other-laptop preview: asset `d-provenance-synthetic-f8483656c86742d189874c3267cdbabc`,
run `d-provenance-finite-984b749d2e5e448193757bcae1817767`, configuration2/readings7–12.
Matching numbers7–12 do not identify C's database. Setup appended explicit assumed
thermal parameters and fresh messages only in D's new database; it did not recompute
earlier data. The earlier coefficient-free stream remains unavailable and retained.

Artifacts are in the primary checkout's ignored `.venv/persond-provenance-1d84ba56eb964c5aa4f6310a515ba309/`:
`frontend-tests.log`, lint/build logs, `selection.json`, full actual source envelopes,
`browser-final/provenance-browser.json`, real API bodies/screenshots and
`browser-preservation.json`. C's supplied manifest under `C:/Users/Akash Patil/...`
was unavailable on this machine; no claim is made to have inspected its raw files.

Setup failures are retained separately: copied historical migration fixtures had
empty parameter provenance, so registry serialization rejected those artificial
rows; that restored copy was retained rather than edited. A first fresh stream
correctly lacked predictions because its sample configuration had no coefficients;
a separate new assumed-coefficient configuration/run was appended. A harness initially
used telemetry history `reading_id` instead of contract `id`. Initial Chrome failed
because15452 was absent from process-local CORS; the isolated API was restarted
with the matching origin and the same assertions passed. None is counted as a pass.
Environment files were untouched, and only task-owned preview/API processes stopped.

## Adoption and migration review remain separate gates

A's new source candidate is `35d21edca689385ef8bf032c025848b8cae2b5fa`, based on
registry `2e934c85098453db7342ea6ade570759ef4b9161`, which already contains PR25/27.
This is not main or a deployed model. A's documented decisions include retained
historical1.0.1 dispatch, explicit admin handover/new namespace/epoch/cold start,
interrupted monitoring without physical recovery/implicit acknowledgement, and
snapshots selected by actual source state version. B's policy approval is not inferred.

Fresh D execution of the exact unmodified candidate produced **350 passed/one
failed**, not a green final result. Failure: `test_existing_stream_blocks_without_mutating_jobs_and_other_stream_progresses`
used a date-only SQL subquery; PostgreSQL timezone Asia/Calcutta made both UTC
readings satisfy it, causing CardinalityViolation. The failure is in a test query,
not proof of a broken transition. D's [draft PR30](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/pull/30)
targets A's adoption branch and binds the blocked reading's actual receipt ID,
preserving the attempts==0/no-mutation/independent-stream assertions. Exact test
source is `508c7b1f8d6d76f7e74e47262bfb446a05bbe782`; the full fresh suite passed
**351 tests**, 392 deprecation warnings, in153.27s on Python3.13/PostgreSQL18,
timezone Asia/Calcutta. This single execution includes transition/version dispatch,
old capture/result/state preservation, unsupported versions, populated migration
combinations and concurrency coverage. Fresh Alembic upgrade/heads/check also passed
with sole D006/no metadata operations. Hosted exact-head checks are reported in
PR30 independently. No A branch was modified or model adopted into main/runtime.

The source retains D006's no-DDL A002/D005/W001 join and explicit-column populated
preservation/concurrency tests. D restored a native backup of retained QA data into
a **new** database and verified equal all-table record digests; the original remains
unchanged. That is a native backup/restore rehearsal, not a development backup or
Docker populated upgrade. Docker is still unavailable here; no normal image build,
container restart or combined frontend/adoption-runtime verification is claimed.
PR29's Docker runner and review gates remain separate pending work.

Recovery is application rollback/forward repair with additive data retained and
reviewed schema compatibility. Restore a verified backup into a new database;
never blindly downgrade populated history or overwrite post-backup records.
A single restart is controlled interruption evidence, not zero-downtime proof.
What-if is reduced-load comparison, not cooling-intervention prediction. A request
does not convert existing1.0.1 state into1.0.2; captures must retain their actual
selected state's model version. Recovered/interrupted new-task creation remains409;
equivalent terminal retries and independent ack/task/condition remain intact.

No PR merge, development deployment, teammate message or automatic GitHub review
approval occurred. A/B must review adoption; A/C must review runtime and future UI;
production SSO/shared transport/physical calibration remain separate limitations.

Ready-to-send: D independently verified PR28's exact source with41 tests/lint/build
and actual Chrome real-response plus labelled-fixture checks. Please review it for
human approval. Phase0 remains blocked on A's old/new complete response/snapshot
artifacts; the two quoted reading25 sequences cannot be identical. PR30 fixes a
timezone-sensitive adoption test assertion without changing runtime behavior.
Do not deploy combined changes until exact-source checks, Docker rehearsal and
required A/B/C reviews are complete.
