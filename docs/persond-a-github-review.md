Request changes for PR9 tip 087a884e31c7942330f3cf599aa190b916bfff1e against current main 9d2f9cda817bc6312d00a4fc001050b04b85a2cb.

1. Current main includes analytics-worker PR11. Integrating PR9 now conflicts in API/model registration and produces two Alembic heads (d003_audit_maintenance and d730a91b4c22). Retain both APIs/models and add an additive no-op join; do not rewrite D003's applied parents.
2. Maintenance POST/PATCH lack the shared finite-JSON guard. Requests with NaN reproduced HTTP500. Reuse the existing dependency to return422 for invalid finite-number JSON.

A prepared the supplemental fix on fix/persond-main-integration for incorporation into persond, with a D004 join and regression tests. The isolated current-main combination passes222 backend tests, including fresh database upgrade, eight upgrade states, populated record/result/state/history preservation, schema consistency, concurrency, CORS and route checks. Full review/handover: docs/persond-a-review.md on that branch.

The earlier173-test/CI report is historical; current hosted run/review metadata could not be verified because GitHub APIs returned Forbidden. Re-run CI on the refreshed PR9 exact commit and obtain human approval. This is still a labelled sample/demo maintenance milestone: no canonical persisted genuine incident identity/transport or trusted operator authentication is implemented. X-Demo-Actor is not authenticated identity; task completion does not acknowledge/recover an incident. No browser/frontend approval is implied.
