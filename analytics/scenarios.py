"""Explicit load/ambient what-if forecasts from the healthy worker state.

These are conditional estimates, not fault-aware action recommendations.
"""
from copy import deepcopy
import math
import json

from .transformer_twin import AssetConfig, ThermalState
from .transformer_twin.model import _advance, finite
from .worker import MODEL_VERSION, STATE_VERSION, _parameter_version, _validate_config

FORECAST_VERSION = "healthy-top-oil-scenarios-1.0.0"


def forecast_from_worker_state(current_state: dict, asset_config: dict,
                               future_load_profile: list[dict]) -> dict:
    """Forecast supplied piecewise-constant K/ambient, never changing live state.

    Every segment requires duration_s, thermal_load_pu and ambient_temp_c.
    No measured oil reinitialization or uncalibrated cooling factor is introduced.
    """
    if current_state.get("schema_version") != STATE_VERSION:
        raise ValueError("Unsupported worker state schema")
    binding = current_state["binding"]
    missing = _validate_config({"asset_id": binding["stream"]["asset_id"], "configuration_version": binding["configuration_version"]}, asset_config)
    if binding["model_version"] != MODEL_VERSION or binding["parameter_version"] != _parameter_version(asset_config):
        raise ValueError("Forecast requires matching model and immutable configuration")
    thermal = current_state["thermal"]
    if missing or not thermal["initialized"] or not thermal["valid"] or not finite(thermal["oil_temp_c"]):
        raise ValueError("Forecast requires explicit parameters and valid initialized thermal state")
    if not isinstance(future_load_profile, list) or not 1 <= len(future_load_profile) <= 96:
        raise ValueError("Require one to 96 explicit profile segments")
    horizon = 0.0
    for row in future_load_profile:
        if set(row) != {"duration_s", "thermal_load_pu", "ambient_temp_c"}:
            raise ValueError("Segments require duration_s, thermal_load_pu and ambient_temp_c only")
        if not all(finite(row[k]) for k in row) or row["duration_s"] <= 0 or not 0 <= row["thermal_load_pu"] <= 10 or not -50 <= row["ambient_temp_c"] <= 80:
            raise ValueError("Invalid duration, load or ambient")
        horizon += row["duration_s"]
    if not finite(horizon) or horizon > 86400:
        raise ValueError("Maximum forecast horizon is 24 hours")
    params = asset_config["thermal_parameters"]
    tau = params["oil_time_constant_min"]*60
    core = AssetConfig(asset_id=asset_config["asset_id"], rated_current_a=asset_config["rated_current_a"],
                       rated_phase_voltage_v=asset_config["rated_voltage_v"]/(math.sqrt(3) if asset_config["voltage_convention"] == "line_to_line" else 1),
                       rated_oil_rise_c=params["rated_top_oil_rise_c"], time_constant_s=tau,
                       loss_ratio=params["loss_ratio"], oil_exponent=params["oil_exponent"])
    temperature, elapsed = thermal["oil_temp_c"], 0.0
    points = [{"elapsed_s": elapsed, "predicted_top_oil_temperature_c": temperature}]
    limit = asset_config.get("operational_limits", {}).get("max_top_oil_temp_c")
    crossing = 0.0 if limit is not None and temperature >= limit else None
    try:
        for row in future_load_profile:
            duration, k, ambient = row["duration_s"], row["thermal_load_pu"], row["ambient_temp_c"]
            target = ambient+core.rated_oil_rise_c*((1+core.loss_ratio*k*k)/(1+core.loss_ratio))**core.oil_exponent
            end = _advance(ThermalState(temperature, ambient, core), k, ambient, duration).predicted_oil_temp_c
            if not finite(end) or not finite(target):
                raise ValueError("Non-finite forecast")
            if crossing is None and limit is not None and temperature < limit <= end and target > limit:
                crossing = elapsed-tau*math.log((target-limit)/(target-temperature))
            temperature, elapsed = end, elapsed+duration
            points.append({"elapsed_s": elapsed, "predicted_top_oil_temperature_c": temperature})
    except (OverflowError, ZeroDivisionError, ValueError):
        raise ValueError("Forecast arithmetic unavailable for supplied parameters") from None
    result = {"forecast_version": FORECAST_VERSION, "model_version": MODEL_VERSION,
              "source": "estimated", "initial_condition_source": "healthy_worker_prediction_or_observed_bootstrap",
              "state_reference": deepcopy(binding), "initial_measurement_time": current_state["last_measurement_time"],
              "initial_top_oil_temperature_c": thermal["oil_temp_c"], "horizon_s": horizon,
              "profile": deepcopy(future_load_profile), "points": points,
              "final_top_oil_temperature_c": temperature,
              "peak_top_oil_temperature_c": max(p["predicted_top_oil_temperature_c"] for p in points),
              "configured_top_oil_limit_c": limit, "first_limit_crossing_s": crossing,
              "limit_check_status": "available" if limit is not None else "unavailable_configured_limit_missing",
              "units": {"temperature": "C", "time": "s", "thermal_load": "pu"},
              "assumptions": ["Explicit future K/ambient held constant within each segment.",
                              "Same simplified healthy thermal parameters and initial state for all scenarios.",
                              "No fault continuation, cooling intervention, measured-oil assimilation or uncertainty calibration."]}
    json.dumps(result, allow_nan=False)
    return result


def compare_worker_scenarios(current_state: dict, asset_config: dict,
                             scenarios: list[dict]) -> dict:
    """Compare equal-horizon forecasts; first scenario is the named baseline."""
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 12:
        raise ValueError("Require one to 12 scenarios")
    names, results = set(), []
    for item in scenarios:
        if set(item) != {"name", "profile"} or not isinstance(item["name"], str) or not item["name"] or item["name"] in names:
            raise ValueError("Scenarios need unique names and explicit profiles only")
        names.add(item["name"])
        forecast = forecast_from_worker_state(current_state, asset_config, item["profile"])
        if results and not math.isclose(forecast["horizon_s"], results[0]["forecast"]["horizon_s"], rel_tol=0, abs_tol=1e-9):
            raise ValueError("Scenario horizons must agree")
        results.append({"name": item["name"], "forecast": forecast,
                        "explanation": "Load changes squared-current loss; ambient shifts the equilibrium. Inputs are conditional assumptions."})
    baseline = results[0]["forecast"]["final_top_oil_temperature_c"]
    for item in results:
        item["final_delta_from_baseline_c"] = item["forecast"]["final_top_oil_temperature_c"]-baseline
    return {"forecast_version": FORECAST_VERSION, "baseline": results[0]["name"],
            "horizon_s": results[0]["forecast"]["horizon_s"], "scenarios": results,
            "interpretation": "Healthy expected-temperature comparison, not an action recommendation or unresolved-fault forecast."}
