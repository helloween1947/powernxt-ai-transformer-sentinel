# Integrate current main and fix maintenance validation/migration join

Supplemental A-owned fix for D's PR9; **target persond**, leaving D's branch untouched until its owner reviews/incorporates this change. The first commit locally integrates already-merged current main (analytics-worker PR11) and resolves API/model registration conflicts, retaining both worker and maintenance. It does not duplicate/reimplement D's maintenance workflow.

D003 correctly joins audit and maintenance, but current main's worker revision leaves two heads. Add no-op `d004_worker_maintenance` joining d730+D003 without rewriting applied migrations. Extend migration checks for worker/D003 states, populated results/state and task history, deterministic snapshots and cleanup on graph failure.

Maintenance POST/PATCH previously returned500 for nonfinite JSON. Reuse A's existing finite-JSON dependency, returning422; eight regressions cover NaN, infinities and overflowing exponents. Keep sample-alert and demo-identity semantics unchanged.

Validation:222 backend tests passed using isolated PostgreSQL16, including genuine fresh database upgrade, eight schema starting states, preservation, one intended head and metadata checks. Offline upgrade SQL passed. No Docker/Windows/browser/development deployment was performed. Hosted PR/CI APIs are Forbidden, so no hosted pass or approval is inferred.

See [full review and D handover](persond-a-review.md). D should update PR9 to the reviewed current-main integration and rerun CI at the exact new commit. Genuine incident registry/identity/provenance/transport and trusted operator/session authentication are still unimplemented team decisions. No merge or auto-merge.
