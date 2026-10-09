"""Counterexamples found in the Person B source audit."""
from dataclasses import replace
import json

import pytest

from analytics import process_reading, process_stored_reading, evaluate_persistent_rules, forecast_from_worker_state
from analytics.tests.test_worker import bound_config, record, with_measurements
from analytics.tests.test_persistence import frame, policy
from analytics.transformer_twin import AssetConfig, ThermalState
from analytics.transformer_twin.model import finite, _advance
from analytics.transformer_twin.engine import _timestamp


def test_legacy_adapter_is_fully_reproducible():
    row, cfg = record(), bound_config()
    assert process_reading(row["normalized_telemetry"], {}, cfg) == process_reading(row["normalized_telemetry"], {}, cfg)


def test_huge_integer_is_invalid_numeric_evidence_not_a_crash():
    assert finite(10**1000) is False
    assert process_stored_reading(with_measurements(current_y_a=10**1000), bound_config())["electrical_metrics"]["thermal_load_pu"] is None


@pytest.mark.parametrize("flag", ["stale", "clamped"])
@pytest.mark.parametrize("value", ["false", 1, [], None])
def test_global_flags_require_booleans(flag, value):
    row = record()
    row["quality_flags"][flag] = value
    with pytest.raises(ValueError):
        process_stored_reading(row, bound_config())


@pytest.mark.parametrize("field,value", [("initialized", "false"), ("valid", "false"), ("oil_temp_c", "55"), ("oil_temp_c", None)])
def test_malformed_thermal_state_is_rejected_before_computation(field, value):
    state = process_stored_reading(record(), bound_config())["updated_state"]
    state["thermal"][field] = value
    with pytest.raises(ValueError):
        process_stored_reading(record(60), bound_config(), state)


def test_malformed_forecast_state_is_not_treated_as_valid():
    state = process_stored_reading(record(), bound_config())["updated_state"]
    state["thermal"]["valid"] = "false"
    with pytest.raises(ValueError):
        forecast_from_worker_state(state, bound_config(), [{"duration_s": 60, "thermal_load_pu": 1, "ambient_temp_c": 30}])


def test_capacity_arithmetic_unavailability_stays_finite():
    cfg = bound_config(rated_kva=1e-320)
    output = process_stored_reading(record(), cfg)
    assert output["electrical_metrics"]["capacity_loading_pct"] is None
    assert "electrical_arithmetic_unavailable" in output["execution_status"]["availability"]["electrical_metrics.capacity_loading_pct"]["reasons"]
    json.dumps(output, allow_nan=False)


def test_large_but_representable_loading_and_imbalance():
    cfg = bound_config(rated_current_a=1e308)
    row = with_measurements(current_r_a=1e308, current_y_a=5e307, current_b_a=0)
    output = process_stored_reading(row, cfg)
    assert output["electrical_metrics"]["phase_loading_pct"] == [100, 50, 0]
    assert output["electrical_metrics"]["current_magnitude_imbalance_pct"] == 100
    json.dumps(output, allow_nan=False)


def test_zero_elapsed_does_not_compute_an_unneeded_overflowing_target():
    cfg = replace(AssetConfig(), oil_exponent=1e308)
    state = ThermalState(55, 30, cfg)
    assert _advance(state, 2, 30, 0).predicted_oil_temp_c == 55


def test_unrepresentable_utc_time_has_consistent_validation_error():
    with pytest.raises(ValueError):
        _timestamp("0001-01-01T00:00:00+23:00")


@pytest.mark.parametrize("value", ["false", 1, None])
def test_detector_requires_explicit_boolean_eligibility(value):
    row = frame(0)
    row["execution_status"]["state_advanced"] = value
    with pytest.raises(ValueError):
        evaluate_persistent_rules(row, policy())


@pytest.mark.parametrize("field,value", [("active", "false"), ("sequence", -1), ("pending_s", -10), ("recovery_s", -10)])
def test_detector_rejects_corrupt_restored_state(field, value):
    state = evaluate_persistent_rules(frame(0), policy())["updated_state"]
    state["rules"]["capacity_overload"][field] = value
    with pytest.raises(ValueError):
        evaluate_persistent_rules(frame(60), policy(), state)


@pytest.mark.parametrize("group,key", [("thermal_parameters", "scenario_temperature"), ("operational_limits", "fault_label")])
def test_config_rejects_unknown_parameter_fields(group, key):
    cfg = bound_config()
    cfg[group][key] = None
    with pytest.raises(ValueError):
        process_stored_reading(record(), cfg)


@pytest.mark.parametrize("value", [None, [], "reading", {}])
def test_normalized_facade_rejects_malformed_payload(value):
    from analytics import compute_analytics
    with pytest.raises(ValueError):
        compute_analytics(value, bound_config(), {}, 1)


@pytest.mark.parametrize("field,value", [("asset_id", 1), ("run_id", []), ("measurement_quality", [])])
def test_malformed_normalized_identity_and_quality_are_rejected(field, value):
    row = record()
    row["normalized_telemetry"][field] = value
    if field in row:
        row[field] = value
    with pytest.raises(ValueError):
        process_stored_reading(row, bound_config())


def test_legacy_restore_rejects_nonboolean_thermal_validity():
    from analytics.transformer_twin import TwinEngine
    snapshot = TwinEngine().snapshot()
    snapshot["thermal_state"]["valid"] = "false"
    with pytest.raises(ValueError):
        TwinEngine.restore(snapshot)


@pytest.mark.parametrize("field,value", [("active", "false"), ("sequence", -1), ("pending_s", -1)])
def test_legacy_restore_rejects_corrupt_alert_state(field, value):
    from analytics.transformer_twin import TwinEngine
    snapshot = TwinEngine().snapshot()
    item = {"active": False, "sequence": 0, "pending_s": 0, "recovery_s": 0}
    item[field] = value
    snapshot["alert_history"]["overload"] = item
    with pytest.raises(ValueError):
        TwinEngine.restore(snapshot)


def test_legacy_initialization_waits_for_usable_currents_and_can_retry():
    first = process_reading(with_measurements(current_y_a=None)["normalized_telemetry"], {}, bound_config())
    assert first["updated_state"]["thermal_initialized"] is False
    second = process_reading(record(60)["normalized_telemetry"], {}, bound_config(), first["updated_state"])
    assert second["updated_state"]["thermal_initialized"] is True
    assert second["thermal_assessment"]["predicted_top_oil_temperature_c"] == 55
