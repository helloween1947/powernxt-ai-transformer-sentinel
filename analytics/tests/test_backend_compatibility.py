"""Real API + migrated PostgreSQL -> Person B -> forecast, without changing A's worker status."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

import pytest

from backend.tests.conftest import registry  # Reuse A's isolated, freshly migrated schemas.
from analytics import process_telemetry_response, compare_what_if
from analytics.tests.test_adapter import config, packet


@pytest.fixture
def configured_asset(registry):
    client, _ = registry
    asset = {"asset_id": "DT-001", "name": "Analytics compatibility test", "location": "Test lab", "timezone": "UTC"}
    assert client.post("/api/v1/assets", json=asset).status_code == 201
    body = config()
    body.pop("asset_id")
    body.pop("version")
    response = client.post("/api/v1/assets/DT-001/configurations", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def ingest(client, row):
    response = client.post("/api/v1/telemetry", json=row)
    assert response.status_code == 201, response.text
    return response.json()


def test_api_reading_to_analytics_persistent_alert_and_what_if(registry, configured_asset):
    client, _ = registry
    state = None
    for second in (0, 60, 120, 180):
        row = packet(second)
        for phase in ("r", "y", "b"):
            row["measurements"][f"current_{phase}_a"] = 70
        response = ingest(client, row)
        assert response["analytics_status"] == "pending"  # No fabricated job completion.
        output = process_telemetry_response(response, configured_asset, state)
        assert output["execution_status"]["status"] == "computed"
        assert output["metadata"]["configuration_version"] == response["configuration_version"]
        state = json.loads(json.dumps(output["updated_state"], allow_nan=False))
    alert = next(a for a in output["anomaly_observations"] if a["category"] == "overload")
    assert alert["lifecycle"] == "opened"
    assert alert["threshold"] == 120
    assert output["thermal_assessment"]["predicted_top_oil_temperature_c"] > 55
    comparison = compare_what_if(state, [
        {"name": "keep", "profile": [{"duration_s": 7200, "load_pu": 1.3, "ambient_temp_c": 30}]},
        {"name": "reduce", "profile": [{"duration_s": 7200, "load_pu": 0.7, "ambient_temp_c": 30}]},
    ])
    assert comparison["scenarios"][1]["final_delta_from_baseline_c"] < 0
    assert comparison["configuration_version"] == 1


def test_api_flags_are_applied_and_original_metadata_is_not_read(registry, configured_asset):
    client, _ = registry
    row = packet()
    row["measurements"]["current_y_a"] = -1
    row["measurement_quality"] = {"oil_temperature_c": "suspect"}
    response = ingest(client, row)
    assert response["quality_flags"]["current_y_a"] == ["negative_magnitude"]
    response["original_payload"]["scenario_label"] = "normal"
    output = process_telemetry_response(response, configured_asset)
    assert output["electrical_metrics"]["thermal_load_pu"] is None
    assert output["thermal_assessment"]["measured_top_oil_temperature_c"] is None
    assert output["data_confidence"]["score"] == 6 / 8
    assert "negative_magnitude" in output["data_confidence"]["quality_reasons"]["current_y_a"]
    assert output["execution_status"]["status"] == "insufficient_data"
    json.dumps(output, allow_nan=False)


def test_api_duplicate_equal_time_late_and_delayed_job_do_not_change_state(registry, configured_asset):
    client, _ = registry
    first_row = packet(0)
    first = ingest(client, first_row)
    later = ingest(client, packet(120))  # Both initially eligible at admission.
    state = process_telemetry_response(later, configured_asset)["updated_state"]
    before = deepcopy(state)
    delayed = process_telemetry_response(first, configured_asset, state)
    assert delayed["updated_state"] == before
    assert not delayed["execution_status"]["state_advanced"]
    assert "not_newer_than_processed_watermark" in delayed["execution_status"]["reasons"]
    retry = client.post("/api/v1/telemetry", json=first_row)
    assert retry.status_code == 200
    for row in (packet(60), packet(120)):
        historical = ingest(client, row)
        assert historical["processing_job"]["state_policy"] == "historical_only"
        assert process_telemetry_response(historical, configured_asset, state)["updated_state"] == before
    assert state == before


def test_api_stream_namespaces_and_versions_are_bound(registry, configured_asset):
    client, _ = registry
    simulator = ingest(client, packet())
    state = process_telemetry_response(simulator, configured_asset)["updated_state"]
    replay = ingest(client, packet(60, source="file_replay"))
    replay_state = process_telemetry_response(replay, configured_asset)["updated_state"]
    assert replay_state["stream"] != state["stream"]
    with pytest.raises(ValueError, match="asset/source/run_id"):
        process_telemetry_response(replay, configured_asset, state)
    cfg2 = {k: v for k, v in configured_asset.items() if k not in ("asset_id", "version", "created_at")}
    cfg2["rated_current_a"] = 60
    bound2 = client.post("/api/v1/assets/DT-001/configurations", json=cfg2).json()
    second = ingest(client, packet(120, configuration_version=2))
    with pytest.raises(ValueError, match="Configuration changed"):
        process_telemetry_response(second, bound2, state)
    with pytest.raises(ValueError, match="bound ConfigurationResponse"):
        process_telemetry_response(second, configured_asset)
    # Deliberate cold start is explicit and selects the supplied immutable version.
    reset = process_telemetry_response(second, bound2)
    assert reset["updated_state"]["configuration_version"] == 2


def test_missing_thermal_configuration_from_registry_stays_unavailable(registry):
    client, _ = registry
    assert client.post("/api/v1/assets", json={"asset_id": "DT-001", "name": "Missing thermal", "location": "Lab", "timezone": "UTC"}).status_code == 201
    body = config(thermal=False)
    body.pop("asset_id")
    body.pop("version")
    bound = client.post("/api/v1/assets/DT-001/configurations", json=body).json()
    output = process_telemetry_response(ingest(client, packet()), bound)
    assert output["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    assert output["data_confidence"]["score"] == 1
    assert output["execution_status"]["status"] == "degraded"
    with pytest.raises(ValueError):
        compare_what_if(output["updated_state"], [])


def test_device_arrival_freshness_and_replay_event_time(registry, configured_asset):
    client, _ = registry
    row = packet(source="device", run_id=None)
    row["timestamp"] = datetime.now(timezone.utc).isoformat()
    output = process_telemetry_response(ingest(client, row), configured_asset)
    assert output["execution_status"]["state_advanced"]
    old = packet(source="device", run_id=None)
    old["timestamp"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    stale_response = ingest(client, old)
    # Force forward_only here to prove freshness is checked independently of admission.
    stale_response["processing_job"]["state_policy"] = "forward_only"
    stale = process_telemetry_response(stale_response, configured_asset)
    assert not stale["execution_status"]["state_advanced"]
    assert "stale_at_arrival" in stale["execution_status"]["reasons"]
    replay = process_telemetry_response(ingest(client, packet()), configured_asset)
    assert replay["execution_status"]["state_advanced"]  # Old scenario time is legitimate for replay.
