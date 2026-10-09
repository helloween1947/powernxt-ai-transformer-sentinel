"""Sequential per-asset orchestration; A persists snapshot() alongside accepted readings."""
from dataclasses import asdict
from datetime import datetime, timezone
from copy import deepcopy
import json

from .model import (AssetConfig, ThermalState, finite, calculate_electrical_metrics,
                    update_thermal_state, assess_condition, detect_anomalies)


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


class TwinEngine:
    def __init__(self, config=None):
        self.config = config or AssetConfig()
        self.state = ThermalState(self.config.initial_oil_temp_c, self.config.initial_ambient_temp_c, self.config)
        self.last_timestamp = None
        self.alert_history = {}

    def initialize_temperature(self, oil_temp_c, ambient_temp_c):
        """Explicit trusted initial condition; also resets continuity timers, preserving incidents."""
        if not finite(oil_temp_c) or not -50 <= oil_temp_c <= 200:
            raise ValueError("Invalid initial oil temperature")
        if not finite(ambient_temp_c) or not -50 <= ambient_temp_c <= 80:
            raise ValueError("Invalid initial ambient temperature")
        self.state = ThermalState(oil_temp_c, ambient_temp_c, self.config)
        self.last_timestamp = None
        for item in self.alert_history.values():
            item.update(pending_s=0.0, recovery_s=0.0, previous_abnormal=False, previous_recoverable=False)

    def snapshot(self):
        return {"schema_version": "1.0", "config": asdict(self.config),
                "thermal_state": {k: v for k, v in asdict(self.state).items() if k != "config"},
                "last_timestamp": self.last_timestamp, "alert_history": deepcopy(self.alert_history)}

    @classmethod
    def restore(cls, snapshot):
        if not isinstance(snapshot, dict) or not {"schema_version", "config", "thermal_state", "last_timestamp", "alert_history"}.issubset(snapshot):
            raise ValueError("Engine snapshot requires its complete state maps")
        try:
            json.dumps(snapshot, allow_nan=False)
        except (ValueError, TypeError, OverflowError):
            raise ValueError("Engine snapshot must be finite JSON") from None
        if any(not isinstance(snapshot[key], dict) for key in ("config", "thermal_state", "alert_history")):
            raise ValueError("Engine snapshot state fields must be maps")
        for item in snapshot["alert_history"].values():
            if not isinstance(item, dict) or not {"active", "pending_s", "recovery_s", "sequence"}.issubset(item):
                raise ValueError("Incomplete restored alert state")
            if type(item["active"]) is not bool or type(item["sequence"]) is not int or item["sequence"] < 0:
                raise ValueError("Invalid restored alert flags or sequence")
            if any(not finite(item[key]) or item[key] < 0 for key in ("pending_s", "recovery_s")):
                raise ValueError("Invalid restored alert duration")
            for key in ("previous_abnormal", "previous_recoverable", "evidence_available"):
                if key in item and type(item[key]) is not bool:
                    raise ValueError("Invalid restored alert continuity flag")
        if snapshot["schema_version"] != "1.0":
            raise ValueError("Unsupported state version")
        engine = cls(AssetConfig(**snapshot["config"]))
        engine.state = ThermalState(config=engine.config, **snapshot["thermal_state"])
        engine.last_timestamp = snapshot["last_timestamp"]
        if engine.last_timestamp is not None:
            _timestamp(engine.last_timestamp)
        engine.alert_history = deepcopy(snapshot["alert_history"])
        return engine

    def process(self, reading, *, now=None):
        source = reading.get("source", "measured")
        if source not in ("measured", "simulated"):
            raise ValueError("source must be measured or simulated")
        if reading.get("asset_id") != self.config.asset_id:
            raise ValueError("Reading asset_id does not match this engine")
        timestamp = _timestamp(reading["timestamp"])
        current_time = _timestamp(now) if now is not None else timestamp
        age = (current_time - timestamp).total_seconds()
        reasons = []
        accepted = True
        if age < 0 or age > self.config.max_gap_s:
            reasons.append("future_timestamp" if age < 0 else "stale_reading")
            accepted = False
        elapsed = 0.0
        if self.last_timestamp:
            elapsed = (timestamp - _timestamp(self.last_timestamp)).total_seconds()
            if elapsed <= 0:
                accepted = False
                reasons.append("duplicate_or_out_of_order")
        clean = {k: reading.get(k) for k in ("currents_a", "voltages_v", "oil_temp_c", "ambient_temp_c")}
        flags = reading.get("quality", {})
        if not isinstance(flags, dict):
            raise ValueError("quality must be a map of field -> good/missing/invalid/stale")
        for field, flag in flags.items():
            if flag not in ("good", "missing", "invalid", "stale"):
                raise ValueError(f"Unsupported quality flag: {flag}")
            if field in clean and flag != "good":
                clean[field] = None
                reasons.append(f"{field}:{flag}")
        for field, lower, upper in (("oil_temp_c", -50, 200), ("ambient_temp_c", -50, 80)):
            if not finite(clean[field]) or not lower <= clean[field] <= upper:
                clean[field] = None
                reasons.append(f"{field}:missing_or_invalid")
        metrics = calculate_electrical_metrics(clean, self.config)
        if metrics["phase_loading_pct"] is None:
            reasons.append("currents_a:missing_or_invalid")
        if metrics["voltage_imbalance_pct"] is None:
            reasons.append("voltages_v:missing_or_invalid")
        coverage = sum((metrics["phase_loading_pct"] is not None, metrics["voltage_imbalance_pct"] is not None,
                        clean["oil_temp_c"] is not None, clean["ambient_temp_c"] is not None)) / 4
        if accepted:
            self.state = update_thermal_state(self.state, clean, elapsed)
            self.last_timestamp = timestamp.isoformat()
        if not self.state.valid:
            reasons.append(self.state.reason)
        confidence = coverage if accepted and self.state.valid else 0.0
        residual = clean["oil_temp_c"] - self.state.predicted_oil_temp_c if accepted and self.state.valid and clean["oil_temp_c"] is not None else None
        quality = {"confidence": confidence, "reasons": sorted(set(reasons)),
                   "oil_temp_c": clean["oil_temp_c"] if accepted else None, "residual_c": residual}
        if accepted:
            alerts = detect_anomalies(metrics, {**quality, "elapsed_s": elapsed, "timestamp": timestamp.isoformat(),
                                               "data_unavailable": 1 - coverage,
                                               "usable": True}, self.alert_history)
            self.alert_history = alerts["history"]
        else:
            alerts = {"events": [], "history": deepcopy(self.alert_history),
                      "active_alerts": [{"type": k, **v} for k, v in self.alert_history.items() if v["active"]]}
        return {"schema_version": "1.0", "asset_id": self.config.asset_id,
                "timestamp": timestamp.isoformat(), "accepted": accepted, "source": source,
                "electrical": metrics,
                "thermal": {"source": "estimated", "valid": self.state.valid,
                            "predicted_oil_temp_c": self.state.predicted_oil_temp_c if self.state.valid else None,
                            "measured_oil_temp_c": clean["oil_temp_c"], "residual_c": residual,
                            "forecast_initial_oil_temp_c": clean["oil_temp_c"] if accepted and self.state.valid else None,
                            "initialization": "configured_or_explicit_trusted_initial_condition"},
                "condition": assess_condition(metrics, self.state, quality),
                "data_quality": {"confidence": confidence, "coverage": coverage, "age_s": age, "reasons": quality["reasons"]},
                "alerts": alerts}
