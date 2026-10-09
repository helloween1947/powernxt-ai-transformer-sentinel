"""Analytical scenario expectations; no independent measured validation."""
from copy import deepcopy
import json
import math
from pathlib import Path

import pytest

from analytics import process_stored_reading, forecast_from_worker_state, compare_worker_scenarios
from analytics.tests.test_worker import bound_config, record


def initial():
    cfg = bound_config()
    return cfg, process_stored_reading(record(), cfg)["updated_state"]


def profile(k=1, ambient=30, duration=3600):
    return [{"duration_s": duration, "thermal_load_pu": k, "ambient_temp_c": ambient}]


def test_closed_form_forecast_and_input_immutability():
    cfg, state = initial()
    args = deepcopy((state, cfg, profile()))
    result = forecast_from_worker_state(state, cfg, profile())
    assert result["final_top_oil_temperature_c"] == pytest.approx(70-15*math.exp(-3600/10800))
    assert (state, cfg, profile()) == args
    assert forecast_from_worker_state(state, cfg, profile()) == result
    json.dumps(result, allow_nan=False)


def test_partition_invariance_and_peak_including_initial():
    cfg, state = initial()
    p = profile(duration=137)+profile(duration=59)+profile(duration=3404)
    assert forecast_from_worker_state(state, cfg, p)["final_top_oil_temperature_c"] == pytest.approx(forecast_from_worker_state(state, cfg, profile())["final_top_oil_temperature_c"])
    cooling = forecast_from_worker_state(state, cfg, profile(k=0))
    assert cooling["peak_top_oil_temperature_c"] == 55
    assert cooling["final_top_oil_temperature_c"] < 55


def test_exact_crossing_and_missing_threshold():
    cfg, state = initial()
    cfg["operational_limits"]["max_top_oil_temp_c"] = 60
    state = process_stored_reading(record(), cfg)["updated_state"]
    result = forecast_from_worker_state(state, cfg, profile(duration=7200))
    assert result["first_limit_crossing_s"] == pytest.approx(10800*math.log(1.5))
    cfg["operational_limits"]["max_top_oil_temp_c"] = None
    del cfg["parameter_provenance"]["operational_limits.max_top_oil_temp_c"]
    state = process_stored_reading(record(), cfg)["updated_state"]
    result = forecast_from_worker_state(state, cfg, profile())
    assert result["first_limit_crossing_s"] is None
    assert result["limit_check_status"] == "unavailable_configured_limit_missing"


def test_initial_breach_and_asymptotic_limit():
    cfg, _ = initial()
    cfg["operational_limits"]["max_top_oil_temp_c"] = 55
    state = process_stored_reading(record(), cfg)["updated_state"]
    assert forecast_from_worker_state(state, cfg, profile())["first_limit_crossing_s"] == 0
    cfg["operational_limits"]["max_top_oil_temp_c"] = 70
    cfg["thermal_parameters"]["oil_time_constant_min"] = 0.001
    state = process_stored_reading(record(), cfg)["updated_state"]
    assert forecast_from_worker_state(state, cfg, profile())["first_limit_crossing_s"] is None


def test_scenarios_have_explainable_load_and_ambient_differences():
    cfg, state = initial()
    scenarios = [{"name": "baseline", "profile": profile()}, {"name": "reduce_load", "profile": profile(k=0.5)},
                 {"name": "hotter_ambient", "profile": profile(ambient=40)}]
    output = compare_worker_scenarios(state, cfg, scenarios)
    assert output["scenarios"][0]["final_delta_from_baseline_c"] == 0
    assert output["scenarios"][1]["final_delta_from_baseline_c"] < 0
    assert output["scenarios"][2]["final_delta_from_baseline_c"] > 0
    assert all(item["forecast"]["initial_top_oil_temperature_c"] == 55 for item in output["scenarios"])


@pytest.mark.parametrize("case", ["gap", "uninitialized", "schema", "model", "config", "coefficients"])
def test_unusable_or_incompatible_state_rejected(case):
    cfg, state = initial()
    if case == "gap":
        state["thermal"]["valid"] = False
    elif case == "uninitialized":
        state["thermal"]["initialized"] = False
    elif case == "schema":
        state["schema_version"] = "other"
    elif case == "model":
        state["binding"]["model_version"] = "other"
    elif case == "coefficients":
        cfg = bound_config(thermal=False)
        state = process_stored_reading(record(), cfg)["updated_state"]
    else:
        cfg["thermal_parameters"]["loss_ratio"] = 6
    with pytest.raises(ValueError):
        forecast_from_worker_state(state, cfg, profile())


@pytest.mark.parametrize("key,value", [("duration_s", 0), ("duration_s", 86401), ("duration_s", float("inf")), ("thermal_load_pu", -1), ("thermal_load_pu", True), ("ambient_temp_c", 100), ("cooling_factor", 2)])
def test_explicit_profiles_reject_invalid_and_unmodeled_inputs(key, value):
    cfg, state = initial()
    p = profile()
    p[0][key] = value
    with pytest.raises(ValueError):
        forecast_from_worker_state(state, cfg, p)


@pytest.mark.parametrize("case", ["empty", "names", "horizon"])
def test_invalid_comparisons_rejected(case):
    cfg, state = initial()
    scenarios = [] if case == "empty" else [{"name": "one", "profile": profile()}, {"name": "one" if case == "names" else "two", "profile": profile(duration=1)}]
    with pytest.raises(ValueError):
        compare_worker_scenarios(state, cfg, scenarios)


def test_executed_scenario_fixture_reproduces_exactly():
    path = Path(__file__).resolve().parents[1]/"examples/worker-scenarios-test-example.json"
    fixture = json.loads(path.read_text())
    assert compare_worker_scenarios(**fixture["input"]) == fixture["output"]
