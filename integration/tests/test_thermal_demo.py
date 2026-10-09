"""Thermal handoff on the deployed model and real isolated API/worker."""
from copy import deepcopy
import json
import math
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.analytics.person_b import compute_analytics
from backend.app.schemas.assets import ConfigurationCreate, ConfigurationResponse
from backend.app.simulator.generator import RunSpec, generate
from backend.app.services.analytics_worker import run_once
from backend.tests.conftest import asset, configuration, registry
from integration.prepare_thermal_demo import PROFILE, main, prepare_configuration


def snapshot():
    cfg = json.loads(Path("data/sample/asset-configuration-assumed.json").read_text())
    cfg.update(asset_id="local-numerical-thermal-test", version=7, created_at="2026-01-01T00:00:00Z")
    return ConfigurationResponse.model_validate(cfg).model_dump(mode="json")


def reviewed(source=None):
    source = source or snapshot()
    payload = prepare_configuration(source, json.loads(PROFILE.read_text()))
    return {**payload, "asset_id": source["asset_id"], "version": source["version"], "created_at": source["created_at"]}


def telemetry(config, seconds):
    return {"schema_version": "1.0.0", "message_id": str(uuid4()), "asset_id": config["asset_id"],
            "source": "simulator", "run_id": "numerical-thermal-run", "configuration_version": config["version"],
            "timestamp": f"2026-01-01T00:{seconds//60:02d}:{seconds%60:02d}Z",
            "measurements": {**{f"current_{p}_a": config["rated_current_a"] for p in "ryb"},
                             **{f"voltage_{p}_v": config["rated_voltage_v"] for p in "ryb"},
                             "ambient_temperature_c": 30, "oil_temperature_c": 55}}


def compute(cfg, seconds, previous=None):
    return compute_analytics(telemetry(cfg, seconds), cfg, {}, seconds+1, previous)


def test_existing_worker_sample_is_schema_valid_and_sufficient():
    cfg = ConfigurationCreate.model_validate_json(Path("data/sample/asset-configuration-worker-assumed.json").read_text())
    assert cfg.thermal_parameters.model_dump(exclude_none=True) == json.loads(PROFILE.read_text())["thermal_parameters"]


@pytest.mark.parametrize("convention,side,voltage,current,kva", [("line_to_line", "primary", 22000, 26.2432, 1000), ("phase_to_neutral", "secondary", 240, 100, 72)])
def test_payload_preserves_actual_electrical_fields_and_provenance(convention, side, voltage, current, kva):
    source = snapshot()
    source.update(voltage_convention=convention, measurement_side=side, rated_voltage_v=voltage, rated_current_a=current, rated_kva=kva)
    source["parameter_provenance"]["rated_current_a"] = "nameplate"
    before = deepcopy(source)
    payload = prepare_configuration(source, json.loads(PROFILE.read_text()))
    ConfigurationCreate.model_validate(payload)
    for key in ("rated_kva", "rated_current_a", "rated_voltage_v", "voltage_convention", "measurement_side", "cooling_type", "operational_limits"):
        assert payload[key] == source[key]
    assert payload["parameter_provenance"]["rated_current_a"] == "nameplate"
    assert "version" not in payload and "asset_id" not in payload and "created_at" not in payload
    assert source == before


def test_measured_coefficients_are_not_overwritten_by_assumptions():
    source = snapshot()
    source["thermal_parameters"]["loss_ratio"] = 6
    source["parameter_provenance"]["thermal_parameters.loss_ratio"] = "measured"
    cfg = reviewed(source)
    assert cfg["thermal_parameters"]["loss_ratio"] == 6
    assert cfg["parameter_provenance"]["thermal_parameters.loss_ratio"] == "measured"


def test_cli_reads_bom_and_refuses_to_overwrite(tmp_path):
    source, output = tmp_path/"baseline.json", tmp_path/"payload.json"
    source.write_text(json.dumps(snapshot()), encoding="utf-8-sig")
    args = ["--configuration-json", str(source), "--output", str(output)]
    assert main(args) == 0
    original = output.read_bytes()
    assert main(args) == 1
    assert output.read_bytes() == original


@pytest.mark.parametrize("value", [None, 0, -1, True, float("inf")])
def test_invalid_assumed_coefficients_rejected(value):
    p = json.loads(PROFILE.read_text())
    p["thermal_parameters"]["oil_time_constant_min"] = value
    with pytest.raises(ValueError):
        prepare_configuration(snapshot(), p)


@pytest.mark.parametrize("seconds", [1, 60, 137, 300])
def test_initialization_then_independent_elapsed_thermal_expectation(seconds):
    cfg = reviewed()
    first = compute(cfg, 0)
    assert first["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    assert first["thermal_assessment"]["thermal_residual_c"] is None
    assert first["execution_status"]["outcome"] == "partially_available"
    prior = json.loads(json.dumps(first["updated_state"], allow_nan=False))
    frame = telemetry(cfg, seconds)
    frame["measurements"].update(oil_temperature_c=60, ambient_temperature_c=40, current_r_a=0, current_y_a=0, current_b_a=0)
    output = compute_analytics(frame, cfg, {}, seconds+1, prior)
    expected = 70-15*math.exp(-seconds/10800)  # Rated K1 target30+40C; independent exact ODE solution.
    assert output["thermal_assessment"]["predicted_top_oil_temperature_c"] == pytest.approx(expected)
    assert output["thermal_assessment"]["thermal_residual_c"] == pytest.approx(60-expected)
    assert output["thermal_assessment"]["elapsed_s"] == seconds
    assert output["updated_state"]["thermal"]["oil_temp_c"] == pytest.approx(expected)
    json.dumps(output, allow_nan=False)


def test_gap_latches_and_configuration_model_and_run_isolate_state():
    cfg = reviewed()
    state = compute(cfg, 0)["updated_state"]
    gap = compute(cfg, 301, state)
    assert gap["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    assert "measurement_gap_exceeds_300_s" in gap["thermal_assessment"]["reasons"]
    assert compute(cfg, 360, gap["updated_state"])["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    for changed in ("version", "model", "run"):
        c, s, frame = deepcopy(cfg), deepcopy(state), telemetry(cfg, 60)
        if changed == "version":
            c["version"] += 1
            frame["configuration_version"] = c["version"]
        elif changed == "model":
            s["binding"]["model_version"] = "other"
        else:
            frame["run_id"] = "new-run"
        with pytest.raises(ValueError):
            compute_analytics(frame, c, {}, 2, s)
    assert compute({**cfg, "version": cfg["version"]+1}, 0)["thermal_assessment"]["initial_condition"] is not None


def test_missing_coefficients_still_give_exact_unavailable_paths():
    cfg = snapshot()
    output = compute(cfg, 0)
    assert output["execution_status"]["outcome"] == "unsupported_configuration"
    assert output["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    assert output["thermal_assessment"]["reasons"] == [f"thermal_parameters.{k}" for k in ("rated_top_oil_rise_c", "oil_time_constant_min", "loss_ratio", "oil_exponent")]


@pytest.mark.parametrize("channel", ["ambient_temperature_c", "oil_temperature_c", "current_y_a"])
def test_missing_channels_prevent_initialization(channel):
    cfg = reviewed()
    p = telemetry(cfg, 0)
    p["measurements"][channel] = None
    output = compute_analytics(p, cfg, {}, 1)
    assert not output["updated_state"]["thermal"]["initialized"]


def test_fresh_api_version_and_simulator_run_complete_in_durable_worker(registry, asset, configuration):
    client, factory = registry
    path = f"/api/v1/assets/{asset['asset_id']}/configurations"
    old = client.post(path, json=configuration).json()
    old_packet = generate(RunSpec(asset_id=asset["asset_id"], configuration_version=old["version"], run_id="original-no-thermal-local-test",
                                  seed=42, start="2026-01-01T00:00:00Z", duration_seconds=1, interval_seconds=60,
                                  initial_oil_temperature_c=45), ConfigurationResponse.model_validate(old))[0]
    old_response = client.post("/api/v1/telemetry", json=old_packet)
    assert old_response.status_code == 201
    old_id = old_response.json()["id"]
    assert run_once(factory)
    old_result = client.get(f"/api/v1/telemetry/{old_id}/analytics").json()
    assert old_result["result"]["payload"]["execution_status"]["outcome"] == "unsupported_configuration"
    # Make the returned version deliberately >2 to test capture, not assumption.
    assert client.post(path, json=configuration).status_code == 201
    payload = prepare_configuration(old, json.loads(PROFILE.read_text()))
    response = client.post(path, json=payload)
    assert response.status_code == 201
    cfg = ConfigurationResponse.model_validate(response.json())
    assert cfg.version == 3
    packets = generate(RunSpec(asset_id=asset["asset_id"], configuration_version=cfg.version, run_id="fresh-thermal-local-test",
                               seed=42, start="2026-01-01T00:00:00Z", duration_seconds=301, interval_seconds=60,
                               initial_oil_temperature_c=45), cfg)
    ids = []
    for p in packets:
        response = client.post("/api/v1/telemetry", json=p)
        assert response.status_code == 201
        ids.append(response.json()["id"])
    for _ in packets:
        assert run_once(factory)
    results = [client.get(f"/api/v1/telemetry/{identity}/analytics").json() for identity in ids]
    assert all(r["status"] == "completed" and r["configuration_version"] == cfg.version for r in results)
    thermal = [r["result"]["payload"]["thermal_assessment"] for r in results]
    assert thermal[0]["predicted_top_oil_temperature_c"] is None
    for row in thermal[1:]:
        assert math.isfinite(row["predicted_top_oil_temperature_c"])
        assert row["thermal_residual_c"] == pytest.approx(row["measured_top_oil_temperature_c"]-row["predicted_top_oil_temperature_c"])
        assert row["elapsed_s"] == 60
    latest = client.get(f"/api/v1/assets/{asset['asset_id']}/analytics/latest", params={"source": "simulator", "run_id": "fresh-thermal-local-test"}).json()
    assert latest["latest_completed_reading_id"] == ids[-1]
    assert client.get(path).json()["items"][0] == old
    assert client.get(f"/api/v1/telemetry/{old_id}/analytics").json() == old_result
    assert client.get(f"/api/v1/assets/{asset['asset_id']}/analytics/latest", params={"source": "device"}).json()["result"] is None
    json.dumps(results, allow_nan=False)


@pytest.mark.parametrize("profile", [None, [], {"thermal_parameters": None, "parameter_provenance": {}}])
def test_malformed_demo_profile_is_a_validation_error(profile):
    with pytest.raises(ValueError):
        prepare_configuration(snapshot(), profile)
