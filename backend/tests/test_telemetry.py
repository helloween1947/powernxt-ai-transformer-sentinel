"""PostgreSQL-backed API and transaction tests, using isolated migrated schemas."""

import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from backend.app.models.telemetry import ProcessingJob, TelemetryReading

ROOT = "/api/v1/telemetry"


@pytest.fixture
def packet(registry, asset, configuration):
    client, _ = registry
    result = client.post(
        f"/api/v1/assets/{asset['asset_id']}/configurations", json=configuration
    )
    assert result.status_code == 201
    return {
        "schema_version": "1.0.0",
        "message_id": str(uuid4()),
        "asset_id": asset["asset_id"],
        "timestamp": "2026-10-08T12:00:00+05:30",
        "source": "device",
        "configuration_version": 1,
        "measurements": {"voltage_r_v": 11000, "oil_temperature_c": 50},
    }


def path(packet):
    return f"/api/v1/assets/{packet['asset_id']}/telemetry"


def counts(factory):
    with factory() as db:
        return (
            db.scalar(select(func.count()).select_from(TelemetryReading)),
            db.scalar(select(func.count()).select_from(ProcessingJob)),
        )


def post(client, packet):
    response = client.post(ROOT, json=packet)
    assert response.status_code == 201, response.text
    return response.json()


def test_valid_ingestion_and_retrieval(registry, packet):
    client, factory = registry
    result = post(client, packet)
    assert result["original_payload"] == packet
    assert result["measurement_time"] == "2026-10-08T06:30:00Z"
    assert datetime.fromisoformat(result["arrival_time"]).utcoffset() == timedelta(0)
    assert result["arrival_time"] != result["measurement_time"]
    assert result["analytics_status"] == result["processing_job"]["status"] == "pending"
    assert result["processing_job"]["state_policy"] == "forward_only"
    assert result["out_of_order"] is False
    assert client.get(path(packet) + "/latest").json() == result
    assert client.get(path(packet)).json()["items"] == [result]
    assert counts(factory) == (1, 1)


def test_missing_channels_are_null(registry, packet):
    client, _ = registry
    packet["measurements"] = {"current_r_a": 0, "oil_level_pct": None}
    result = post(client, packet)
    values = result["normalized_telemetry"]["measurements"]
    assert values["current_r_a"] == 0
    assert all(value is None for key, value in values.items() if key != "current_r_a")
    assert (
        result["normalized_telemetry"]["measurement_quality"]["voltage_r_v"]
        == "missing"
    )
    assert result["quality_flags"]["voltage_r_v"] == ["missing"]
    assert result["original_payload"]["measurements"] == packet["measurements"]


def test_unknown_and_empty_assets(registry, packet):
    client, _ = registry
    assert client.get(path(packet) + "/latest").status_code == 404
    assert client.get(path(packet)).json()["items"] == []
    packet["asset_id"] = "unknown"
    assert client.post(ROOT, json=packet).status_code == 404
    assert client.get(path(packet)).status_code == 404
    assert client.get(path(packet) + "/latest").status_code == 404


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "2.0.0"),
        ("message_id", "not-a-uuid"),
        ("message_id", "00000000-0000-1000-8000-000000000000"),
        ("asset_id", "bad/id"),
        ("asset_id", " test-transformer "),
        ("source", "unknown"),
        ("run_id", "live-run"),
        ("configuration_version", 0),
        ("configuration_version", True),
        ("timestamp", "2026-10-08T12:00:00"),
        ("timestamp", "bad-time"),
        ("timestamp", 1760000000),
        ("timestamp", "1760000000"),
        ("timestamp", "2026-13-08T12:00:00Z"),
        ("timestamp", "2026-10-08T12:00:00.1234567Z"),
        ("measurements", {"current_r_a": "10"}),
        ("measurements", {"current_r_a": True}),
        ("measurements", {"surprise": 2}),
        ("fault_label", "cooling_failure"),
        ("measurement_quality", {"current_r_a": "good"}),
        ("measurement_quality", {"voltage_r_v": "missing"}),
        ("measurement_quality", {"voltage_r_v": "unknown"}),
        ("measurement_quality", {"unknown": "bad"}),
        ("measurement_quality", {"voltage_r_v": True}),
    ],
)
def test_malformed_input(registry, packet, field, value):
    client, factory = registry
    packet[field] = value
    response = client.post(ROOT, json=packet)
    assert response.status_code == 422, response.text
    assert counts(factory) == (0, 0)


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_nonfinite_json_rejected(registry, packet, token):
    import json

    client, factory = registry
    packet["measurements"] = {"voltage_r_v": "REPLACE"}
    body = json.dumps(packet).replace('"REPLACE"', token)
    assert (
        client.post(
            ROOT, content=body, headers={"Content-Type": "application/json"}
        ).status_code
        == 422
    )
    assert counts(factory) == (0, 0)


def test_implausible_values_preserved_and_flagged(registry, packet):
    client, _ = registry
    packet["measurements"] = {
        "voltage_r_v": -1,
        "voltage_y_v": 999999,
        "current_b_a": 99999,
        "oil_temperature_c": -300,
        "ambient_temperature_c": 300,
        "oil_level_pct": 110,
    }
    packet["measurement_quality"] = {"voltage_r_v": "suspect", "current_b_a": "bad"}
    result = post(client, packet)
    assert result["original_payload"] == packet
    assert result["normalized_telemetry"]["measurements"]["oil_level_pct"] == 110
    assert result["quality_flags"]["voltage_r_v"] == ["suspect", "negative_magnitude"]
    assert result["quality_flags"]["voltage_y_v"] == ["above_10x_rating"]
    assert result["quality_flags"]["current_b_a"] == ["bad", "above_10x_rating"]
    assert result["quality_flags"]["oil_temperature_c"] == ["outside_sanity_range"]


def test_duplicates_and_conflicts(registry, packet, configuration):
    client, factory = registry
    first = post(client, packet)
    # Even after adding another configuration, a retry returns the original binding.
    client.post(
        f"/api/v1/assets/{packet['asset_id']}/configurations", json=configuration
    )
    retry = client.post(ROOT, json=dict(reversed(list(packet.items()))))
    assert retry.status_code == 200 and retry.json() == first
    packet["measurements"]["voltage_r_v"] = 11001
    conflict = client.post(ROOT, json=packet)
    assert conflict.status_code == 409
    assert "sentinel_dev_pw" not in conflict.text
    assert counts(factory) == (1, 1)
    assert client.get(path(packet) + "/latest").json() == first


def test_concurrent_identical_submissions(registry, packet):
    client, factory = registry
    barrier = Barrier(8)

    def submit(_):
        barrier.wait(timeout=10)
        return client.post(ROOT, json=packet)

    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(submit, range(8)))
    assert sorted(response.status_code for response in responses) == [200] * 7 + [201]
    assert all(response.json() == responses[0].json() for response in responses)
    assert counts(factory) == (1, 1)


def test_concurrent_conflicting_submissions(registry, packet):
    client, factory = registry
    barrier = Barrier(2)

    def submit(value):
        body = copy.deepcopy(packet)
        body["measurements"]["voltage_r_v"] = value
        barrier.wait(timeout=10)
        return client.post(ROOT, json=body)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(submit, [11000, 11001]))
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert counts(factory) == (1, 1)


def test_out_of_order_and_ties(registry, packet):
    client, _ = registry
    first = post(client, packet)
    packet["message_id"] = str(uuid4())
    packet["timestamp"] = "2026-10-08T05:30:00Z"
    older = post(client, packet)
    assert older["out_of_order"] is True
    assert older["processing_job"]["state_policy"] == "historical_only"
    assert client.get(path(packet) + "/latest").json() == first
    packet["message_id"] = str(uuid4())
    packet["timestamp"] = "2026-10-08T06:30:00Z"
    tied = post(client, packet)
    assert tied["out_of_order"] is False
    assert tied["processing_job"]["state_policy"] == "historical_only"
    assert client.get(path(packet) + "/latest").json() == tied
    packet["message_id"] = str(uuid4())
    packet["timestamp"] = "2026-10-08T06:31:00Z"
    newest = post(client, packet)
    assert newest["processing_job"]["state_policy"] == "forward_only"
    assert client.get(path(packet) + "/latest").json() == newest
    assert [row["id"] for row in client.get(path(packet)).json()["items"]] == [
        older["id"],
        first["id"],
        tied["id"],
        newest["id"],
    ]


def test_run_and_source_isolation(registry, packet):
    client, factory = registry
    live = post(client, packet)
    results = []
    for source, run_id in [
        ("simulator", "run-a"),
        ("simulator", "run-b"),
        ("file_replay", "run-a"),
    ]:
        body = {
            **packet,
            "source": source,
            "run_id": run_id,
            "timestamp": "2026-10-09T12:00:00Z",
        }
        results.append(post(client, body))
        params = {"source": source, "run_id": run_id}
        assert client.get(path(packet) + "/latest", params=params).json() == results[-1]
        assert client.get(path(packet), params=params).json()["items"] == [results[-1]]
        assert results[-1]["processing_job"]["state_policy"] == "forward_only"
    assert client.get(path(packet) + "/latest").json() == live
    assert client.get(path(packet)).json()["items"] == [live]
    assert counts(factory) == (4, 4)
    for params in [
        {"source": "simulator"},
        {"source": "device", "run_id": "run-a"},
        {"source": "file_replay", "run_id": "bad/id"},
        {"source": "unknown"},
    ]:
        assert client.get(path(packet), params=params).status_code == 422
    assert (
        client.get(
            path(packet) + "/latest", params={"source": "simulator", "run_id": "empty"}
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "source,run_id",
    [
        ("simulator", None),
        ("file_replay", ""),
        ("simulator", "bad/id"),
        ("simulator", " padded-run "),
    ],
)
def test_invalid_run(registry, packet, source, run_id):
    client, _ = registry
    packet.update(source=source, run_id=run_id)
    assert client.post(ROOT, json=packet).status_code == 422


def test_configuration_references(registry, packet, configuration):
    client, factory = registry
    packet["configuration_version"] = 2
    assert client.post(ROOT, json=packet).status_code == 422
    assert counts(factory) == (0, 0)
    client.post(
        "/api/v1/assets",
        json={
            "asset_id": "other",
            "name": "Other",
            "location": "Lab",
            "timezone": "UTC",
        },
    )
    client.post("/api/v1/assets/other/configurations", json=configuration)
    client.post("/api/v1/assets/other/configurations", json=configuration)
    assert (
        client.post(ROOT, json=packet).status_code == 422
    )  # v2 on other asset is insufficient
    client.post(
        f"/api/v1/assets/{packet['asset_id']}/configurations", json=configuration
    )
    packet["configuration_version"] = 1
    first = post(client, packet)  # Historical version can be chosen explicitly.
    assert first["configuration_version"] == 1
    packet["configuration_version"] = 2
    packet["message_id"] = str(uuid4())
    assert post(client, packet)["configuration_version"] == 2


def test_atomic_job_failure_rolls_back_reading(registry, packet, monkeypatch):
    client, factory = registry
    from sqlalchemy.orm import Session

    original_flush = Session.flush

    def fail_job(session, *args, **kwargs):
        if any(isinstance(row, ProcessingJob) for row in session.new):
            raise IntegrityError("job insert", {}, Exception("private-credential"))
        return original_flush(session, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Session, "flush", fail_job)
        failed = client.post(ROOT, json=packet)
        assert failed.status_code == 409
        assert "private-credential" not in failed.text
    assert counts(factory) == (0, 0)
    post(client, packet)
    assert counts(factory) == (1, 1)


def test_database_constraints(registry, packet):
    client, factory = registry
    result = post(client, packet)
    with factory() as db:
        job = ProcessingJob(
            reading_id=result["id"], status="pending", state_policy="forward_only"
        )
        db.add(job)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        original = db.get(TelemetryReading, result["id"])
        fields = {
            column.name: getattr(original, column.name)
            for column in TelemetryReading.__table__.columns
            if column.name != "id"
        }
        db.add(TelemetryReading(**fields))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        fields["message_id"] = uuid4()
        fields["configuration_version"] = 999
        db.add(TelemetryReading(**fields))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    assert counts(factory) == (1, 1)


def test_history_filters_pagination(registry, packet):
    client, _ = registry
    rows = []
    for stamp in ["06:31:00", "06:30:00", "06:32:00", "06:31:00"]:
        packet.update(message_id=str(uuid4()), timestamp=f"2026-10-08T{stamp}Z")
        rows.append(post(client, packet))
    expected = [rows[1], rows[0], rows[3], rows[2]]
    assert client.get(path(packet)).json()["items"] == expected
    assert (
        client.get(path(packet), params={"limit": 2, "offset": 1}).json()["items"]
        == expected[1:3]
    )
    assert client.get(path(packet), params={"offset": 4}).json()["items"] == []
    filtered = client.get(
        path(packet),
        params={"start": "2026-10-08T12:01:00+05:30", "end": "2026-10-08T06:32:00Z"},
    )
    assert filtered.status_code == 200 and filtered.json()["items"] == expected[1:3]
    for params in [
        {"limit": 101},
        {"limit": 0},
        {"offset": -1},
        {"start": "2026-10-08T06:30:00"},
        {"start": "bad"},
        {"start": "1760000000"},
        {"start": "2026-10-08T06:32:00Z", "end": "2026-10-08T06:32:00Z"},
    ]:
        assert client.get(path(packet), params=params).status_code == 422


def test_database_failure_sanitized(registry, packet, monkeypatch):
    client, _ = registry

    def fail(*args):
        raise OperationalError("query", {}, Exception("private-password"))

    monkeypatch.setattr("backend.app.services.telemetry.history", fail)
    response = client.get(path(packet))
    assert response.status_code == 503 and "private-password" not in response.text


def test_migration_preserves_registry(registry, packet):
    _, factory = registry
    from alembic import command
    from alembic.config import Config

    with factory.kw["bind"].begin() as connection:
        config = Config("backend/alembic.ini")
        config.attributes["connection"] = connection
        command.downgrade(config, "f272b723f71b")
        assert connection.scalar(text("SELECT count(*) FROM assets")) == 1
        assert connection.scalar(text("SELECT count(*) FROM asset_configurations")) == 1
        command.upgrade(config, "head")
        assert connection.scalar(text("SELECT count(*) FROM assets")) == 1
        assert connection.scalar(text("SELECT count(*) FROM telemetry_readings")) == 0


def test_concurrent_distinct_readings_use_serialized_watermark(registry, packet):
    client, factory = registry
    barrier = Barrier(8)

    def submit(index):
        body = {
            **packet,
            "message_id": str(uuid4()),
            "timestamp": f"2026-10-08T06:{30 + index}:00Z",
        }
        barrier.wait(timeout=10)
        return post(client, body)

    with ThreadPoolExecutor(max_workers=8) as executor:
        rows = list(executor.map(submit, range(8)))
    maximum = None
    for row in sorted(rows, key=lambda reading: reading["id"]):
        stamp = row["measurement_time"]
        older = maximum is not None and stamp < maximum
        assert row["out_of_order"] == older
        assert row["processing_job"]["state_policy"] == (
            "historical_only" if older else "forward_only"
        )
        maximum = max(maximum, stamp) if maximum else stamp
    assert client.get(path(packet) + "/latest").json()["measurement_time"] == maximum
    assert counts(factory) == (8, 8)


def test_deduplication_has_no_24_hour_expiry(registry, packet):
    client, factory = registry
    first = post(client, packet)
    with factory() as db:
        reading = db.get(TelemetryReading, first["id"])
        reading.arrival_time -= timedelta(days=365)
        db.commit()
    result = client.post(ROOT, json=packet)
    assert result.status_code == 200 and result.json()["id"] == first["id"]
    assert result.json()["processing_job"] == first["processing_job"]
    assert counts(factory) == (1, 1)


def test_deduplication_is_scoped_to_asset(registry, packet, configuration):
    client, factory = registry
    post(client, packet)
    client.post(
        "/api/v1/assets",
        json={
            "asset_id": "other",
            "name": "Other",
            "location": "Lab",
            "timezone": "UTC",
        },
    )
    client.post("/api/v1/assets/other/configurations", json=configuration)
    packet["asset_id"] = "other"
    post(client, packet)
    assert counts(factory) == (2, 2)


def test_real_job_insert_failure_is_atomic(registry, packet):
    client, factory = registry
    with factory.kw["bind"].begin() as connection:
        connection.execute(
            text("""CREATE FUNCTION reject_job() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'private-internal-message'; END; $$""")
        )
        connection.execute(
            text("""CREATE TRIGGER reject_job BEFORE INSERT ON telemetry_processing_jobs
            FOR EACH ROW EXECUTE FUNCTION reject_job()""")
        )
    failed = client.post(ROOT, json=packet)
    assert failed.status_code == 503 and "private-internal-message" not in failed.text
    assert counts(factory) == (0, 0)
    with factory.kw["bind"].begin() as connection:
        connection.execute(text("DROP TRIGGER reject_job ON telemetry_processing_jobs"))
        connection.execute(text("DROP FUNCTION reject_job()"))
    post(client, packet)
    assert counts(factory) == (1, 1)
