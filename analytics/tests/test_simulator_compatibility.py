"""Generator/adapter compatibility ONLY, never a predictive-accuracy benchmark.

Set SIMULATOR_REVIEW_ROOT to a read-only exported simulator checkout when the
simulator is not merged. No simulator files are copied into the analytics branch.
"""
import importlib.util
import json
import os
from pathlib import Path

import pytest

from backend.app.schemas.assets import ConfigurationResponse
from backend.tests.conftest import registry
from analytics import process_stored_reading


@pytest.fixture
def generator():
    root = Path(os.environ.get("SIMULATOR_REVIEW_ROOT", Path(__file__).resolve().parents[2]))
    path = root / "backend/app/simulator/generator.py"
    if not path.exists():
        pytest.skip("Simulator branch is not merged; set SIMULATOR_REVIEW_ROOT to reviewed 55a9c54 export")
    spec = importlib.util.spec_from_file_location("reviewed_normal_simulator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.VERSION == "normal-operation-1.0.0"
    return module


def prepare(client, thermal):
    cfg = json.loads((Path(__file__).resolve().parents[2] / "data/sample/asset-configuration-assumed.json").read_text())
    if thermal:
        cfg["thermal_parameters"] = {"rated_top_oil_rise_c": 40, "oil_time_constant_min": 180, "loss_ratio": 5, "oil_exponent": 0.8}
        cfg["parameter_provenance"].update({f"thermal_parameters.{k}": "assumed" for k in cfg["thermal_parameters"]})
    asset_id = "personb-simulator-compatibility"
    assert client.post("/api/v1/assets", json={"asset_id": asset_id, "name": "Synthetic test", "location": "Test", "timezone": "UTC"}).status_code == 201
    response = client.post(f"/api/v1/assets/{asset_id}/configurations", json=cfg)
    assert response.status_code == 201, response.text
    return ConfigurationResponse.model_validate(response.json())


@pytest.mark.parametrize("thermal", [False, True])
def test_six_generated_packets_real_ingestion_then_worker(registry, generator, thermal):
    client, factory = registry
    config = prepare(client, thermal)
    spec = generator.RunSpec(asset_id=config.asset_id, configuration_version=1, run_id="personb-normal-local-test", seed=42,
                             start="2026-01-01T00:00:00Z", duration_seconds=301, interval_seconds=60, initial_oil_temperature_c=45)
    packets = generator.generate(spec, config)
    assert len(packets) == 6
    state = None
    for index, packet in enumerate(packets):
        response = client.post("/api/v1/telemetry", json=packet)
        assert response.status_code == 201
        stored = response.json()
        output = process_stored_reading(stored, config.model_dump(mode="json"), state)
        assert output["metadata"]["reading_identity"]["reading_id"] == stored["id"]
        assert stored["processing_job"]["status"] == "pending"
        assert output["data_confidence"]["channels"]["oil_level_pct"]["usable"] is False
        if not thermal or index == 0:
            assert output["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
        else:
            assert output["thermal_assessment"]["predicted_top_oil_temperature_c"] is not None
            assert output["thermal_assessment"]["thermal_residual_c"] is not None
        state = json.loads(json.dumps(output["updated_state"], allow_nan=False))
        duplicate = client.post("/api/v1/telemetry", json=packet)
        assert duplicate.status_code == 200
        assert duplicate.json() == stored
        assert process_stored_reading(duplicate.json(), config.model_dump(mode="json"), state)["updated_state"] == state
    from sqlalchemy import func, select
    from backend.app.models.telemetry import ProcessingJob, TelemetryReading
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(TelemetryReading)) == 6
        assert db.scalar(select(func.count()).select_from(ProcessingJob)) == 6
    device = client.get(f"/api/v1/assets/{config.asset_id}/telemetry").json()
    assert device["items"] == []
    assert state["last_measurement_time"] == "2026-01-01T00:05:00Z"


def test_load_limit_basis_counterexample(generator):
    # Evidence for the review: apparent capacity loading and worst-phase current
    # loading are different quantities, especially within the allowed rating tolerance.
    cfg = json.loads((Path(__file__).resolve().parents[2] / "data/sample/asset-configuration-assumed.json").read_text())
    cfg.update(asset_id="counterexample", version=1, created_at="2026-01-01T00:00:00Z", rated_kva=1040)
    cfg["operational_limits"]["max_load_pct"] = 75
    config = ConfigurationResponse.model_validate(cfg)
    spec = generator.RunSpec(asset_id="counterexample", configuration_version=1, run_id="limit-test", seed=42,
                             start="2026-01-01T00:00:00Z", duration_seconds=1000, interval_seconds=10, initial_oil_temperature_c=45)
    packets = generator.generate(spec, config)  # Accepted conservative apparent-power envelope.
    assert max(100 * p["measurements"][f"current_{phase}_a"] / config.rated_current_a for p in packets for phase in "ryb") > 75
