"""Transparent prototype calculations, not a protection or certified rating system."""
from dataclasses import dataclass, asdict
import math
from copy import deepcopy


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


@dataclass(frozen=True)
class AssetConfig:
    asset_id: str = "demo-transformer"
    rated_current_a: float = 50.0
    rated_phase_voltage_v: float = 260.0
    rated_oil_rise_c: float = 40.0
    loss_ratio: float = 5.0
    oil_exponent: float = 0.8
    time_constant_s: float = 10800.0
    initial_oil_temp_c: float = 55.0
    initial_ambient_temp_c: float = 30.0
    oil_warning_c: float = 85.0
    oil_critical_c: float = 100.0
    imbalance_warning_pct: float = 10.0
    overload_warning_pct: float = 100.0
    voltage_imbalance_warning_pct: float = 3.0
    residual_warning_c: float = 8.0
    residual_recovery_c: float = 4.0
    persistence_s: float = 180.0
    recovery_s: float = 180.0
    max_gap_s: float = 300.0

    def __post_init__(self):
        for key, value in asdict(self).items():
            if key != "asset_id" and not finite(value):
                raise ValueError(f"{key} must be finite")
        for key in ("rated_current_a", "rated_phase_voltage_v", "rated_oil_rise_c",
                    "loss_ratio", "oil_exponent", "time_constant_s", "imbalance_warning_pct",
                    "overload_warning_pct", "voltage_imbalance_warning_pct", "residual_warning_c", "persistence_s", "recovery_s", "max_gap_s"):
            if getattr(self, key) <= 0:
                raise ValueError(f"{key} must be positive")
        if not self.asset_id or self.oil_critical_c <= self.oil_warning_c:
            raise ValueError("Require asset_id and critical temperature > warning")
        if not 0 <= self.residual_recovery_c < self.residual_warning_c:
            raise ValueError("Require 0 <= residual recovery < warning")


@dataclass(frozen=True)
class ThermalState:
    predicted_oil_temp_c: float
    ambient_temp_c: float
    config: AssetConfig
    valid: bool = True
    reason: str | None = None

    def __post_init__(self):
        if not finite(self.predicted_oil_temp_c) or not finite(self.ambient_temp_c):
            raise ValueError("Thermal state temperatures must be finite")


def _phase_values(readings, key, maximum):
    values = readings.get(key)
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return None
    if not all(finite(v) and 0 <= v <= maximum for v in values):
        return None
    return list(values)


def _imbalance(values):
    mean = sum(values) / 3
    return 100 * max(abs(v - mean) for v in values) / mean if mean else 0.0


def calculate_electrical_metrics(readings, asset_config):
    """Voltage inputs are phase-to-neutral RMS, current inputs phase RMS [R,Y,B]."""
    currents = _phase_values(readings, "currents_a", asset_config.rated_current_a * 10)
    volts = _phase_values(readings, "voltages_v", asset_config.rated_phase_voltage_v * 2)
    return {
        "phase_loading_pct": [100 * i / asset_config.rated_current_a for i in currents] if currents else None,
        "max_loading_pct": 100 * max(currents) / asset_config.rated_current_a if currents else None,
        "thermal_load_pu": math.sqrt(sum((i / asset_config.rated_current_a) ** 2 for i in currents) / 3) if currents else None,
        "current_imbalance_pct": _imbalance(currents) if currents else None,
        "voltage_imbalance_pct": _imbalance(volts) if volts else None,
        "apparent_power_kva": sum(i * v for i, v in zip(currents, volts)) / 1000 if currents and volts else None,
        "config": asdict(asset_config),
    }


def _advance(state, load, ambient, duration, cooling=1.0):
    config = state.config
    if not finite(duration) or duration < 0:
        raise ValueError("elapsed_time must be finite and nonnegative")
    if not finite(load) or not 0 <= load <= 10 or not finite(ambient) or not -50 <= ambient <= 80:
        raise ValueError("Invalid load or ambient")
    if not finite(cooling) or not 0.2 <= cooling <= 2:
        raise ValueError("cooling_factor must be in [0.2, 2]")
    target = ambient + config.rated_oil_rise_c * ((1 + config.loss_ratio * load ** 2) / (1 + config.loss_ratio)) ** config.oil_exponent / cooling
    temperature = target + (state.predicted_oil_temp_c - target) * math.exp(-duration / (config.time_constant_s / cooling))
    return ThermalState(temperature, ambient, config)


def update_thermal_state(previous_state, readings, elapsed_time):
    """Advance expected healthy oil temperature; never assimilate measured oil temperature."""
    if not finite(elapsed_time) or elapsed_time < 0:
        raise ValueError("elapsed_time must be finite and nonnegative")
    if not previous_state.valid:
        return previous_state  # Replay or explicit reinitialization is required after unknown load history.
    metrics = calculate_electrical_metrics(readings, previous_state.config)
    ambient = readings.get("ambient_temp_c")
    if metrics["thermal_load_pu"] is None or not finite(ambient) or not -50 <= ambient <= 80:
        return ThermalState(previous_state.predicted_oil_temp_c, previous_state.ambient_temp_c,
                            previous_state.config, False, "missing_or_invalid_thermal_inputs")
    if elapsed_time > previous_state.config.max_gap_s:
        return ThermalState(previous_state.predicted_oil_temp_c, previous_state.ambient_temp_c,
                            previous_state.config, False, "unobserved_time_gap")
    return _advance(previous_state, metrics["thermal_load_pu"], ambient, elapsed_time)


def assess_condition(metrics, thermal_state, data_quality):
    """Health score is an explainable heuristic; confidence is a separate input coverage score."""
    config = thermal_state.config
    evidence = [
        ("loading", metrics.get("max_loading_pct"), 100.0, 150.0, 30.0, "%"),
        ("current_imbalance", metrics.get("current_imbalance_pct"), config.imbalance_warning_pct,
         config.imbalance_warning_pct * 3, 20.0, "%"),
        ("oil_temperature", data_quality.get("oil_temp_c"), config.oil_warning_c,
         config.oil_critical_c, 30.0, "C"),
        ("thermal_residual", data_quality.get("residual_c"), config.residual_recovery_c,
         config.residual_warning_c * 2, 20.0, "C"),
    ]
    contributors = []
    for name, value, lower, upper, weight, unit in evidence:
        penalty = weight * min(1.0, max(0.0, (value - lower) / (upper - lower))) if finite(value) else None
        contributors.append({"name": name, "value": value, "unit": unit, "penalty": penalty,
                             "weight": weight, "healthy_limit": lower, "full_penalty_at": upper})
    complete = all(c["penalty"] is not None for c in contributors)
    score = max(0.0, 100 - sum(c["penalty"] or 0 for c in contributors)) if complete else None
    confidence = data_quality.get("confidence", 0.0)
    status = "unknown" if score is None or confidence < 0.8 else "critical" if score < 50 else "warning" if score < 80 else "healthy"
    return {"health_index": score, "status": status, "contributors": contributors,
            "data_confidence": confidence, "confidence_reasons": data_quality.get("reasons", []),
            "method": "heuristic_v1", "remaining_useful_life": None}


def detect_anomalies(metrics, residuals, alert_history):
    """Pure state transition. History must be per asset. No scenario labels are read."""
    config = AssetConfig(**metrics["config"])
    duration = residuals.get("elapsed_s", 0)
    if not finite(duration) or duration < 0:
        raise ValueError("elapsed_s must be finite and nonnegative")
    history = deepcopy(alert_history or {})
    events = []
    checks = {
        "overload": (metrics.get("max_loading_pct"), config.overload_warning_pct, config.overload_warning_pct * 0.95, "%"),
        "current_imbalance": (metrics.get("current_imbalance_pct"), config.imbalance_warning_pct, config.imbalance_warning_pct * 0.8, "%"),
        "voltage_imbalance": (metrics.get("voltage_imbalance_pct"), config.voltage_imbalance_warning_pct, config.voltage_imbalance_warning_pct * 0.8, "%"),
        "high_oil_temperature": (residuals.get("oil_temp_c"), config.oil_warning_c, config.oil_warning_c - 5, "C"),
        "unexpected_heating": (residuals.get("residual_c"), config.residual_warning_c, config.residual_recovery_c, "C"),
        "data_unavailable": (residuals.get("data_unavailable"), 0.0, 0.01, "fraction"),
    }
    for kind, (value, trigger, recovery, unit) in checks.items():
        item = history.setdefault(kind, {"active": False, "pending_s": 0.0, "recovery_s": 0.0, "sequence": 0})
        usable = finite(value) and residuals.get("usable", True) and duration <= config.max_gap_s
        if not usable:
            item.update(pending_s=0.0, recovery_s=0.0, evidence_available=False,
                        previous_abnormal=False, previous_recoverable=False)
            continue  # Missing evidence never resolves an existing incident.
        item["evidence_available"] = True
        item["evidence"] = {"value": value, "unit": unit, "trigger": trigger, "recovery": recovery,
                            "timestamp": residuals.get("timestamp")}
        if item["active"] and kind == "high_oil_temperature" and value >= config.oil_critical_c:
            item["severity"] = "critical"
        if not item["active"]:
            abnormal = value > trigger
            item["pending_s"] = item["pending_s"] + duration if abnormal and item.get("previous_abnormal", False) else 0.0
            item["previous_abnormal"] = abnormal
            if item["pending_s"] >= config.persistence_s:
                item.update(active=True, pending_s=0.0, recovery_s=0.0, sequence=item["sequence"] + 1)
                item["incident_id"] = f"{config.asset_id}:{kind}:{item['sequence']}"
                transition = "opened"
            else:
                continue
        else:
            recoverable = value < recovery
            item["recovery_s"] = item["recovery_s"] + duration if recoverable and item.get("previous_recoverable", False) else 0.0
            item["previous_recoverable"] = recoverable
            if item["recovery_s"] >= config.recovery_s:
                item.update(active=False, recovery_s=0.0)
                transition = "resolved"
            else:
                continue
        severity = "critical" if kind == "high_oil_temperature" and value >= config.oil_critical_c else "warning"
        if transition == "opened":
            item["severity"] = severity
            item["previous_recoverable"] = False
        else:
            severity = item.get("severity", severity)
            item["previous_abnormal"] = False
        events.append({"incident_id": item["incident_id"], "asset_id": config.asset_id, "type": kind,
                       "severity": severity, "lifecycle": transition, "evidence": item["evidence"],
                       "persistence_required_s": config.persistence_s, "recovery_required_s": config.recovery_s})
    return {"events": events, "history": history,
            "active_alerts": [{"type": kind, **item} for kind, item in history.items() if item["active"]]}


def forecast_temperature(current_state, future_load_profile):
    """Piecewise-constant forecast: each row supplies duration_s, load_pu, ambient_temp_c."""
    if not current_state.valid:
        raise ValueError("Forecast requires a valid thermal state")
    if not future_load_profile:
        raise ValueError("Forecast requires at least one profile segment")
    state = current_state
    elapsed = 0.0
    points = [{"elapsed_s": 0.0, "oil_temp_c": state.predicted_oil_temp_c}]
    first_crossing = None
    for row in future_load_profile:
        duration = row["duration_s"]
        if not finite(duration) or duration <= 0 or duration > 86400:
            raise ValueError("Segment duration must be in (0, 86400] seconds")
        steps = math.ceil(duration / 60)
        dt = duration / steps
        for _ in range(steps):
            state = _advance(state, row["load_pu"], row["ambient_temp_c"], dt, row.get("cooling_factor", 1.0))
            elapsed += dt
            if first_crossing is None and state.predicted_oil_temp_c >= state.config.oil_warning_c:
                first_crossing = elapsed
            points.append({"elapsed_s": elapsed, "oil_temp_c": state.predicted_oil_temp_c})
    if current_state.predicted_oil_temp_c >= current_state.config.oil_warning_c:
        first_crossing = 0.0
    return {"source": "estimated", "points": points, "final_oil_temp_c": state.predicted_oil_temp_c,
            "peak_oil_temp_c": max(p["oil_temp_c"] for p in points), "warning_crossing_s": first_crossing,
            "assumptions": "Specified load, ambient and cooling remain constant within each segment; no probability interval calibrated."}


def compare_scenarios(current_state, scenarios):
    """First scenario is the baseline; all forecasts share the identical initial state and horizon."""
    if not scenarios or len({s["name"] for s in scenarios}) != len(scenarios):
        raise ValueError("Require nonempty scenarios with unique names")
    horizons = [sum(r["duration_s"] for r in s["profile"]) for s in scenarios]
    if not all(math.isclose(h, horizons[0]) for h in horizons):
        raise ValueError("Comparison scenarios must have equal horizons")
    results = []
    for scenario in scenarios:
        forecast = forecast_temperature(current_state, scenario["profile"])
        results.append({"name": scenario["name"], "inputs": deepcopy(scenario["profile"]), "forecast": forecast,
                        "explanation": "Load changes squared-current losses; ambient shifts equilibrium; cooling changes equilibrium and response time."})
    baseline = results[0]["forecast"]["final_oil_temp_c"]
    for result in results:
        result["final_delta_from_baseline_c"] = result["forecast"]["final_oil_temp_c"] - baseline
    return {"baseline": results[0]["name"], "initial_oil_temp_c": current_state.predicted_oil_temp_c,
            "horizon_s": horizons[0], "scenarios": results}
