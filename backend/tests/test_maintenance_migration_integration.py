"""Real PostgreSQL upgrade paths; never migrate an existing application schema."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

HEAD = "d003_audit_maintenance"


def rows(connection, table):
    return connection.execute(text(f"SELECT to_jsonb(t) FROM {table} t ORDER BY 1::text")).scalars().all()


@pytest.mark.parametrize("start", ["fresh", "84b8976a7d0d", "ce21c3b8140a",
                                  "d001_maintenance", "d002_task_workflow", "both_heads"])
def test_combined_migration_paths_preserve_records(start):
    url = os.environ.get("TEST_DATABASE_URL", "")
    parsed = make_url(url)
    assert parsed.drivername.startswith("postgresql") and parsed.database.endswith("_test")
    schema = "migration_d_test_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert ScriptDirectory.from_config(config).get_heads() == [HEAD]
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            if start != "fresh":
                command.upgrade(config, "ce21c3b8140a" if start == "both_heads" else start)
                if start == "both_heads":
                    command.upgrade(config, "d002_task_workflow")
                    assert set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars()) == {"ce21c3b8140a", "d002_task_workflow"}
                connection.execute(text("""INSERT INTO assets (asset_id,name,location,timezone)
                    VALUES ('migration-asset','Existing asset','Lab','Asia/Kolkata')"""))
                connection.execute(text("""INSERT INTO asset_configurations
                    (asset_id,version,rated_kva,rated_voltage_v,rated_current_a,voltage_convention,
                     measurement_side,cooling_type,operational_limits,thermal_parameters,parameter_provenance)
                    VALUES ('migration-asset',1,1000,11000,52.49,'line_to_line','primary','ONAN','{}','{}','{}')"""))
                connection.execute(text("""INSERT INTO telemetry_readings
                    (asset_id,configuration_version,schema_version,message_id,source,run_key,measurement_time,
                     original_payload,payload_fingerprint,normalized_telemetry,quality_flags,out_of_order)
                    VALUES ('migration-asset',1,'1.0.0',:message,'device','',now(),'{}',:fingerprint,'{}','[]',false)"""),
                    {"message": str(uuid4()), "fingerprint": "a" * 64})
                connection.execute(text("""INSERT INTO telemetry_processing_jobs
                    (reading_id,status,state_policy) SELECT id,'pending','forward_only' FROM telemetry_readings"""))
                tables = ["assets", "asset_configurations", "telemetry_readings", "telemetry_processing_jobs"]
                if start in {"d001_maintenance", "d002_task_workflow", "both_heads"}:
                    connection.execute(text("""INSERT INTO maintenance_tasks
                        (id,asset_id,alert_source,alert_id,alert_summary,action,status)
                        VALUES (:id,'migration-asset','sample','sample-existing','Old sample','Inspect','open')"""),
                        {"id": str(uuid4())})
                    tables.append("maintenance_tasks")
                    if start != "d001_maintenance":
                        connection.execute(text("""UPDATE maintenance_tasks
                            SET owner='Existing demo',notes='Existing notes',version=2"""))
                        connection.execute(text("""INSERT INTO maintenance_task_history
                            (task_id,version,event_type,new_status,new_owner,notes,actor,identity_source)
                            SELECT id,2,'updated','open',owner,notes,'Existing demo','demo_header' FROM maintenance_tasks"""))
                        tables.append("maintenance_task_history")
                before = {table: rows(connection, table) for table in tables}
            else:
                before = {}
            command.upgrade(config, "head")
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all() == [HEAD]
            for table, saved in before.items():
                after = rows(connection, table)
                assert len(after) == len(saved)
                # D001 gains workflow fields; all original values must survive.
                for old, new in zip(saved, after):
                    assert {key: new[key] for key in old} == old
            if start == "d001_maintenance":
                history = rows(connection, "maintenance_task_history")
                assert len(history) == 1 and history[0]["event_type"] == "legacy_import"
                assert history[0]["actor"] is None
            assert connection.scalar(text("SELECT to_regclass('maintenance_task_history')"))
            assert connection.scalar(text("SELECT count(*) FROM pg_trigger WHERE tgname='asset_configuration_immutable' AND tgrelid='asset_configurations'::regclass")) == 1
            if before:
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.execute(text("UPDATE asset_configurations SET rated_kva=2000"))
                assert rows(connection, "asset_configurations") == before["asset_configurations"]
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
