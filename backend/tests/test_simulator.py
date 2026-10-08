"""Synthetic generation, real schema admission and bounded delivery behavior."""

import csv
import io
import json
import math
from datetime import datetime, timezone
from itertools import pairwise
from urllib.error import HTTPError, URLError
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.app.schemas.assets import ConfigurationResponse
from backend.app.schemas.telemetry import TelemetryCreate
from backend.app.simulator import client as http
from backend.app.simulator.__main__ import main
from backend.app.simulator.client import Client, SubmissionError
from backend.app.simulator.generator import (
    Parameters,
    RunSpec,
    generate,
    write_artifacts,
)


@pytest.fixture
def config(configuration):
    return ConfigurationResponse(
        **configuration,
        asset_id="test-transformer",
        version=1,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def spec():
    return RunSpec(
        asset_id="test-transformer",
        configuration_version=1,
        run_id="test-run",
        seed=42,
        start="2026-01-01T00:00:00Z",
        duration_seconds=301,
        interval_seconds=60,
        initial_oil_temperature_c=45,
    )


def test_reproducible_schema_spacing_and_labels(spec, config):
    packets = generate(spec, config)
    assert packets == generate(spec, config)
    assert len(packets) == 6  # 0,60,...,300 < 301; no sample at 301
    parsed = [TelemetryCreate.model_validate(p) for p in packets]
    assert len({p.message_id for p in parsed}) == 6
    assert all(UUID(p["message_id"]).version == 4 for p in packets)
    assert [int((p.timestamp - spec.start).total_seconds()) for p in parsed] == [
        0,
        60,
        120,
        180,
        240,
        300,
    ]
    assert all(p.timestamp.utcoffset().total_seconds() == 0 for p in parsed)
    assert all(
        set(p)
        == {
            "schema_version",
            "message_id",
            "asset_id",
            "source",
            "run_id",
            "configuration_version",
            "timestamp",
            "measurements",
            "measurement_quality",
        }
        for p in packets
    )
    assert all(
        p["measurements"]["oil_level_pct"] is None
        and p["measurement_quality"]["oil_level_pct"] == "missing"
        for p in packets
    )
    changed = generate(spec.model_copy(update={"seed": 43}), config)
    assert changed[0]["message_id"] != packets[0]["message_id"]
    assert changed[0]["measurements"] != packets[0]["measurements"]


@pytest.mark.parametrize(
    "duration,interval,count", [(300, 60, 5), (1, 60, 1), (301, 60, 6)]
)
def test_half_open_count_and_offset_normalization(spec, duration, interval, count):
    values = spec.model_dump(mode="json")
    values.update(
        duration_seconds=duration,
        interval_seconds=interval,
        start="2026-01-01T05:30:00+05:30",
    )
    result = RunSpec.model_validate(values)
    assert result.sample_count == count
    assert result.start == datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "field,value",
    [
        ("seed", True),
        ("configuration_version", 0),
        ("run_id", "invalid run"),
        ("start", "2026-01-01T00:00:00"),
        ("duration_seconds", 0),
        ("interval_seconds", 0),
        ("initial_oil_temperature_c", float("nan")),
        ("initial_oil_temperature_c", 100),
        ("start", "9999-12-31T23:59:59Z"),
    ],
)
def test_invalid_run_inputs(spec, field, value):
    values = spec.model_dump(mode="json")
    values[field] = value
    with pytest.raises(ValidationError):
        RunSpec.model_validate(values)


@pytest.mark.parametrize(
    "values",
    [
        {"load_mean_pu": 0.8, "load_amplitude_pu": 0.3},
        {"thermal_time_constant_minutes": 0},
        {"oil_level_pct": 101},
        {"electrical_noise_pu": float("inf")},
        {"unknown_parameter": 1},
    ],
)
def test_invalid_parameters(values):
    with pytest.raises(ValidationError):
        Parameters(**values)


def test_configuration_voltage_conventions_and_side(spec, config):
    for convention, voltage, side in [
        ("line_to_line", 11000, "primary"),
        ("phase_to_neutral", 11000 / math.sqrt(3), "primary"),
        ("line_to_line", 415, "secondary"),
    ]:
        values = config.model_dump(mode="json")
        factor = math.sqrt(3) if convention == "line_to_line" else 3
        values.update(
            voltage_convention=convention,
            rated_voltage_v=voltage,
            measurement_side=side,
            rated_current_a=1000 * config.rated_kva / (factor * voltage),
        )
        selected = ConfigurationResponse.model_validate(values)
        packet = generate(spec, selected)[0]
        for phase in "ryb":
            assert (
                0.96 <= packet["measurements"][f"voltage_{phase}_v"] / voltage <= 1.04
            )
            assert (
                0.58
                <= packet["measurements"][f"current_{phase}_a"]
                / selected.rated_current_a
                <= 0.62
            )
    with pytest.raises(ValueError, match="disagree"):
        generate(spec, config.model_copy(update={"rated_voltage_v": 415}))
    with pytest.raises(ValueError, match="reference"):
        generate(spec, config.model_copy(update={"version": 2}))
    limits = config.operational_limits.model_copy(update={"max_top_oil_temp_c": 40})
    with pytest.raises(ValueError, match="thermal envelope"):
        generate(spec, config.model_copy(update={"operational_limits": limits}))


def test_gradual_thermal_response_and_optional_level(spec, config):
    p = Parameters(load_amplitude_pu=0, ambient_amplitude_c=0, oil_level_pct=80)
    selected = spec.model_copy(
        update={"initial_oil_temperature_c": 30, "parameters": p}
    )
    packets = generate(selected, config)
    temperatures = [p["measurements"]["oil_temperature_c"] for p in packets]
    target = 25 + 40 * 0.6**2
    assert temperatures[0] == 30
    assert temperatures[1] == pytest.approx(
        target + (30 - target) * math.exp(-60 / 3600), abs=1e-6
    )
    assert all(0 < b - a < 0.2 for a, b in pairwise(temperatures))
    assert all(p["measurements"]["oil_level_pct"] == 80 for p in packets)


def test_artifacts_and_generate_only_cli(spec, config, tmp_path):
    file = tmp_path / "configuration.json"
    file.write_text(config.model_dump_json())
    out = tmp_path / "run"
    assert (
        main(
            [
                "generate",
                "--asset-id",
                spec.asset_id,
                "--configuration-version",
                "1",
                "--run-id",
                spec.run_id,
                "--seed",
                "42",
                "--start",
                "2026-01-01T00:00:00Z",
                "--duration-seconds",
                "301",
                "--interval-seconds",
                "60",
                "--initial-oil-temperature-c",
                "45",
                "--configuration-json",
                str(file),
                "--output-dir",
                str(out),
            ]
        )
        == 0
    )
    packets = [
        json.loads(line) for line in (out / "telemetry.jsonl").read_text().splitlines()
    ]
    assert packets == generate(spec, config)
    with (out / "telemetry.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["oil_level_pct"] == ""
    assert rows[0]["current_r_a"] == str(packets[0]["measurements"]["current_r_a"])
    assert json.loads((out / "run-metadata.json").read_text())["sample_count"] == 6
    with pytest.raises(ValueError, match="already exist"):
        write_artifacts(spec, config, out)


class Response(io.BytesIO):
    def __init__(self, status):
        super().__init__(b"{}")
        self.status = status


def test_retry_identity_and_summary(spec, config, monkeypatch):
    data = (json.dumps(generate(spec, config)[0]) + "\n").encode()
    seen = []
    outcomes = [
        URLError("lost response"),
        HTTPError("http://local", 503, "busy", {}, None),
        201,
        200,
    ]

    def open_request(req, timeout):
        seen.append((req.data, timeout))
        result = outcomes.pop(0)
        if isinstance(result, Exception):
            raise result
        return Response(result)

    monkeypatch.setattr(http, "urlopen", open_request)
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    client = Client(timeout_seconds=2, retries=2)
    assert client.send([data, data]) == {
        "created": 1,
        "identical_duplicates": 1,
        "failures": 0,
    }
    assert seen == [(data, 2)] * 4


@pytest.mark.parametrize("status", [409, 422, 404])
def test_permanent_errors_stop_without_retry(spec, config, monkeypatch, status):
    calls = []

    def fail(req, timeout):
        calls.append(req.data)
        raise HTTPError("http://local", status, "rejected", {}, None)

    monkeypatch.setattr(http, "urlopen", fail)
    with pytest.raises(SubmissionError, match=f"HTTP {status}") as raised:
        Client().send([json.dumps(p) for p in generate(spec, config)])
    assert len(calls) == 1
    assert raised.value.summary == {
        "created": 0,
        "identical_duplicates": 0,
        "failures": 1,
    }


def test_exhausted_retries_and_pacing(spec, config, monkeypatch):
    calls = []
    waits = []

    def fail(req, timeout):
        calls.append(req.data)
        raise URLError("offline")

    monkeypatch.setattr(http, "urlopen", fail)
    monkeypatch.setattr(http.time, "sleep", waits.append)
    lines = [json.dumps(p) for p in generate(spec, config)]
    with pytest.raises(SubmissionError, match="3 attempts"):
        Client(retries=2).send(lines)
    assert len(calls) == 3 and len(set(calls)) == 1
    assert waits == [0.25, 0.5]
    waits.clear()
    seen = []

    def ok(req, timeout):
        seen.append(req.data)
        return Response(201)

    monkeypatch.setattr(http, "urlopen", ok)
    Client().send(lines, paced=True)
    assert waits == [60] * 5
    assert seen == [line.encode() for line in lines]


def test_entire_file_validated_before_post(spec, config, monkeypatch):
    monkeypatch.setattr(
        http,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("must not POST invalid artifact"),
    )
    lines = [json.dumps(generate(spec, config)[0]), '{"fault_label":"fault"}']
    with pytest.raises(ValidationError):
        Client().send(lines)


def test_generated_sequence_real_postgres(registry, asset, configuration, spec):
    client, _factory = registry
    response = client.post(
        f"/api/v1/assets/{asset['asset_id']}/configurations", json=configuration
    )
    config = ConfigurationResponse.model_validate(response.json())
    packets = generate(spec, config)
    for packet in packets:
        accepted = client.post("/api/v1/telemetry", json=packet)
        assert accepted.status_code == 201
        assert accepted.json()["original_payload"] == packet
        assert accepted.json()["analytics_status"] == "pending"
        assert accepted.json()["processing_job"]["status"] == "pending"
        assert client.post("/api/v1/telemetry", json=packet).status_code == 200
    query = {"source": "simulator", "run_id": spec.run_id}
    history = client.get(
        f"/api/v1/assets/{spec.asset_id}/telemetry", params=query
    ).json()["items"]
    assert [r["original_payload"] for r in history] == packets
    assert (
        client.get(
            f"/api/v1/assets/{spec.asset_id}/telemetry/latest", params=query
        ).json()["measurement_time"]
        == packets[-1]["timestamp"]
    )
    assert client.get(f"/api/v1/assets/{spec.asset_id}/telemetry").json()["items"] == []
