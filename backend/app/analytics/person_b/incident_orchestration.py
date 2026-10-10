"""Pure detector-to-registry commands; A owns UUIDs, fencing and transactions."""
from copy import deepcopy
from uuid import UUID

from .persistence import evaluate_persistent_rules
from .validation import identity, mapping, strict_json
from .worker import MODEL_ID, RESULT_VERSION

CONTEXT_VERSION = "incident-detector-context-1.0.0"
COMMAND_VERSION = "incident-storage-commands-1.0.0"
SUPPORTED_MODELS = {"stored-reading-top-oil-1.0.1", "stored-reading-top-oil-1.0.2"}


class IncidentPlanningError(ValueError):
    """Stable machine code and bounded explanation; no raw payload is exposed."""
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _epoch(value):
    try:
        if not isinstance(value, str) or UUID(value).version != 4:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise IncidentPlanningError("incident_invalid_control", "detector_epoch must be a durable UUID4 string") from None


def _evaluate(analytics_result, policy, *, detector_epoch,
                                 result_id, previous_context=None,
                                 continuity_break=False):
    """Plan one immutable snapshot per affected episode for A's atomic commit.

    result_id is A's allocated durable result identity in the intended transaction,
    never an incident ID. No database access, canonical ID allocation or publication.
    continuity_break is A's persisted failed/skipped-sample barrier, consumed only
    on a forward result; it interrupts timers without recovering active incidents.
    """
    _epoch(detector_epoch)
    if type(result_id) is not int or result_id <= 0:
        raise IncidentPlanningError("incident_invalid_control", "result_id must be a positive durable result identity")
    if type(continuity_break) is not bool:
        raise IncidentPlanningError("incident_invalid_control", "continuity_break must be an explicit boolean")
    mapping(analytics_result, "Analytics result", ("metadata", "execution_status", "thermal_assessment", "data_confidence"))
    meta = mapping(analytics_result["metadata"], "Analytics metadata",
                   ("model_id", "model_version", "result_schema_version", "units", "reading_identity", "stream", "configuration_version", "parameter_version", "parameter_provenance", "measurement_time"))
    if meta["model_id"] != MODEL_ID or meta["model_version"] not in SUPPORTED_MODELS or meta["result_schema_version"] != RESULT_VERSION:
        raise IncidentPlanningError("incident_unsupported_contract", "Unsupported analytics model/result contract")
    identity(meta["reading_identity"])
    units = mapping(meta["units"], "Evidence units")
    if units.get("oil_temperature") != "C" or units.get("thermal_residual") != "C":
        raise IncidentPlanningError("incident_unsupported_contract", "Incident temperature evidence requires explicit C units")
    confidence = mapping(analytics_result["data_confidence"], "Data confidence", ("score", "status"))
    if confidence["score"] is not None or confidence["status"] != "not_estimated":
        raise IncidentPlanningError("incident_unsupported_contract", "Supported models do not provide calibrated numerical confidence")
    execution = mapping(analytics_result["execution_status"], "Execution status", ("outcome", "state_advanced"))
    if execution["outcome"] == "computation_error":
        raise IncidentPlanningError("incident_computation_rollback_required", "Computation errors require rollback/retry, not incident publication")
    prior = None
    if previous_context is not None:
        mapping(previous_context, "Detector context", ("schema_version", "detector_epoch", "detector_state"))
        strict_json(previous_context)
        if previous_context["schema_version"] != CONTEXT_VERSION or previous_context["detector_epoch"] != detector_epoch:
            raise IncidentPlanningError("incident_handover_required", "Detector epoch/context changed; explicit handover required")
        prior = deepcopy(previous_context["detector_state"])
    detector = evaluate_persistent_rules(analytics_result, policy, prior)
    # Validate the original state first; a barrier cannot repair corrupt state or
    # change historical/equal/late state. Recompute only an admitted forward sample.
    if continuity_break and detector["state_advanced"] and prior is not None:
        for item in mapping(prior["rules"], "Rule state").values():
            item.update(pending_s=0.0, recovery_s=0.0,
                        previous_abnormal=False, previous_recoverable=False)
        detector = evaluate_persistent_rules(analytics_result, policy, prior)
    if not detector["state_advanced"]:
        return {"schema_version": COMMAND_VERSION, "detector_result": detector,
                "updated_context": deepcopy(previous_context), "mutations": [],
                "continuity_break_consumed": False}
    commands = []
    events = {event["category"]: event for event in detector["events"]}
    active = {item["category"]: item for item in detector["active_incidents"]}
    observations = {item["rule"]: item for item in detector["evidence"]}
    for name in sorted(set(events) | set(active)):
        event = events.get(name)
        item = active.get(name)
        observation = observations[name]
        episode_key = event["incident_id"] if event else item["incident_id"]
        kind = ("recovered" if event["lifecycle"] == "resolved" else "opened") if event else (
            "updated" if observation["available"] else "evidence_unavailable")
        rule = next(rule for rule in policy["rules"] if rule["name"] == name)
        binding = detector["updated_state"]["binding"]
        versions = {key: deepcopy(meta[key]) for key in
                    ("model_id", "model_version", "result_schema_version", "parameter_version", "configuration_version")}
        versions.update({key: binding[key] for key in ("detector_version", "policy_version", "policy_fingerprint")})
        evidence = {**deepcopy(meta["reading_identity"]), "result_id": result_id,
                    "measurement_time": detector["measurement_time"], "observation_kind": kind,
                    "temperatures": {key: analytics_result["thermal_assessment"][key] for key in
                                     ("measured_top_oil_temperature_c", "predicted_top_oil_temperature_c", "thermal_residual_c")},
                    "temperature_unit": "C",
                    "rule_evidence": {**{key: deepcopy(observation[key]) for key in
                                         ("quantity", "value", "unit", "trigger", "recovery", "available", "reasons", "continuity")},
                                      "persistence_required_s": rule["persistence_s"], "recovery_required_s": rule["recovery_s"]},
                    "data_confidence": deepcopy(analytics_result["data_confidence"]),
                    "versions": versions, "parameter_provenance": deepcopy(meta["parameter_provenance"]),
                    "policy_provenance": policy["provenance"],
                    "quality_availability": deepcopy(execution["availability"])}
        if continuity_break:
            evidence["rule_evidence"]["continuity"] = "gap_reset"
        commands.append({"kind": kind, "mapping_key": {"asset_id": meta["stream"]["asset_id"],
                         "detector_epoch": detector_epoch, "detector_episode_key": episode_key},
                         "stream": deepcopy(meta["stream"]), "category": name,
                         "severity": rule["severity"], "evidence": evidence})
    output = {"schema_version": COMMAND_VERSION, "detector_result": detector,
              "updated_context": {"schema_version": CONTEXT_VERSION,
                                  "detector_epoch": detector_epoch,
                                  "detector_state": detector["updated_state"]},
              "mutations": commands, "continuity_break_consumed": continuity_break}
    strict_json(output)
    return output


def evaluate_incident_candidates(analytics_result, policy, *, detector_epoch,
                                 result_id, previous_context=None,
                                 continuity_break=False):
    """Pure planner. Raises IncidentPlanningError with a stable .code on rejection."""
    try:
        return _evaluate(analytics_result, policy, detector_epoch=detector_epoch,
                         result_id=result_id, previous_context=previous_context,
                         continuity_break=continuity_break)
    except IncidentPlanningError:
        raise
    except (ValueError, KeyError, TypeError, OverflowError, AttributeError):
        raise IncidentPlanningError("incident_invalid_input_or_state",
                                    "Invalid input/state or incompatible binding; validate before retry or handover") from None
