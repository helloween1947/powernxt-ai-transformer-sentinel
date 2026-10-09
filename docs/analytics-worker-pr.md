# Add durable analytics worker with fenced leases and stored results

Telemetry ingestion currently leaves durable jobs pending. Add an opt-in separate PostgreSQL worker that atomically claims jobs, recovers expired leases, bounds retries, and commits deterministic analytical results, model state and job completion together. Expired owners cannot advance state or commit stale results. Independent streams process concurrently; a global stream watermark prevents rewinds across model/configuration changes.

Integrate only Person B's reviewed stored-reading computation and required pure primitives from `637fbe810714d0d5c403728ddf7bcba746ea55a9`, with attribution/source hashes and reproduced example outputs. Use the bound immutable configuration, previous-sample hold and actual measurement dt; gaps over300s explicitly invalidate thermal continuity. Unknown/unsupported metrics remain null with reasons. There are no forecasts, invented health/confidence scores, WebSockets, maintenance or ground-truth detector inputs.

Expose versioned GET reading analytics and explicit-stream latest completed analytics, including newest telemetry references/status to show processing lag. Telemetry identity and ingestion semantics remain compatible; its status enums now reflect the real persisted worker lifecycle.

Migration `d730a91b4c22` extends `ce21c3b8140a`, adding result/state/stream tables, leases/retry fields and a claim index without deleting existing records. Downgrade refuses to erase worker history. Migrate before enabling updated API/worker; worker is under Compose profile `analytics` and consumes retained pending backlog.

## Validation and review limitations

See [actual verification](analytics-worker-verification.md) for final test count and source hashes. Isolated PostgreSQL regressions cover competing workers, independent streams, sequential state, duplicate results, lease expiration/stale owners, atomic rollback, bounded retries, late/equal readings, namespace changes, missing/bad/zero channels, thermal cadence, result filtering and populated migration preservation. Full simulator-to-worker-to-result integration passed with deduplication, normal restart persistence and unfinished lease recovery.

Normal fresh Docker build failed because this execution environment cannot resolve `deb.debian.org` (apt exit100). Isolated integrations used an existing image's installed dependencies plus current source and are explicitly **not a clean-build pass**. Windows commands are prepared, not executed. Hosted PR/CI access must be checked at delivery; a Forbidden response is not passing CI. Keep draft until the normal build, available CI and teammate review are assessed.

[Worker/model/ordering policy](analytics-worker.md), [Person C API contract](contracts/analytics-contract.md), [exact Windows commands](analytics-worker-windows.md). Development services, credentials, unrelated edits and database volumes remain preserved. No merge or deployment.
