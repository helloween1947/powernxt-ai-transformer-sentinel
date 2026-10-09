from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from backend.app.models import AssetConfiguration
from backend.app.schemas.assets import ConfigurationCreate

ROOT = "/api/v1/assets"


def test_create_retrieve_and_duplicate(registry, asset):
    client, _ = registry
    response = client.get(f"{ROOT}/{asset['asset_id']}")
    assert response.status_code == 200
    data = response.json()
    assert all(data[key] == value for key, value in asset.items())
    assert data["current_configuration"] is None
    assert datetime.fromisoformat(data["created_at"]).utcoffset() == timedelta(0)
    duplicate = client.post(ROOT, json=asset)
    assert duplicate.status_code == 409
    assert "sentinel_dev_pw" not in duplicate.text
    # A failed insert must not poison later requests.
    assert client.get(f"{ROOT}/{asset['asset_id']}").status_code == 200


def test_unknown_assets(registry, configuration):
    client, _ = registry
    assert client.get(f"{ROOT}/missing").status_code == 404
    assert client.get(f"{ROOT}/missing/configurations").status_code == 404
    assert (
        client.post(f"{ROOT}/missing/configurations", json=configuration).status_code
        == 404
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("timezone", "Mars/Base"),
        ("timezone", "../UTC"),
        ("name", "  "),
        ("asset_id", "bad/id"),
    ],
)
def test_invalid_asset(registry, field, value):
    client, _ = registry
    payload = {
        "asset_id": "test",
        "name": "Test",
        "location": "Lab",
        "timezone": "UTC",
        field: value,
    }
    assert client.post(ROOT, json=payload).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("rated_kva", 0),
        ("rated_voltage_v", -1),
        ("rated_current_a", 0),
        ("rated_kva", "NaN"),
        ("rated_current_a", "Infinity"),
        ("voltage_convention", "unspecified"),
        ("measurement_side", "unknown"),
        ("cooling_type", " "),
        ("parameter_provenance", {}),
    ],
)
def test_invalid_configuration(registry, asset, configuration, field, value):
    client, _ = registry
    configuration[field] = value
    assert (
        client.post(
            f"{ROOT}/{asset['asset_id']}/configurations", json=configuration
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "group,values",
    [
        ("operational_limits", {"min_voltage_pu": 1.1, "max_voltage_pu": 0.9}),
        ("operational_limits", {"max_top_oil_temp_c": 120, "max_hot_spot_temp_c": 100}),
        ("operational_limits", {"max_load_pct": -1}),
        ("operational_limits", {"max_top_oil_temp_c": -300}),
        ("thermal_parameters", {"oil_time_constant_min": 0}),
        ("thermal_parameters", {"loss_ratio": "Infinity"}),
    ],
)
def test_invalid_parameters(registry, asset, configuration, group, values):
    client, _ = registry
    configuration[group] = values
    configuration["parameter_provenance"].update(
        {f"{group}.{key}": "assumed" for key in values}
    )
    assert (
        client.post(
            f"{ROOT}/{asset['asset_id']}/configurations", json=configuration
        ).status_code
        == 422
    )


def test_nonfinite_float_validation(configuration):
    for value in (float("nan"), float("inf"), -float("inf")):
        with pytest.raises(ValidationError):
            ConfigurationCreate.model_validate({**configuration, "rated_kva": value})


def test_listing_pagination(registry):
    client, _ = registry
    for asset_id in ("c", "a", "b"):
        assert (
            client.post(
                ROOT,
                json={
                    "asset_id": asset_id,
                    "name": asset_id,
                    "location": "Lab",
                    "timezone": "UTC",
                },
            ).status_code
            == 201
        )
    first = client.get(ROOT, params={"limit": 2}).json()
    assert [item["asset_id"] for item in first["items"]] == ["a", "b"]
    assert first["limit"] == 2 and first["offset"] == 0
    assert [
        item["asset_id"]
        for item in client.get(ROOT, params={"limit": 2, "offset": 2}).json()["items"]
    ] == ["c"]
    assert client.get(ROOT, params={"offset": 3}).json()["items"] == []
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        assert client.get(ROOT, params=params).status_code == 422


def test_version_history_immutable(registry, asset, configuration):
    client, _ = registry
    path = f"{ROOT}/{asset['asset_id']}"
    configuration["thermal_parameters"] = {"oil_time_constant_min": 180}
    configuration["parameter_provenance"][
        "thermal_parameters.oil_time_constant_min"
    ] = "assumed"
    first = client.post(f"{path}/configurations", json=configuration)
    assert first.status_code == 201
    assert first.json()["version"] == 1
    assert first.json()["thermal_parameters"]["winding_time_constant_min"] is None
    configuration["rated_kva"] = 1200
    second = client.post(f"{path}/configurations", json=configuration)
    assert second.status_code == 201 and second.json()["version"] == 2
    assert client.get(path).json()["current_configuration"] == second.json()
    assert client.get(ROOT).json()["items"][0]["current_configuration"] == second.json()
    history = client.get(f"{path}/configurations").json()["items"]
    assert history == [first.json(), second.json()]
    assert client.get(
        f"{path}/configurations", params={"limit": 1, "offset": 1}
    ).json()["items"] == [second.json()]
    assert client.patch(f"{path}/configurations", json=configuration).status_code == 405
    assert client.delete(f"{path}/configurations").status_code == 405
    for params in ({"limit": 101}, {"offset": -1}):
        assert client.get(f"{path}/configurations", params=params).status_code == 422


def test_concurrent_configuration_versions(registry, asset, configuration):
    client, factory = registry
    from threading import Barrier

    barrier = Barrier(8)
    path = f"{ROOT}/{asset['asset_id']}/configurations"

    def create(index):
        barrier.wait(timeout=10)
        return client.post(path, json={**configuration, "rated_kva": 1000 + index})

    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(create, range(8)))
    assert [response.status_code for response in responses] == [201] * 8
    assert sorted(response.json()["version"] for response in responses) == list(
        range(1, 9)
    )
    history = client.get(path).json()["items"]
    assert [row["version"] for row in history] == list(range(1, 9))
    assert sorted(row["rated_kva"] for row in history) == list(range(1000, 1008))
    # The database independently enforces uniqueness, even outside the API.
    with factory() as db:
        duplicate = AssetConfiguration(
            asset_id=asset["asset_id"], version=1, **configuration
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert len(db.scalars(select(AssetConfiguration)).all()) == 8


def test_database_failure_is_sanitized(registry, monkeypatch):
    client, _ = registry

    def fail(*args):
        raise OperationalError("query", {}, Exception("private-password"))

    monkeypatch.setattr("backend.app.services.assets.list_assets", fail)
    response = client.get(ROOT)
    assert response.status_code == 503
    assert "private-password" not in response.text


def test_migration_roundtrip(registry):
    _, factory = registry
    from alembic import command
    from alembic.config import Config

    with factory.kw["bind"].begin() as connection:
        config = Config("backend/alembic.ini")
        config.attributes["connection"] = connection
        connection.execute(text("CREATE TABLE unrelated_record (value integer)"))
        connection.execute(text("INSERT INTO unrelated_record VALUES (42)"))
        command.downgrade(config, "base")
        assert connection.scalar(text("SELECT to_regclass('assets')")) is None
        command.upgrade(config, "head")
        assert connection.scalar(text("SELECT to_regclass('assets')")) is not None
        assert connection.scalar(text("SELECT value FROM unrelated_record")) == 42


@pytest.mark.parametrize(
    "field,value",
    [
        ("rated_kva", -1),
        ("rated_voltage_v", float("inf")),
        ("rated_current_a", float("nan")),
        ("version", 0),
    ],
)
def test_database_rating_and_version_constraints(
    registry, asset, configuration, field, value
):
    _, factory = registry
    fields = {**configuration, "version": 1, field: value}
    with factory() as db:
        db.add(AssetConfiguration(asset_id=asset["asset_id"], **fields))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert db.scalar(select(AssetConfiguration)) is None
