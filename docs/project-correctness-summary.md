# Correctness delivery summary

Branch `audit/correctness-fixes` contains current fetched main `f35d268cda49d81fac7463d8a5082cb5b1c1bc98` plus the reviewed validation, immutable-configuration migration, environment-example, Docker-context and simulator-documentation corrections.

New Linux verification: **128 backend tests passed**; populated isolated migration downgrade/upgrade preserved every existing row; UPDATE/DELETE guards, new versions and retries passed; registry, telemetry and simulator integrations passed with normal isolated restarts; Alembic current/check and offline SQL passed. The executed image reused installed dependencies. A separate fresh normal Docker build progressed from DNS failure to proxy certificate-chain failure and remains unresolved. GitHub PR/hosted CI access is Forbidden. No review/CI success is inferred.

Development services, `.env`, unrelated edits and database volumes were preserved. No development migration, deployment or merge occurred. The isolated test stack is stopped with its data retained. No Windows execution is claimed in this delivery.

See [new detailed evidence and preserved audit](project-correctness-audit.md), [machine-readable evidence](project-correctness-evidence.json), [prepared draft PR](correctness-fixes-pr.md), and [exact post-review Windows commands](correctness-fixes-windows.md). Source hashes in the evidence identify executed runtime/migration bytes; the pushed branch commit identifies the delivery. No analytics or frontend contract expansion was made.

## Historical summary — October 8 (retained verbatim)

# PowerNXT Transformer Sentinel — correctness summary

**Audit:** 2026-10-08T23:49:28.157673+05:30, Asia/Calcutta (IST), Linux cloud. [Detailed report](project-correctness-audit.md) · [Structured evidence](project-correctness-evidence.json).

## Verified current state

- Registry, telemetry and simulator are merged into main `f35d268…` (simulator PR6). Tested simulator/source base is `55a9c54f44f9f7dc6cdc437438bce9fcc11c1bba`, with the identical source tree as main.
- Newly reran **115 baseline backend tests** and **127 tests on the final local audit fixes**, using isolated PostgreSQL schemas. Concurrency, duplicate conflicts, atomic job rollback, run/time/config isolation and migrations have meaningful assertions.
- All three documented integration scripts passed on a **separate Docker audit stack**. Registry and telemetry survived normal restarts there; six simulator readings produced six pending jobs and six identical retries without duplicates, correct latest/history and empty device history. Regeneration passed byte-for-byte.
- B's unmerged branch `35a8c64…` has real prototype electrical/top-oil functions and conservative stored-reading computation. Its combined suite passed **161 tests** with simulator review enabled. This is pure computation, not a deployed job consumer.
- C's unmerged integration branch `a554786…` passes lint/build and **six adapter tests**; an actual API response also passes its adapter. Backend readings matches current routes and preserves nulls/quality/pending. Browser integration remains unverified.

## Defects fixed locally

| Confirmed problem | Local correction |
|---|---|
| Boolean/string ratings accepted as physical numbers | Strict finite numeric configuration fields |
| Extreme timezone normalization raises uncaught overflow | Validation error/HTTP422 |
| Nonfinite registry JSON returnsHTTP500 | Shared finite-JSON guard/HTTP422 |
| Direct SQL can rewrite configuration history | Append-only row guard migration `ce21c3b8140a` |
| Broken CORS example and wrong host DB port | JSON origins; host5433 in template/default |
| Docker exclusions outside active build context | Root `.dockerignore`, exercised with real canary build |
| Phase-offset versus phase-spread wording | Clarified synthetic documentation |

Fixes/reports live in `/workspace/powernxt-correctness-audit`, branch `audit/correctness-fixes`, based on55a9c54 with **uncommitted working changes**. The new migration is applied only to isolated schemas/audit DB; development remains at84b8976a7d0d. No commits/pushes/merge/deployment occurred. Original `.env`, existing handoff/audit documents and volumes were preserved.

## Practical limits and remaining decisions

Acceptance still stops at pending jobs. No durable analytics scheduler/state/results API, live-event delivery or shared maintenance backend is wired. B's older heuristics/forecast APIs are prototypes; C's original screens are labelled fixtures with browser-local tasks. No calibrated physical prediction/health/confidence result is established.

Agree apparent-capacity versus worst-phase loading semantics and300s worker cadence policy. Confirm C's browser origin/actual local IDs. Independent measured validation is missing. GitHub review/CI queries returnedForbidden; outcomes are unknown. Main's PR6 merge is confirmed by Git, not review API evidence.

The supplied Windows simulator output (`demo-normal-c0415109143f494581036f36d96e32fc`, run `normal-c0415109143f494581036f36d96e32fc`, config1,6 readings/6 pending jobs/6 duplicates) is **user-reported PASS**, not newly executed here. Direct Windows and browser checks were unavailable. A normal dependency Docker rebuild failed at apt; the tested isolated image reused installed dependencies and copied verified fixed source.

Development stayed at5 assets/6 configs/14 readings/14 pending jobs without restart/migration. Only isolated audit/test data and services changed. The audit stack is stopped normally with its volume and demo records retained.

**Highest-priority next action:** review and apply the local validation/configuration-immutability fixes through the normal approval workflow; existing services still have the demonstrated defects. Then integrate B's versioned computation through a real durable worker and verify C's browser connection.
