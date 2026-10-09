"""Worker decisions checked without a database or simulator accuracy claims."""
from copy import deepcopy
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from analytics import compute_analytics, process_stored_reading
from analytics.tests.test_worker import bound_config, record, with_measurements


@pytest.mark.parametrize("side", ["primary", "secondary"])
@pytest.mark.parametrize("convention,voltage,power", [("line_to_line", 400, math.sqrt(3)*400*10/1000), ("phase_to_neutral", 230, 6.9)])
def test_measurement_side_and_convention(side, convention, voltage, power):
    cfg = bound_config(measurement_side=side, voltage_convention=convention, rated_voltage_v=voltage, rated_current_a=10)
    row = with_measurements(**{f"voltage_{p}_v": voltage for p in "ryb"}, **{f"current_{p}_a": 10 for p in "ryb"})
    result = process_stored_reading(row, cfg)
    assert result["electrical_metrics"]["apparent_power_kva"] == pytest.approx(power)
    assert result["electrical_metrics"]["measurement_side"] == side


def test_imbalanced_loading_metrics_and_thermal_driver_are_separate():
    cfg = bound_config(rated_current_a=100, rated_voltage_v=230, rated_kva=69, voltage_convention="phase_to_neutral")
    row = with_measurements(**{f"voltage_{p}_v": 230 for p in "ryb"}, current_r_a=50, current_y_a=100, current_b_a=150)
    result = process_stored_reading(row, cfg)["electrical_metrics"]
    assert result["capacity_loading_pct"] == 100
    assert result["max_phase_loading_pct"] == 150
    assert result["thermal_load_pu"] == pytest.approx(math.sqrt(7/6))
    assert result["current_magnitude_imbalance_pct"] == 50


@pytest.mark.parametrize("dt", [1, 59, 60, 61, 137, 299, 300])
def test_actual_irregular_elapsed_time(dt):
    cfg = bound_config()
    state = process_stored_reading(record(), cfg)["updated_state"]
    result = process_stored_reading(record(dt), cfg, state)
    assert result["thermal_assessment"]["elapsed_s"] == dt
    assert result["thermal_assessment"]["predicted_top_oil_temperature_c"] == pytest.approx(70-15*math.exp(-dt/10800))


@pytest.mark.parametrize("case,outcome", [("full", "completed"), ("initial", "partially_available"), ("parameters", "unsupported_configuration"), ("current", "insufficient_input_or_state"), ("overflow", "computation_error")])
def test_explicit_worker_outcomes(case, outcome):
    cfg = bound_config(thermal=case != "parameters")
    if case == "overflow":
        cfg["thermal_parameters"]["oil_exponent"] = 1e308
    initial_row = with_measurements(current_r_a=104.98, current_y_a=104.98, current_b_a=104.98) if case == "overflow" else record()
    first = process_stored_reading(initial_row, cfg)
    row = record(60)
    if case == "current":
        row = with_measurements(60, current_y_a=None)
    result = first if case == "initial" else process_stored_reading(row, cfg, first["updated_state"])
    assert result["execution_status"]["outcome"] == outcome
    json.dumps(result, allow_nan=False)


def test_normalized_interface_schema_determinism_and_equivalence():
    row, cfg = record(), bound_config()
    args = {"normalized_telemetry": row["normalized_telemetry"], "asset_config": cfg,
            "quality_flags": row["quality_flags"], "reading_id": row["id"], "previous_state": None}
    schema = json.loads((Path(__file__).resolve().parents[1]/"schemas/normalized-input.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(args)
    before = deepcopy(args)
    assert compute_analytics(**args) == compute_analytics(**args) == process_stored_reading(row, cfg)
    assert args == before


def test_nonfinite_previous_state_is_an_explicit_input_error():
    state = process_stored_reading(record(), bound_config())["updated_state"]
    state["thermal"]["oil_temp_c"] = float("nan")
    with pytest.raises(ValueError):
        process_stored_reading(record(60), bound_config(), state)
