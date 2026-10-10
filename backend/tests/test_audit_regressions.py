"""Confirmed audit defects: HTTP-safe timestamps/numbers and declared setup."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.schemas.assets import ConfigurationCreate


@pytest.mark.parametrize("value", [True, False, "1000"])
def test_ratings_require_real_numbers(configuration, value):
    with pytest.raises(ValidationError):
        ConfigurationCreate.model_validate({**configuration, "rated_kva": value})


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_registry_nonfinite_returns_422(registry, asset, configuration, token):
    client, _ = registry
    body = json.dumps(configuration).replace(
        '"rated_kva": 1000', f'"rated_kva": {token}'
    )
    response = client.post(
        f"/api/v1/assets/{asset['asset_id']}/configurations",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert (
        client.get(f"/api/v1/assets/{asset['asset_id']}/configurations").json()["items"]
        == []
    )


@pytest.mark.parametrize(
    "timestamp", ["9999-12-31T23:59:59-23:59", "0001-01-01T00:00:00+23:59"]
)
def test_timestamp_overflow_is_validation_error(registry, timestamp):
    client, _ = registry
    packet = json.loads(Path("data/sample/telemetry-sample.json").read_text())
    packet["timestamp"] = timestamp
    assert client.post("/api/v1/telemetry", json=packet).status_code == 422
    assert (
        client.get(
            "/api/v1/assets/example/telemetry", params={"start": timestamp}
        ).status_code
        == 422
    )


def test_environment_example_loads(monkeypatch):
    # Test the declared example rather than ambient runtime/test database overrides.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    settings = Settings(_env_file=".env.example")
    assert ":5433/" in settings.DATABASE_URL
    assert "http://localhost:5173" in settings.CORS_ORIGINS


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE asset_configurations SET rated_kva = 999 WHERE asset_id = :asset",
        "DELETE FROM asset_configurations WHERE asset_id = :asset",
    ],
)
def test_database_configuration_history_is_append_only(
    registry, asset, configuration, statement
):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    client, factory = registry
    path = f"/api/v1/assets/{asset['asset_id']}/configurations"
    first = client.post(path, json=configuration).json()
    with factory() as db:
        with pytest.raises(IntegrityError, match="immutable"):
            db.execute(text(statement), {"asset": asset["asset_id"]})
            db.commit()
        db.rollback()
    assert client.get(path).json()["items"] == [first]
    second = client.post(path, json={**configuration, "rated_kva": 1100})
    assert second.status_code == 201 and second.json()["version"] == 2
    assert client.get(path).json()["items"][0] == first


def test_populated_migration_upgrade_downgrade_preserves_rows(
    registry, asset, configuration
):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    client, factory = registry
    path = f"/api/v1/assets/{asset['asset_id']}/configurations"
    first = client.post(path, json=configuration)
    assert first.status_code == 201
    packet = json.loads(Path("data/sample/telemetry-sample.json").read_text())
    packet.update(asset_id=asset["asset_id"], configuration_version=1)
    accepted = client.post("/api/v1/telemetry", json=packet)
    assert accepted.status_code == 201
    tables = [
        "assets",
        "asset_configurations",
        "telemetry_readings",
        "telemetry_processing_jobs",
    ]
    original_columns = {
        "assets": "asset_id,name,location,timezone,created_at",
        "asset_configurations": "id,asset_id,version,created_at,rated_kva,rated_voltage_v,rated_current_a,voltage_convention,measurement_side,cooling_type,operational_limits,thermal_parameters,parameter_provenance",
        "telemetry_readings": "id,asset_id,configuration_version,schema_version,message_id,source,run_key,measurement_time,arrival_time,original_payload,payload_fingerprint,normalized_telemetry,quality_flags,out_of_order",
        "telemetry_processing_jobs": "id,reading_id,created_at,status,state_policy",
    }
    with factory.kw["bind"].begin() as connection:
        config = Config("backend/alembic.ini")
        config.attributes["connection"] = connection
        command.downgrade(config, "84b8976a7d0d")
        before = {
            table: connection.execute(
                text("SELECT " + original_columns[table] + " FROM " + table)
            ).all()
            for table in tables
        }
        schema = connection.scalar(text("SELECT current_schema()"))
        command.upgrade(config, "head")
        after = {
            table: connection.execute(
                text("SELECT " + original_columns[table] + " FROM " + table)
            ).all()
            for table in tables
        }
        assert before == after
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE p.proname='reject_asset_configuration_mutation' AND n.nspname=:schema"
                ),
                {"schema": schema},
            )
            == 1
        )
    for statement in [
        "UPDATE asset_configurations SET rated_kva=999",
        "DELETE FROM asset_configurations",
    ]:
        with factory() as db:
            with pytest.raises(IntegrityError, match="immutable"):
                db.execute(text(statement))
            db.rollback()
    assert (
        client.post(path, json={**configuration, "rated_kva": 1100}).status_code == 201
    )
    retry = client.post("/api/v1/telemetry", json=packet)
    assert retry.status_code == 200 and retry.json() == accepted.json()
    with factory.kw["bind"].begin() as connection:
        config = Config("backend/alembic.ini")
        config.attributes["connection"] = connection
        before = {
            table: connection.execute(
                text("SELECT " + original_columns[table] + " FROM " + table)
            ).all()
            for table in tables
        }
        command.downgrade(config, "84b8976a7d0d")
        assert {
            table: connection.execute(
                text("SELECT " + original_columns[table] + " FROM " + table)
            ).all()
            for table in tables
        } == before
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE p.proname='reject_asset_configuration_mutation' AND n.nspname=:schema"
                ),
                {"schema": schema},
            )
            == 0
        )
        # A no-op UPDATE succeeds after downgrade: the protection is intentionally gone.
        connection.execute(text("UPDATE asset_configurations SET rated_kva=rated_kva"))
        command.upgrade(config, "head")
    assert client.post("/api/v1/telemetry", json=packet).json() == accepted.json()
