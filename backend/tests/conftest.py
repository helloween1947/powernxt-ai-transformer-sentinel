"""Registry tests migrate fresh schemas in an explicitly selected test database."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.app.db.session import get_db
from backend.app.main import create_app


@pytest.fixture
def registry():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.fail(
            "Set TEST_DATABASE_URL to an isolated PostgreSQL database ending in _test"
        )
    parsed = make_url(url)
    if (
        not parsed.drivername.startswith("postgresql")
        or not parsed.database
        or not parsed.database.endswith("_test")
    ):
        pytest.fail("Registry tests require a PostgreSQL database ending in _test")
    schema = "registry_test_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        factory = sessionmaker(bind=engine)
        app = create_app()

        def test_db():
            with factory() as session:
                yield session

        app.dependency_overrides[get_db] = test_db
        with TestClient(app) as client:
            yield client, factory
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def configuration():
    fields = {
        "rated_kva": 1000,
        "rated_voltage_v": 11000,
        "rated_current_a": 52.49,
        "voltage_convention": "line_to_line",
        "measurement_side": "primary",
        "cooling_type": "ONAN",
    }
    return {**fields, "parameter_provenance": {key: "assumed" for key in fields}}


@pytest.fixture
def asset(registry):
    client, _ = registry
    payload = {
        "asset_id": "test-transformer",
        "name": "Test transformer",
        "location": "Test lab",
        "timezone": "Asia/Kolkata",
    }
    assert client.post("/api/v1/assets", json=payload).status_code == 201
    return payload
