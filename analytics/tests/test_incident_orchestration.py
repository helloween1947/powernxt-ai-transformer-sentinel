"""Pure storage plans, not assertions of implemented registry/atomic persistence."""
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from analytics import evaluate_incident_candidates
from analytics.tests.test_persistence import frame, policy

EPOCH = "50000000-0000-4000-8000-000000000001"


def run(time, previous=None, *, load=1.5, missing=False, continuity_break=False):
    return evaluate_incident_candidates(frame(time, load, missing), policy(),
        detector_epoch=EPOCH, result_id=time+1001, previous_context=previous,
        continuity_break=continuity_break)


def opened():
    return run(180, run(0)["updated_context"])


def test_open_update_unavailable_and_recovery_share_mapping_not_result_id():
    initial = run(0)
    assert initial["mutations"] == []
    opening = run(180, initial["updated_context"])
    commands = [opening["mutations"][0]]
    context = opening["updated_context"]
    for time, load, missing in ((240, .5, False), (300, .5, True), (360, .5, False), (480, .5, False)):
        output = run(time, context, load=load, missing=missing)
        commands.extend(output["mutations"])
        context = output["updated_context"]
    assert [c["kind"] for c in commands] == ["opened", "updated", "evidence_unavailable", "updated", "recovered"]
    assert all(c["mapping_key"] == commands[0]["mapping_key"] for c in commands)
    assert len({c["evidence"]["result_id"] for c in commands}) == 5
    assert all("incident_id" not in c for c in commands)
    missing = commands[2]["evidence"]["rule_evidence"]
    assert missing["value"] is None and missing["available"] is False
    assert commands[2]["evidence"]["measurement_time"].endswith("00:05:00Z")
    reopened = run(540, context)
    reopened = run(720, reopened["updated_context"])
    assert reopened["mutations"][0]["mapping_key"] != commands[0]["mapping_key"]


def test_commands_evidence_matches_merged_contract_definition():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root/"contracts/incident-proposal.schema.json").read_text())
    validator = Draft202012Validator({"$ref": "#/$defs/evidence", "$defs": schema["$defs"]}, format_checker=FormatChecker())
    for output in (opened(), run(240, opened()["updated_context"], missing=True)):
        for command in output["mutations"]:
            validator.validate(command["evidence"])
        json.dumps(output, allow_nan=False)


def test_retry_is_deterministic_without_mutating_input_and_poststate_is_noop():
    before = run(0)["updated_context"]
    saved = deepcopy(before)
    reading = frame(180)
    args = {"detector_epoch": EPOCH, "result_id": 1181, "previous_context": before}
    first = evaluate_incident_candidates(reading, policy(), **args)
    assert evaluate_incident_candidates(reading, policy(), **args) == first and before == saved
    retry = run(180, first["updated_context"])
    assert retry["mutations"] == []
    assert retry["updated_context"] == first["updated_context"]


@pytest.mark.parametrize("time", [0, 60, 180])
def test_nonforward_sample_cannot_consume_barrier_or_change_context(time):
    context = opened()["updated_context"]
    result = run(time, context, continuity_break=True)
    assert result["mutations"] == []
    assert result["updated_context"] == context
    assert result["detector_result"]["updated_state"] == context["detector_state"]
    assert result["continuity_break_consumed"] is False


def test_recorded_failure_barrier_interrupts_pending_time():
    state = run(120, run(0)["updated_context"])["updated_context"]
    result = run(180, state, continuity_break=True)
    assert result["mutations"] == []
    assert result["updated_context"]["detector_state"]["rules"]["capacity_overload"]["pending_s"] == 0
    assert result["continuity_break_consumed"] is True
    assert run(360, result["updated_context"])["mutations"][0]["kind"] == "opened"


def test_barrier_preserves_active_mapping_and_interrupts_recovery():
    first = opened()
    recovering = run(240, first["updated_context"], load=.5)
    interrupted = run(360, recovering["updated_context"], load=.5, continuity_break=True)
    assert interrupted["mutations"][0]["kind"] == "updated"
    assert interrupted["mutations"][0]["mapping_key"] == first["mutations"][0]["mapping_key"]
    assert interrupted["mutations"][0]["evidence"]["rule_evidence"]["continuity"] == "gap_reset"
    assert run(480, interrupted["updated_context"], load=.5)["mutations"][0]["kind"] == "recovered"


@pytest.mark.parametrize("field,value", [("detector_epoch", "50000000-0000-4000-8000-000000000002"), ("schema_version", "other")])
def test_epoch_or_context_version_change_requires_explicit_handover(field, value):
    context = opened()["updated_context"]
    context[field] = value
    with pytest.raises(ValueError, match="handover"):
        run(240, context)


@pytest.mark.parametrize("field", ["configuration_version", "model_version", "parameter_version"])
def test_configuration_model_parameter_transition_does_not_recover_old_episode(field):
    context = opened()["updated_context"]
    saved = deepcopy(context)
    result = frame(240)
    result["metadata"][field] = {"configuration_version": 2, "model_version": "stored-reading-top-oil-1.0.1", "parameter_version": "new-profile"}[field]
    with pytest.raises(ValueError, match="binding"):
        evaluate_incident_candidates(result, policy(), detector_epoch=EPOCH, result_id=99, previous_context=context)
    assert context == saved
    fresh = evaluate_incident_candidates(result, policy(), detector_epoch="50000000-0000-4000-8000-000000000002", result_id=99)
    assert fresh["mutations"] == []
    assert context["detector_state"]["rules"]["capacity_overload"]["active"] is True


def test_error_result_requires_worker_rollback_and_historical_is_noop():
    context = opened()["updated_context"]
    result = frame(240)
    result["execution_status"]["outcome"] = "computation_error"
    with pytest.raises(ValueError, match="rollback"):
        evaluate_incident_candidates(result, policy(), detector_epoch=EPOCH, result_id=99, previous_context=context)
    result["execution_status"].update(outcome="completed", state_advanced=False)
    assert evaluate_incident_candidates(result, policy(), detector_epoch=EPOCH, result_id=99, previous_context=context)["updated_context"] == context


@pytest.mark.parametrize("key,value", [("detector_epoch", "19"), ("result_id", True), ("result_id", 0), ("continuity_break", "false")])
def test_invalid_control_values_rejected(key, value):
    args = {"detector_epoch": EPOCH, "result_id": 99}
    args[key] = value
    with pytest.raises(ValueError):
        evaluate_incident_candidates(frame(0), policy(), **args)


def test_barrier_does_not_repair_corrupt_state():
    context = opened()["updated_context"]
    context["detector_state"]["rules"]["capacity_overload"]["pending_s"] = -1
    with pytest.raises(ValueError):
        run(240, context, continuity_break=True)


def test_fresh_same_binding_epoch_disambiguates_restarted_candidate_sequence():
    old = opened()["mutations"][0]["mapping_key"]
    fresh_epoch = "50000000-0000-4000-8000-000000000002"
    first = evaluate_incident_candidates(frame(0), policy(), detector_epoch=fresh_epoch, result_id=1001)
    new = evaluate_incident_candidates(frame(180), policy(), detector_epoch=fresh_epoch,
                                      result_id=1181, previous_context=first["updated_context"])["mutations"][0]["mapping_key"]
    assert old["detector_episode_key"] == new["detector_episode_key"]
    assert old != new


def test_labels_and_arbitrary_payload_metadata_do_not_change_commands():
    context = run(0)["updated_context"]
    result = frame(180)
    args = {"detector_epoch": EPOCH, "result_id": 99, "previous_context": context}
    expected = evaluate_incident_candidates(result, policy(), **args)
    result["original_payload"] = {"scenario": "fault", "ground_truth": True}
    result["metadata"]["scenario"] = "normal"
    assert evaluate_incident_candidates(result, policy(), **args) == expected


@pytest.mark.parametrize("kind,code", [("control", "incident_invalid_control"), ("contract", "incident_unsupported_contract"), ("handover", "incident_handover_required"), ("computation", "incident_computation_rollback_required"), ("malformed", "incident_invalid_input_or_state")])
def test_errors_have_stable_codes_without_payload_content(kind, code):
    from analytics.incident_orchestration import IncidentPlanningError
    result = frame(240)
    args = {"detector_epoch": EPOCH, "result_id": 99}
    if kind == "control":
        args["result_id"] = 0
    elif kind == "contract":
        result["metadata"]["model_version"] = "not-supported"
    elif kind == "handover":
        args["previous_context"] = opened()["updated_context"]
        args["detector_epoch"] = "50000000-0000-4000-8000-000000000002"
    elif kind == "computation":
        result["execution_status"]["outcome"] = "computation_error"
    else:
        result = {"secret": "do-not-log-this"}
    with pytest.raises(IncidentPlanningError) as error:
        evaluate_incident_candidates(result, policy(), **args)
    assert error.value.code == code
    assert "do-not-log-this" not in str(error.value)
