# Fix validation and enforce immutable configuration history

Registry requests could accept boolean/string ratings, overflow during UTC normalization, or fail with HTTP 500 on nonfinite JSON. Configuration versions were immutable through the API but could still be rewritten or deleted through SQL, invalidating telemetry references.

Reject invalid finite-number inputs and timestamp overflow with HTTP 422 while preserving valid request/response behaviour and original ingestion payloads. Add schema-qualified PostgreSQL UPDATE/DELETE guards; legitimate new configuration versions and identical ingestion retries remain supported. Correct host database/CORS examples, apply exclusions at the actual Docker build-context root, and clarify the simulator's ±2% phase offsets / 4% spread.

## Migration and compatibility

`ce21c3b8140a` extends `84b8976a7d0d`. Upgrade adds a trigger/function without rewriting data. Downgrade removes those guards and preserves rows, but allows later mutation of configuration history. Online DDL binds to the current schema; offline SQL uses the configured version-table schema or public.

After review and merge: build normally, stop backend writers, apply migration, start backend and verify readiness/Alembic consistency. Existing development services/database have not been updated. B's analytics must append configuration versions; C's editors must submit finite JSON numbers. Successful read-response schemas are unchanged; analytics and processing lifecycle are outside this change.

## Validation executed on Linux

- 128 backend tests passed using isolated PostgreSQL schemas, including populated migration round-trip, both SQL guards, new versions and retries.
- Separate populated isolated Docker database: full snapshots of 3 assets, 4 configurations, 7 readings and 7 jobs unchanged across downgrade/upgrade; both guards rejected SQL mutations.
- Registry, telemetry and simulator integration scripts passed against the isolated updated-source image; registry/telemetry normal restart persistence and duplicate job checks passed. Simulator created six readings/jobs and accepted six identical retries; analytics remains pending.
- Alembic current/check and offline upgrade/downgrade SQL passed; targeted Ruff/formatting and diff checks passed.
- Runtime/migration bytes matched the tested container. Original local work, development services and volumes preserved.

## Outstanding checks — keep draft

The normal fresh Dockerfile build remains blocked by execution-environment networking/trust: initially apt could not resolve `deb.debian.org`; proxy host mapping let apt finish, then official PyPI rejected a self-signed proxy certificate chain. TLS verification remained enabled. Integration used an explicitly identified existing image's installed dependencies plus current sources; this is **not** a clean-build pass.

GitHub PR/workflow APIs returned Forbidden; hosted CI and review status are unknown. Windows commands are prepared but were not executed here. Run the normal build in a working, trusted environment and assess hosted CI before approval.

[Current/historical evidence](project-correctness-audit.md), [structured evidence](project-correctness-evidence.json), [PowerShell handoff](correctness-fixes-windows.md).
