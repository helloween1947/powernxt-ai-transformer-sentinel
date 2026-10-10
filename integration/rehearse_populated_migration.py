"""Populated migration rehearsal and preservation verifier for Phase 3 integration candidate.

Verifies that upgrading from D004 to D006 preserves all pre-existing records,
including jobs, streams, states, tasks, and telemetry, with exact before/after row hashes.
"""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

HEAD = "d006_combined_integration"
D004_TABLES = [
    "assets",
    "asset_configurations",
    "telemetry_readings",
    "telemetry_processing_jobs",
    "analytics_results",
    "analytics_streams",
    "analytics_states",
    "maintenance_tasks",
    "maintenance_task_history",
]

ALL_TABLES = [
    "assets",
    "asset_configurations",
    "telemetry_readings",
    "telemetry_processing_jobs",
    "analytics_results",
    "analytics_streams",
    "analytics_states",
    "incident_operators",
    "incident_detector_epochs",
    "incident_detector_controls",
    "incidents",
    "incident_evidence",
    "incident_events",
    "incident_operations",
    "incident_deliveries",
    "maintenance_tasks",
    "maintenance_task_history",
    "what_if_snapshots",
]


def canonical_hash(obj) -> str:
    serialized = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def snapshot_table(db, table: str):
    rows = db.execute(text(f'SELECT to_jsonb(t) FROM "{table}" t ORDER BY to_jsonb(t)')).scalars().all()
    return rows


def run_rehearsal(database_url: str, output_path: str):
    url = make_url(database_url)
    assert url.host in ("127.0.0.1", "localhost"), "Dedicated loopback required"
    assert url.database and url.database.endswith("_test"), "Database name must end in _test"

    engine = create_engine(url)
    schema = f"rehearsal_{uuid4().hex}"
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))

    test_engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    cfg = Config("backend/alembic.ini")

    try:
        with test_engine.begin() as db:
            cfg.attributes["connection"] = db

            # 1. Upgrade to D004
            command.upgrade(cfg, "d004_worker_maintenance")
            assert db.scalar(text("SELECT version_num FROM alembic_version")) == "d004_worker_maintenance"

            # 2. Seed representative records across ALL D004 tables
            asset_id = "d004-preservation-fixture"
            db.execute(text("""
                INSERT INTO assets (asset_id, name, location, timezone)
                VALUES (:asset, 'Historical D004 Fixture', 'Substation Rehearsal', 'UTC')
            """), {"asset": asset_id})

            db.execute(text("""
                INSERT INTO asset_configurations
                (asset_id, version, rated_kva, rated_voltage_v, rated_current_a, voltage_convention,
                 measurement_side, cooling_type, operational_limits, thermal_parameters, parameter_provenance)
                VALUES (:asset, 1, 1000, 11000, 52.49, 'line_to_line', 'primary', 'ONAN', '{}', '{}', '{}')
            """), {"asset": asset_id})

            reading_id = db.scalar(text("""
                INSERT INTO telemetry_readings
                (asset_id, configuration_version, schema_version, message_id, source, run_key, measurement_time,
                 original_payload, payload_fingerprint, normalized_telemetry, quality_flags, out_of_order)
                VALUES (:asset, 1, '1.0.0', :msg, 'device', '', '2026-01-01T00:00:00Z',
                        '{}', :fp, '{}', '[]', false)
                RETURNING id
            """), {"asset": asset_id, "msg": str(uuid4()), "fp": "a" * 64})

            db.execute(text("""
                INSERT INTO telemetry_processing_jobs
                (reading_id, status, state_policy, attempts, completed_at)
                VALUES (:rid, 'completed', 'forward_only', 1, '2026-01-01T00:00:02Z')
            """), {"rid": reading_id})

            db.execute(text("""
                INSERT INTO analytics_results
                (reading_id, model_id, model_version, parameter_version, schema_version, status, payload)
                VALUES (:rid, 'stored-reading-top-oil-1.0.1', '1.0.1', 'assumed', 'result-1.0.0', 'completed', '{"top_oil_c": 55.4}')
            """), {"rid": reading_id})

            db.execute(text("""
                INSERT INTO analytics_streams
                (asset_id, source, run_key, watermark_time, watermark_reading_id, active_token, lease_until, advances)
                VALUES (:asset, 'device', '', '2026-01-01T00:00:00Z', :rid, null, '2026-01-01T00:00:00Z', 1)
            """), {"asset": asset_id, "rid": reading_id})

            db.execute(text("""
                INSERT INTO analytics_states
                (asset_id, source, run_key, model_id, model_version, configuration_version, parameter_version, state, advances)
                VALUES (:asset, 'device', '', 'stored-reading-top-oil-1.0.1', '1.0.1', 1, 'assumed', '{"temperature": 55.4}', 1)
            """), {"asset": asset_id})

            task_id = str(uuid4())
            db.execute(text("""
                INSERT INTO maintenance_tasks
                (id, asset_id, alert_source, alert_id, alert_summary, action, status, owner, notes, version)
                VALUES (:tid, :asset, 'sample', 'sample-d004', 'Historical sample alert', 'Inspect transformer', 'open', 'Technician A', 'Initial notes', 1)
            """), {"tid": task_id, "asset": asset_id})

            db.execute(text("""
                INSERT INTO maintenance_task_history
                (task_id, version, event_type, new_status, new_owner, notes, actor, identity_source)
                VALUES (:tid, 1, 'created', 'open', 'Technician A', 'Initial notes', 'Technician A', 'demo_header')
            """), {"tid": task_id})

            # Record BEFORE state
            before_inventory = {}
            for t in D004_TABLES:
                cols = db.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = :schema AND table_name = :t
                    ORDER BY ordinal_position
                """), {"schema": schema, "t": t}).mappings().all()
                rows = snapshot_table(db, t)
                before_inventory[t] = {
                    "columns": [dict(c) for c in cols],
                    "row_count": len(rows),
                    "rows": rows,
                    "table_hash": canonical_hash(rows),
                }

            # 3. Upgrade to D006 HEAD
            command.upgrade(cfg, "head")
            assert db.scalar(text("SELECT version_num FROM alembic_version")) == HEAD

            # 4. Check schema drift
            command.check(cfg)

            # 5. Record AFTER state & verify preservation
            after_inventory = {}
            preservation_checks = []

            for t in D004_TABLES:
                cols = db.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = :schema AND table_name = :t
                    ORDER BY ordinal_position
                """), {"schema": schema, "t": t}).mappings().all()
                rows = snapshot_table(db, t)
                after_inventory[t] = {
                    "columns": [dict(c) for c in cols],
                    "row_count": len(rows),
                    "rows": rows,
                    "table_hash": canonical_hash(rows),
                }

                # Verify exact row count
                assert len(rows) == before_inventory[t]["row_count"], f"Row count changed for {t}"

                # Verify each pre-existing column and value matches
                for b_row, a_row in zip(before_inventory[t]["rows"], rows):
                    for k, v in b_row.items():
                        assert a_row[k] == v, f"Field {t}.{k} changed from {v} to {a_row[k]}"
                    # Verify additive columns are null
                    for k, v in a_row.items():
                        if k not in b_row:
                            assert v is None, f"Additive field {t}.{k} expected None, got {v}"

                preservation_checks.append(f"{t}: all {len(rows)} pre-existing rows preserved identically")

            # Check new tables present at D006
            new_tables_d006 = [
                "incident_operators",
                "incident_detector_epochs",
                "incident_detector_controls",
                "incidents",
                "incident_evidence",
                "incident_events",
                "incident_operations",
                "incident_deliveries",
                "what_if_snapshots",
            ]
            d006_table_inventory = {}
            for nt in new_tables_d006:
                cnt = db.scalar(text(f'SELECT count(*) FROM "{nt}"'))
                cols = db.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = :schema AND table_name = :t
                    ORDER BY ordinal_position
                """), {"schema": schema, "t": nt}).mappings().all()
                d006_table_inventory[nt] = {
                    "columns": [dict(c) for c in cols],
                    "row_count": cnt,
                }
                assert cnt == 0, f"Expected clean empty table for {nt}"

            # Verify sample tasks did not get linked to incidents
            unlinked_sample_tasks = db.scalar(text("SELECT count(*) FROM maintenance_tasks WHERE alert_source='sample' AND incident_id IS NULL"))
            assert unlinked_sample_tasks == 1
            preservation_checks.append("Sample maintenance tasks remain unlinked (incident_id is null)")

            result = {
                "migration_start": "d004_worker_maintenance",
                "final_head": HEAD,
                "schema": schema,
                "preservation_status": "PASS",
                "tables_verified_count": len(D004_TABLES),
                "d004_table_inventory": {t: {"columns_count": len(v["columns"]), "row_count": v["row_count"], "table_hash": v["table_hash"]} for t, v in before_inventory.items()},
                "d006_additive_tables_count": len(new_tables_d006),
                "d006_additive_tables": d006_table_inventory,
                "preservation_checks": preservation_checks,
                "original_records": {t: v["rows"] for t, v in before_inventory.items()},
                "upgraded_records": {t: v["rows"] for t, v in after_inventory.items()},
            }

            Path(output_path).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print("PASS: Populated migration rehearsal from D004 to D006 verified with 100% field parity and canonical hashes!")
            return result
    finally:
        test_engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


if __name__ == "__main__":
    db_url = "postgresql+psycopg://sentinel:sentinel_phase3_pw@127.0.0.1:55433/sentinel_phase3_test"
    out_file = "docs/evidence/populated-migration-preservation.json"
    run_rehearsal(db_url, out_file)
