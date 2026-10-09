"""Pure, optional sustained-threshold detector for versioned worker evidence.

No thresholds are inferred, no state is persisted, and no events are published.
"""
from copy import deepcopy
import hashlib
import json

from .core import _timestamp, finite
from .validation import mapping, strict_json, identity as validate_identity

DETECTOR_VERSION = "sustained-threshold-1.0.1"
STATE_VERSION = "sustained-threshold-state-1.0.0"
QUANTITIES = {
    "electrical_metrics.capacity_loading_pct": "%",
    "electrical_metrics.max_phase_loading_pct": "%",
    "electrical_metrics.current_magnitude_imbalance_pct": "%",
    "electrical_metrics.voltage_magnitude_imbalance_pct": "%",
    "thermal_assessment.thermal_residual_c": "C",
    "thermal_assessment.measured_top_oil_temperature_c": "C",
}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _policy(policy):
    mapping(policy, "Detector policy")
    if set(policy) != {"version", "provenance", "max_gap_s", "rules"}:
        raise ValueError("Policy requires version, provenance, max_gap_s and rules only")
    if not isinstance(policy["version"], str) or not policy["version"] or policy["provenance"] not in ("assumed", "measured", "team_agreed"):
        raise ValueError("Explicit policy version and provenance required")
    if not finite(policy["max_gap_s"]) or policy["max_gap_s"] <= 0:
        raise ValueError("Positive finite max_gap_s required")
    if not isinstance(policy["rules"], list) or not policy["rules"] or len(policy["rules"]) > len(QUANTITIES):
        raise ValueError("Require one to six named rules")
    names = set()
    for rule in policy["rules"]:
        mapping(rule, "Detector rule")
        if set(rule) != {"name", "quantity", "unit", "trigger", "recovery", "persistence_s", "recovery_s", "severity"}:
            raise ValueError("Unexpected or missing rule fields")
        if not isinstance(rule["name"], str) or not rule["name"] or rule["name"] in names:
            raise ValueError("Nonempty unique rule names required")
        names.add(rule["name"])
        if rule["quantity"] not in QUANTITIES or rule["unit"] != QUANTITIES[rule["quantity"]]:
            raise ValueError("Unsupported quantity or unit")
        if rule["severity"] not in ("info", "warning", "critical"):
            raise ValueError("Explicit valid severity required")
        if not all(finite(rule[k]) for k in ("trigger", "recovery", "persistence_s", "recovery_s")):
            raise ValueError("Rule parameters must be finite numbers")
        if rule["recovery"] >= rule["trigger"] or min(rule["persistence_s"], rule["recovery_s"]) <= 0:
            raise ValueError("Require recovery < trigger and positive durations")


def evaluate_persistent_rules(analytics_result: dict, policy: dict,
                              previous_state: dict | None = None) -> dict:
    """Return candidate lifecycle transitions and serializable detector state.

    Strict > trigger opens; strict < recovery resolves. Credit elapsed time only
    between consecutive qualifying samples. A/D own orchestration and publication.
    """
    _policy(policy)
    mapping(analytics_result, "Analytics result", ("metadata", "execution_status"))
    execution = mapping(analytics_result["execution_status"], "Execution status", ("state_advanced", "outcome"))
    if type(execution["state_advanced"]) is not bool:
        raise ValueError("State advancement must be an explicit boolean")
    meta = analytics_result["metadata"]
    stamp = _timestamp(meta["measurement_time"]).isoformat().replace("+00:00", "Z")
    binding = {k: deepcopy(meta[k]) for k in
               ("stream", "configuration_version", "model_id", "model_version", "parameter_version")}
    binding.update(detector_version=DETECTOR_VERSION, policy_version=policy["version"], policy_fingerprint=_digest(policy))
    # Ignore arbitrary raw metadata / labels. Only whitelisted result values enter rules.
    identity = deepcopy(meta["reading_identity"])
    validate_identity(identity)
    elapsed = None
    if previous_state is not None:
        mapping(previous_state, "Detector state", ("schema_version", "binding", "last_measurement_time", "last_reading_identity", "rules"))
        strict_json(previous_state)
        if previous_state.get("schema_version") != STATE_VERSION or previous_state.get("binding") != binding:
            raise ValueError("Detector binding changed; select matching state or deliberately reset/replay")
        validate_identity(previous_state["last_reading_identity"])
        history = mapping(previous_state["rules"], "Detector rule history")
        if set(history) != {rule["name"] for rule in policy["rules"]}:
            raise ValueError("Detector history must match the policy rules")
        for name, item in history.items():
            mapping(item, "Detector rule state", ("active", "sequence", "incident_id", "pending_s", "recovery_s", "previous_abnormal", "previous_recoverable", "last_usable_evidence"))
            if any(type(item[key]) is not bool for key in ("active", "previous_abnormal", "previous_recoverable")):
                raise ValueError("Detector state flags must be booleans")
            if type(item["sequence"]) is not int or item["sequence"] < 0:
                raise ValueError("Detector sequence must be a nonnegative integer")
            if any(not finite(item[key]) or item[key] < 0 for key in ("pending_s", "recovery_s")):
                raise ValueError("Detector durations must be finite and nonnegative")
            expected = f"{_digest(binding)}:{name}:{item['sequence']}" if item["sequence"] else None
            if item["incident_id"] != expected or (item["active"] and not item["sequence"]):
                raise ValueError("Detector episode key is inconsistent with its state")
        elapsed = (_timestamp(stamp)-_timestamp(previous_state["last_measurement_time"])).total_seconds()
        prior = previous_state["last_reading_identity"]
        if (identity["reading_id"] == prior["reading_id"] or identity["message_id"] == prior["message_id"]) and elapsed != 0:
            raise ValueError("Reading identity reused at another measurement time")
    reasons = []
    if not analytics_result["execution_status"]["state_advanced"]:
        reasons.append("analytics_forward_state_not_advanced")
    if analytics_result["execution_status"]["outcome"] == "computation_error":
        reasons.append("analytics_computation_error")
    if elapsed is not None and elapsed <= 0:
        reasons.append("equal_or_out_of_order_measurement_time")
    state = deepcopy(previous_state)
    events, evidence = [], []
    if not reasons:
        history = deepcopy(previous_state["rules"]) if previous_state else {}
        gap = elapsed is not None and elapsed > policy["max_gap_s"]
        dt = elapsed if elapsed is not None and not gap else 0.0
        for rule in policy["rules"]:
            name, quantity = rule["name"], rule["quantity"]
            section, field = quantity.split(".")
            value = analytics_result[section][field]
            availability = analytics_result["execution_status"]["availability"].get(quantity)
            if quantity == "thermal_assessment.measured_top_oil_temperature_c":
                usable = analytics_result["data_confidence"]["channels"]["oil_temperature_c"]["usable"]
            else:
                usable = availability is not None and availability["status"] == "available"
            usable = usable and finite(value)
            item = history.setdefault(name, {"active": False, "sequence": 0, "incident_id": None,
                                             "pending_s": 0.0, "recovery_s": 0.0,
                                             "previous_abnormal": False, "previous_recoverable": False,
                                             "last_usable_evidence": None})
            if gap or not usable:
                item.update(pending_s=0.0, recovery_s=0.0, previous_abnormal=False, previous_recoverable=False)
            observation = {"rule": name, "quantity": quantity, "value": value if usable else None,
                           "unit": rule["unit"], "trigger": rule["trigger"], "recovery": rule["recovery"],
                           "measurement_time": stamp, "reading_identity": identity,
                           "available": usable, "reasons": [] if usable else ["usable_rule_evidence_unavailable"],
                           "continuity": "gap_reset" if gap else "sampled_endpoints",
                           "assumption": "Qualifying endpoints approximate continuous evidence between samples."}
            evidence.append(observation)
            if not usable:
                continue  # Never resolve active incidents on missing evidence.
            item["last_usable_evidence"] = deepcopy(observation)
            transition = None
            if not item["active"]:
                abnormal = value > rule["trigger"]
                item["pending_s"] = item["pending_s"]+dt if abnormal and item["previous_abnormal"] else 0.0
                item["previous_abnormal"] = abnormal
                if item["pending_s"] >= rule["persistence_s"]:
                    item.update(active=True, sequence=item["sequence"]+1, pending_s=0.0, recovery_s=0.0, previous_recoverable=False)
                    item["incident_id"] = f"{_digest(binding)}:{name}:{item['sequence']}"
                    transition = "opened"
            else:
                recoverable = value < rule["recovery"]
                item["recovery_s"] = item["recovery_s"]+dt if recoverable and item["previous_recoverable"] else 0.0
                item["previous_recoverable"] = recoverable
                if item["recovery_s"] >= rule["recovery_s"]:
                    item.update(active=False, recovery_s=0.0, previous_abnormal=False)
                    transition = "resolved"
            if transition:
                events.append({"incident_id": item["incident_id"], "category": name, "severity": rule["severity"],
                               "lifecycle": transition, "evidence": deepcopy(observation),
                               "persistence_required_s": rule["persistence_s"], "recovery_required_s": rule["recovery_s"]})
        state = {"schema_version": STATE_VERSION, "binding": binding, "last_measurement_time": stamp,
                 "last_reading_identity": identity, "rules": history}
    output = {"detector_version": DETECTOR_VERSION, "policy_version": policy["version"],
              "policy_provenance": policy["provenance"], "state_advanced": not reasons, "reasons": reasons,
              "measurement_time": stamp, "events": events, "evidence": evidence, "updated_state": state,
              "active_incidents": [{"category": name, **deepcopy(item)} for name, item in (state["rules"] if state else {}).items() if item["active"]]}
    json.dumps(output, allow_nan=False)
    return output
