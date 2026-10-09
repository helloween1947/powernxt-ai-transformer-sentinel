# Independent verification of PR13 — 9 October 2026

Repository is the existing Windows checkout. Initial persond working tree was
clean. No teammate branch, main, application database or volume was changed.

## Exact reviewed inputs and prepared result

- main: `9d2f9cda817bc6312d00a4fc001050b04b85a2cb`.
- persond before this documentation update: `05cefcc339a72143ec7a683255df08b5143e53ce`.
- PR13 / A's fix branch: `13cbb80f80d53e7b49a026c3bb986e12c9e7203e`.
- Integration refresh parent: `b2da162` incorporates already-merged main; its
  worker/audit/simulator changes explain the broad PR13 comparison with persond.
- Focused `13cbb80` fixes registrations, D004, finite JSON and review checks.

The exact current persond + PR13 combination merged without conflicts into an
isolated checkout `../persond-13-verification` on local D-owned branch
`codex/persond-13-verification`, with `--no-commit`. Its proposed merge is
preserved for review. This is not incorporation into persond or a merged PR.
No implementation defect requiring a new fix was found. Main remains an
ancestor of the tested PR13 branch; D004 is sufficient for its current graph.

Both analytics and maintenance routers remain registered. Alembic metadata
imports worker results/state/streams and maintenance task/history models.
D001, D002 and D003 are byte-identical to their published counterparts. D004
joins `d730a91b4c22` and `d003_audit_maintenance` with no DDL/data operation.
Maintenance POST/PATCH use the existing finite-JSON dependency; NaN, positive
and negative infinity and overflowing exponents return 422 rather than 500.

## Independently observed checks

Windows Python3.13 and existing isolated native PostgreSQL18, loopback port55432:

| Check | Observed result |
| --- | --- |
| Full backend suite in exact proposed combination | 222 passed in 52.81 seconds |
| Fresh uniquely named database upgrade | Passed; only this newly created database removed afterward |
| Eight schema upgrade states: fresh/84/ce21/D001/D002/old dual heads/D003/d730 | Passed |
| Existing assets/configuration/readings/jobs/task/history values | Preserved |
| Populated worker results/state/streams and maintenance/history | Preserved |
| Model/schema consistency via Alembic check | Passed |
| API registration and allowed/rejected CORS origins | Passed |
| Eight POST/PATCH nonfinite-input cases | Returned 422; passed |
| Alembic heads | Exactly d004_worker_maintenance |
| Offline upgrade head SQL generation | Exit 0 |
| Maintenance mapper Node suite | 3 passed |

All destructive cleanup was limited to newly generated test schemas and the
uniquely created fresh test database. Preserved application databases and
volumes were not removed, restarted or migrated. No browser/Docker deployment
success is claimed in this backend-only verification. The temporary native
PostgreSQL test server was stopped after verification, retaining its data.

A's earlier reported 222 tests used PostgreSQL16. The 222 above are D's new,
independent run on PostgreSQL18; they are not a restatement of A's evidence.
Earlier PR9 CI successes at 087a884 and earlier 173 tests are historical and
cannot verify the currently proposed integration or latest main.

## Approval and current PR9/CI status

CONTRIBUTING.md section 2.5 requires: "Require **at least one teammate review**
and approval before merging." The user's authorization is expressly conditional
on repository policy. PR13 had no submitted reviews/approvals at inspection;
A's authored fix/report is not an explicit approval of its incorporation.
Therefore no merge into persond is made. The exact remaining prerequisite is
one teammate review and explicit approval of PR13's reviewed changes. Any newer
head must be rechecked before incorporation. Nothing was force-pushed.

Only this verification documentation is committed/pushed to persond. PR9's
published implementation still lacks PR13's current-main registration fixes and
D004, and GitHub reports conflicts against main. No new integrated persond
commit exists on which to claim green hosted CI. After approval, normally merge
PR13 into persond, push, and verify PR9 CI on that exact resulting commit before
it is declared merge-ready. PR9 remains draft and ready for human review of the
verified proposed fix, not ready to merge into main. PR13 is not merged either.

## Frontend ownership and remaining prerequisites

D's PR10 component/client/mount proposal is **superseded by C's maintenance
screen in PR12**. Keep PR10 open until explicitly instructed otherwise. Do not
retarget it automatically, apply its patch alongside C's screen, or duplicate
C's implementation. Historical PR10 Chrome results are not validation of C's
new screen or merged main.

- C dashboard PR1: open, unmerged, head `72acc3bd60842d70af0c922c370f4351fb2e4a7d`, base main.
- C API PR5: open, unmerged, head `e87a8856e9323c88854147c5ed7d4f54c336ba9e`, base feat/frontend-setup.
- C maintenance PR12: draft, unmerged, head `4941d2fdc39679b691a8bb15e308b388000084ba`, base feat/frontend-api-integration.

C owns how its stacked changes reach main. Backend PR9 can proceed independently
once PR13 incorporation/CI/review requirements are satisfied. After backend and
C's frontend reach main, test C's actual screen for workflow, conflicts, errors,
refresh and backend restart. Genuine incident registry/provenance and trusted
operator identity remain unimplemented; X-Demo-Actor and sample alerts remain
labelled prototypes.

## Ready-to-send review request (not sent)

A/team: D independently verified PR13 at 13cbb80 against current main9d2f9cd:
222 backend tests passed on native PostgreSQL18, including fresh DB/eight upgrade
paths, preserved worker/task/history records, metadata, CORS/routes and nonfinite
JSON422; single head D004. No new code fix was needed. CONTRIBUTING requires a
teammate review and approval before merging, and PR13 has none, so it is not yet
incorporated into persond. Please review/approve the exact fix; after approval
we can normally merge it into persond and verify PR9 CI on the new commit.
C's PR1/5/12 remain unmerged. D's PR10 UI is superseded by C's maintenance screen;
its mount will not be applied alongside C's code. No PR was merged into main.
