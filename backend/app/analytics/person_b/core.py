"""Exact extracted physical primitives; no legacy orchestration or heuristics."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import math

def finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False

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
        if type(self.valid) is not bool or (self.reason is not None and not isinstance(self.reason, str)):
            raise ValueError("Thermal validity must be boolean and reason null or a string")

def _advance(state, load, ambient, duration, cooling=1.0):
    config = state.config
    if not finite(duration) or duration < 0:
        raise ValueError("elapsed_time must be finite and nonnegative")
    if not finite(load) or not 0 <= load <= 10 or not finite(ambient) or not -50 <= ambient <= 80:
        raise ValueError("Invalid load or ambient")
    if not finite(cooling) or not 0.2 <= cooling <= 2:
        raise ValueError("cooling_factor must be in [0.2, 2]")
    if duration == 0:
        return ThermalState(state.predicted_oil_temp_c, ambient, config)
    target = ambient + config.rated_oil_rise_c * ((1 + config.loss_ratio * load ** 2) / (1 + config.loss_ratio)) ** config.oil_exponent / cooling
    temperature = target + (state.predicted_oil_temp_c - target) * math.exp(-duration / (config.time_constant_s / cooling))
    return ThermalState(temperature, ambient, config)

def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string with timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        raise ValueError("timestamp cannot be represented in UTC") from None
