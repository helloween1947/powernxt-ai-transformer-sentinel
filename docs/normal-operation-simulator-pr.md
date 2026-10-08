# Add reproducible normal-operation transformer simulator

A registered transformer configuration can now produce deterministic synthetic readings and submit them to the real ingestion API. The generator uses explicit configuration/run/seed/time references, bounded three-phase RMS variation and a documented first-order thermal assumption. Artifacts retain an immutable configuration snapshot and separate assumptions from detector inputs; disabled oil level stays null.

The sender validates JSONL before admission, preserves packet bytes/identifiers across bounded transient retries, reports created/duplicate/failure counts and stops on conflicting or invalid requests. Immediate or measurement-gap pacing never changes measurement timestamps. No database/API migration, analytics worker, fault scenario or WebSocket is added.

Validation: 115 backend tests passed against isolated PostgreSQL schemas. Actual cloud Docker integration created six readings/six pending jobs, resent six identical duplicates without extra rows/jobs, matched paginated history/latest and confirmed an empty device stream. Ruff checks pass; curated samples reproduce from recorded metadata. Windows commands are supplied but have not been executed here. See `docs/normal-operation-simulator-verification.md`.

Person B review requested for the declared synthetic envelope, thermal constants and magnitude/noise assumptions. Matching this generator does not validate predictive accuracy. Do not merge until reviewed.
