"""Retained migration/restart evidence for an explicitly isolated test database.

No drops, truncations, downgrades or connections to development databases.
Preparation requires a wholly empty database and seeds labelled historical fixtures.
"""
import argparse
import json
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

HEAD = "d006_combined_integration"
TABLES = (
    "assets", "asset_configurations", "telemetry_readings", "analytics_results",
    "maintenance_tasks", "maintenance_task_history", "incidents", "incident_evidence",
    "incident_events", "incident_operations", "what_if_snapshots",
)


def snapshot(db, tables=TABLES):
    return {table: db.execute(text(f'SELECT to_jsonb(t) FROM "{table}" t ORDER BY to_jsonb(t)')).scalars().all()
            for table in tables}


def verify(database_url, mode, evidence_file):
    url = make_url(database_url)
    if (not url.drivername.startswith("postgresql") or not url.database
            or not url.database.startswith("persond_review_") or not url.database.endswith("_test")
            or url.host not in ("127.0.0.1", "localhost")):
        raise ValueError("Dedicated loopback persond_review_*_test database required")
    engine = create_engine(url)
    cfg = Config("backend/alembic.ini")
    try:
        with engine.begin() as db:
            cfg.attributes["connection"] = db
            if mode in ("prepare", "seed"):
                if db.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")):
                    raise ValueError("Preparation requires an empty public schema; existing records are never replaced")
                command.upgrade(cfg, "d004_worker_maintenance")
                db.execute(text("INSERT INTO assets(asset_id,name,location,timezone) VALUES ('d-review-existing','Historical migration fixture','Isolated synthetic test','UTC')"))
                db.execute(text("""INSERT INTO asset_configurations
                    (asset_id,version,rated_kva,rated_voltage_v,rated_current_a,voltage_convention,
                     measurement_side,cooling_type,operational_limits,thermal_parameters,parameter_provenance)
                    VALUES ('d-review-existing',1,1000,11000,52.49,'line_to_line','primary','ONAN','{}','{}','{}')"""))
                reading = db.scalar(text("""INSERT INTO telemetry_readings
                    (asset_id,configuration_version,schema_version,message_id,source,run_key,measurement_time,
                     original_payload,payload_fingerprint,normalized_telemetry,quality_flags,out_of_order)
                    VALUES ('d-review-existing',1,'1.0.0',:message,'device','',now(),'{}',:fingerprint,'{}','[]',false) RETURNING id"""),
                    {"message": str(uuid4()), "fingerprint": "d" * 64})
                db.execute(text("""INSERT INTO analytics_results
                    (reading_id,model_id,model_version,parameter_version,schema_version,status,payload)
                    VALUES (:reading,'historical-migration-fixture','original-fixture-version','assumed','fixture','unavailable','{}')"""), {"reading": reading})
                db.execute(text("""INSERT INTO maintenance_tasks
                    (id,asset_id,alert_source,alert_id,alert_summary,action,status,owner,notes,version)
                    VALUES (:id,'d-review-existing','sample','sample-existing-review','Synthetic migration fixture','Preserve sample','open','Demo label','Historical notes',2)"""), {"id": str(uuid4())})
                db.execute(text("""INSERT INTO maintenance_task_history
                    (task_id,version,event_type,new_status,new_owner,notes,actor,identity_source)
                    SELECT id,2,'updated','open',owner,notes,'Demo label','demo_header' FROM maintenance_tasks"""))
                old = snapshot(db, TABLES[:6])
                if mode == "seed":
                    assert db.execute(text("SELECT version_num FROM alembic_version")).scalars().all() == ["d004_worker_maintenance"]
                    Path(evidence_file).write_text(json.dumps({"migration_start": "d004_worker_maintenance", "original_records": old}, indent=2) + "\n")
                    print("PASS: isolated historical sample/analytics fixtures seeded at D004")
                    return
                command.upgrade(cfg, "head")
                new = snapshot(db, TABLES[:6])
                for table, rows in old.items():
                    assert len(new[table]) == len(rows)
                    for before, after in zip(rows, new[table]):
                        assert all(after[key] == value for key, value in before.items())
                        assert all(value is None for key, value in after.items() if key not in before)
                data = {"migration_start": "d004_worker_maintenance", "original_records": old,
                        "final_head": HEAD, "checks": ["historical fields unchanged", "additive fields null"]}
            elif mode == "preserve":
                data = json.loads(Path(evidence_file).read_text())
                new = snapshot(db, TABLES[:6])
                for table, rows in data["original_records"].items():
                    assert len(new[table]) == len(rows)
                    for before, after in zip(rows, new[table]):
                        assert all(after[key] == value for key, value in before.items())
                        assert all(value is None for key, value in after.items() if key not in before)
                data["final_head"] = HEAD
                data["checks"] = ["historical fields unchanged", "additive fields null"]
            elif mode == "capture":
                data = {"final_head": HEAD, "records": snapshot(db)}
                assert all(data["records"][table] for table in ("maintenance_tasks", "analytics_results", "what_if_snapshots", "incidents"))
            else:
                data = json.loads(Path(evidence_file).read_text())
                assert snapshot(db) == data["records"], "Restart changed retained record snapshots"
            assert db.execute(text("SELECT version_num FROM alembic_version")).scalars().all() == [HEAD]
            command.check(cfg)
        if mode != "verify":
            Path(evidence_file).write_text(json.dumps(data, indent=2) + "\n")
        print(f"PASS: isolated combined records {mode}; sole {HEAD} and consistent metadata")
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--mode", choices=("prepare", "seed", "preserve", "capture", "verify"), required=True)
    parser.add_argument("--evidence-file", required=True)
    args = parser.parse_args()
    verify(args.database_url, args.mode, args.evidence_file)
