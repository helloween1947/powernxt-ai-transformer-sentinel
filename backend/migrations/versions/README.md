# Alembic Migration Versions

This directory contains versioned database schema migration scripts for Alembic.

## Workflow for Person A
When data models (e.g. `TransformerAsset`, `TelemetryRecord`, `EventRecord`) are implemented in `backend/app/db/`:

1. Ensure models inherit from `backend.app.db.base.Base` and are imported into `backend/app/db/__init__.py`.
2. Generate an autodetected migration revision:
   ```powershell
   # Run from repository root:
   .\.venv\Scripts\alembic -c backend/alembic.ini revision --autogenerate -m "create_asset_and_telemetry_tables"
   ```
3. Inspect the newly created Python file in this folder to ensure changes are accurate.
4. Apply the migration to the running PostgreSQL database:
   ```powershell
   .\.venv\Scripts\alembic -c backend/alembic.ini upgrade head
   ```
5. To downgrade one revision:
   ```powershell
   .\.venv\Scripts\alembic -c backend/alembic.ini downgrade -1
   ```
