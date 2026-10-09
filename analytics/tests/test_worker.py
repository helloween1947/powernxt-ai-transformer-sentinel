"""Analytical cases, not simulator-vs-predictor accuracy measurements."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math
from uuid import uuid4

import pytest

from analytics import process_stored_reading
from analytics.worker import MODEL_VERSION
from analytics.tests.test_adapter import config, packet


def bound_config(thermal=True, **changes):
    result = config(thermal=thermal, **changes)
    result["created_at"] = "2026-01-01T00:00:00Z"
    return result


def record(second=0, **changes):
    reading = packet(second, **changes)
    return {"id": second + 1, "asset_id": reading["asset_id"], "source": reading["source"],
            "run_id": reading.get("run_id"), "configuration_version": reading["configuration_version"],
            "message_id": reading["message_id"], "measurement_time": reading["timestamp"],
            "normalized_telemetry": reading, "quality_flags": {},
            "processing_job": {"state_policy": "forward_only"}}


def with_measurements(second=0, **measurements):
    result = record(second)
    result["normalized_telemetry"]["measurements"].update(measurements)
    return result


def test_balanced_line_line_units():
    result = process_stored_reading(record(), bound_config())
    assert result["electrical_metrics"]["apparent_power_kva"] == pytest.approx(math.sqrt(3) * 11000 * 52.49 / 1000)
    assert result["electrical_metrics"]["phase_loading_pct"] == [100, 100, 100]
    assert result["electrical_metrics"]["thermal_load_pu"] == 1
    assert result["electrical_metrics"]["active_power_kw"] is None
    assert result["electrical_metrics"]["power_factor"] is None
    assert result["metadata"]["units"]["apparent_power_kva"] == "kVA"


def test_phase_neutral_known_case_and_partial_phase_loading():
    row = with_measurements(voltage_r_v=230, voltage_y_v=230, voltage_b_v=230,
                            current_r_a=25, current_y_a=50, current_b_a=75)
    cfg = bound_config(rated_voltage_v=230, rated_current_a=50, voltage_convention="phase_to_neutral")
    output = process_stored_reading(row, cfg)["electrical_metrics"]
    assert output["apparent_power_kva"] == 34.5
    assert output["phase_loading_pct"] == [50, 100, 150]
    assert output["current_magnitude_imbalance_pct"] == 50
    row["normalized_telemetry"]["measurements"]["current_y_a"] = None
    output = process_stored_reading(row, cfg)["electrical_metrics"]
    assert output["phase_loading_pct"] == [50, None, 150]
    assert output["apparent_power_kva"] is None


def test_zero_is_not_missing_and_zero_reference_imbalance_unavailable():
    output = process_stored_reading(with_measurements(current_r_a=0, current_y_a=0, current_b_a=0), bound_config())
    assert output["electrical_metrics"]["thermal_load_pu"] == 0
    assert output["electrical_metrics"]["apparent_power_kva"] == 0
    assert output["electrical_metrics"]["phase_loading_pct"] == [0, 0, 0]
    assert output["electrical_metrics"]["current_magnitude_imbalance_pct"] is None
    assert output["data_confidence"]["score"] is None
    assert output["condition_contributors"]["health_index"] is None


@pytest.mark.parametrize("flag", ["suspect", "bad", "missing"])
def test_explicit_producer_quality_masks_channel(flag):
    row = record()
    row["normalized_telemetry"]["measurement_quality"] = {"current_y_a": flag}
    if flag == "missing":
        row["normalized_telemetry"]["measurements"]["current_y_a"] = None
    output = process_stored_reading(row, bound_config())
    assert output["electrical_metrics"]["phase_loading_pct"][1] is None
    assert output["data_confidence"]["channels"]["current_y_a"]["reasons"] == [flag]


@pytest.mark.parametrize("value", [-1, True, float("nan"), float("inf")])
def test_invalid_numbers_are_unavailable_and_output_is_finite(value):
    output = process_stored_reading(with_measurements(current_y_a=value), bound_config())
    assert output["electrical_metrics"]["thermal_load_pu"] is None
    json.dumps(output, allow_nan=False)


def test_ingestion_flags_are_honored_without_mutating_inputs():
    row = record()
    row["quality_flags"]["oil_temperature_c"] = ["outside_sanity_range"]
    before, cfg = deepcopy(row), bound_config()
    previous_cfg = deepcopy(cfg)
    output = process_stored_reading(row, cfg)
    assert output["thermal_assessment"]["measured_top_oil_temperature_c"] is None
    assert output["updated_state"]["thermal"]["initialized"] is False
    assert row == before
    assert cfg == previous_cfg


def test_bootstrap_is_measurement_not_an_independent_prediction():
    output = process_stored_reading(record(), bound_config())
    assert output["updated_state"]["thermal"]["oil_temp_c"] == 55
    assert output["thermal_assessment"]["initial_condition"]["value"] == 55
    assert output["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    assert output["thermal_assessment"]["thermal_residual_c"] is None


def test_exact_elapsed_response_and_residual_sign():
    cfg = bound_config()
    first = process_stored_reading(record(), cfg)
    state = json.loads(json.dumps(first["updated_state"], allow_nan=False))
    row = with_measurements(60, oil_temperature_c=60)
    output = process_stored_reading(row, cfg, state)
    # Rated K=1 -> target=30+40=70 C. Independently solve dT/dt=(70-T)/10800.
    expected = 70 + (55 - 70) * math.exp(-60 / 10800)
    assert output["thermal_assessment"]["predicted_top_oil_temperature_c"] == pytest.approx(expected)
    assert output["thermal_assessment"]["thermal_residual_c"] == pytest.approx(60 - expected)
    row["normalized_telemetry"]["measurements"]["oil_temperature_c"] = 50
    assert process_stored_reading(row, cfg, state)["thermal_assessment"]["thermal_residual_c"] == pytest.approx(50 - expected)
    assert state == first["updated_state"]


def test_previous_sample_drives_interval_and_partition_identity():
    cfg = bound_config()
    initial = process_stored_reading(record(), cfg)["updated_state"]
    changed = with_measurements(60, current_r_a=0, current_y_a=0, current_b_a=0)
    transition = process_stored_reading(changed, cfg, initial)
    assert transition["thermal_assessment"]["predicted_top_oil_temperature_c"] == pytest.approx(70 - 15 * math.exp(-60 / 10800))
    midpoint = process_stored_reading(record(60), cfg, initial)["updated_state"]
    stepped = process_stored_reading(record(120), cfg, midpoint)
    joined = process_stored_reading(record(120), cfg, initial)
    assert stepped["thermal_assessment"]["predicted_top_oil_temperature_c"] == pytest.approx(joined["thermal_assessment"]["predicted_top_oil_temperature_c"])


def test_missing_initial_channel_can_bootstrap_later_explicitly():
    cfg = bound_config()
    first = process_stored_reading(with_measurements(oil_temperature_c=None), cfg)
    second = process_stored_reading(record(60), cfg, first["updated_state"])
    assert second["thermal_assessment"]["initial_condition"] is not None
    assert second["thermal_assessment"]["thermal_residual_c"] is None


def test_missing_interval_input_latches_unknown_history():
    cfg = bound_config()
    state = process_stored_reading(record(), cfg)["updated_state"]
    missing = process_stored_reading(with_measurements(60, current_y_a=None), cfg, state)
    assert missing["thermal_assessment"]["predicted_top_oil_temperature_c"] is not None  # Previous interval was known.
    broken = process_stored_reading(record(120), cfg, missing["updated_state"])
    assert broken["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    assert "preceding_interval_inputs_unavailable" in broken["thermal_assessment"]["reasons"]
    recovered = process_stored_reading(record(180), cfg, broken["updated_state"])
    assert recovered["thermal_assessment"]["predicted_top_oil_temperature_c"] is None


def test_oil_loss_does_not_destroy_load_driven_state():
    cfg = bound_config()
    state = process_stored_reading(record(), cfg)["updated_state"]
    second = process_stored_reading(with_measurements(60, oil_temperature_c=None), cfg, state)
    assert second["thermal_assessment"]["predicted_top_oil_temperature_c"] is not None
    assert second["thermal_assessment"]["thermal_residual_c"] is None
    third = process_stored_reading(record(120), cfg, second["updated_state"])
    assert third["thermal_assessment"]["thermal_residual_c"] is not None


@pytest.mark.parametrize("elapsed,available", [(300, True), (301, False)])
def test_gap_boundary(elapsed, available):
    cfg = bound_config()
    state = process_stored_reading(record(), cfg)["updated_state"]
    output = process_stored_reading(record(elapsed), cfg, state)
    assert (output["thermal_assessment"]["predicted_top_oil_temperature_c"] is not None) == available
    if not available:
        assert "measurement_gap_exceeds_300_s" in output["thermal_assessment"]["reasons"]


def test_same_reading_equal_time_and_late_do_not_advance():
    cfg, row = bound_config(), record(120)
    state = process_stored_reading(row, cfg)["updated_state"]
    before = deepcopy(state)
    for candidate in (row, record(120), record(60)):
        output = process_stored_reading(candidate, cfg, state)
        assert output["updated_state"] == state
        assert not output["execution_status"]["state_advanced"]
        assert output["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    assert before == state


def test_historical_policy_cannot_create_or_advance_state():
    row = record()
    row["processing_job"]["state_policy"] = "historical_only"
    assert process_stored_reading(row, bound_config())["updated_state"] is None
    state = process_stored_reading(record(), bound_config())["updated_state"]
    later = record(60)
    later["processing_job"]["state_policy"] = "historical_only"
    assert process_stored_reading(later, bound_config(), state)["updated_state"] == state


@pytest.mark.parametrize("changes", [{"run_id": "other"}, {"source": "file_replay"}, {"source": "device", "run_id": None}])
def test_run_and_source_isolation(changes):
    cfg = bound_config()
    state = process_stored_reading(record(), cfg)["updated_state"]
    with pytest.raises(ValueError, match="binding changed"):
        process_stored_reading(record(60, **changes), cfg, state)


def test_config_model_parameter_and_state_versions_require_explicit_reset():
    cfg = bound_config()
    state = process_stored_reading(record(), cfg)["updated_state"]
    with pytest.raises(ValueError, match="binding changed"):
        process_stored_reading(record(60, configuration_version=2), bound_config(version=2), state)
    changed = deepcopy(cfg)
    changed["thermal_parameters"]["oil_time_constant_min"] = 60
    with pytest.raises(ValueError, match="binding changed"):
        process_stored_reading(record(60), changed, state)
    for path, value in (("model_version", "other-model"), ("parameter_version", "other-profile")):
        modified = deepcopy(state)
        modified["binding"][path] = value
        with pytest.raises(ValueError, match="binding changed"):
            process_stored_reading(record(60), cfg, modified)
    modified = deepcopy(state)
    modified["schema_version"] = "legacy"
    with pytest.raises(ValueError, match="State schema"):
        process_stored_reading(record(60), cfg, modified)


def test_missing_thermal_parameters_no_fallback_and_named_reasons():
    result = process_stored_reading(record(), bound_config(thermal=False))
    assert result["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    assert "thermal_parameters.oil_time_constant_min" in result["thermal_assessment"]["reasons"]
    assert result["updated_state"]["thermal"]["oil_temp_c"] is None
    assert result["data_confidence"]["score"] is None
    assert result["metadata"]["model_version"] == MODEL_VERSION


def test_only_configured_threshold_evidence_no_alerts_or_scores():
    row = with_measurements(oil_temperature_c=106)
    output = process_stored_reading(row, bound_config())
    oil = next(r for r in output["anomaly_observations"] if r["quantity"] == "measured_top_oil_temperature_c")
    assert oil["breached"] is True
    assert oil["threshold"] == 105
    assert oil["unit"] == "C"
    assert all("severity" not in r and "incident_id" not in r for r in output["anomaly_observations"])
    cfg = bound_config(operational_limits={})
    cfg["parameter_provenance"] = {k: v for k, v in cfg["parameter_provenance"].items() if not k.startswith("operational_limits.")}
    output = process_stored_reading(row, cfg)
    assert all(r["breached"] is None for r in output["anomaly_observations"])


def test_original_payload_and_evaluation_labels_cannot_change_results():
    row = record()
    first = process_stored_reading(row, bound_config())
    row["original_payload"] = {"scenario": "overload", "oil_temperature_c": 200}
    row["ground_truth"] = "failed"
    assert process_stored_reading(row, bound_config()) == first


def test_envelope_identity_validation_and_stale_guard():
    row = record()
    row["measurement_time"] = "2026-01-01T00:01:00Z"
    with pytest.raises(ValueError, match="stream/time"):
        process_stored_reading(row, bound_config())
    row = record()
    row["quality_flags"]["stale"] = True
    assert process_stored_reading(row, bound_config())["updated_state"] is None


def test_real_elapsed_time_with_offset_and_roundtrip():
    cfg = bound_config()
    first = process_stored_reading(record(), cfg)
    row = record(60)
    row["measurement_time"] = row["normalized_telemetry"]["timestamp"] = "2026-01-01T05:31:00+05:30"
    output = process_stored_reading(row, cfg, json.loads(json.dumps(first["updated_state"])))
    assert output["thermal_assessment"]["elapsed_s"] == 60
    assert output["metadata"]["measurement_time"] == "2026-01-01T00:01:00Z"
