"""Sampled evidence lifecycle checks; not statistical fault validation."""
from copy import deepcopy
import json
import math
from pathlib import Path

import pytest

from analytics import evaluate_persistent_rules, process_stored_reading
from analytics.tests.test_worker import bound_config, record, with_measurements


def policy():
    return {"version": "test-policy-v1", "provenance": "assumed", "max_gap_s": 300,
            "rules": [{"name": "capacity_overload", "quantity": "electrical_metrics.capacity_loading_pct", "unit": "%",
                       "trigger": 120, "recovery": 100, "persistence_s": 180, "recovery_s": 120, "severity": "warning"}]}


def frame(t, load=1.5, missing=False):
    row = with_measurements(t, **{f"current_{p}_a": 52.49*load for p in "ryb"})
    if missing:
        row["normalized_telemetry"]["measurements"]["current_y_a"] = None
    return process_stored_reading(row, bound_config(thermal=False))


def advance(times, state=None, load=1.5):
    result = None
    for t in times:
        result = evaluate_persistent_rules(frame(t, load), policy(), state)
        state = json.loads(json.dumps(result["updated_state"], allow_nan=False))
    return result


def test_first_sample_starts_at_zero_and_sustained_endpoints_open_once():
    first = advance([0])
    assert first["events"] == []
    assert first["updated_state"]["rules"]["capacity_overload"]["pending_s"] == 0
    opened = advance([59, 137, 179, 180], first["updated_state"])
    assert len(opened["events"]) == 1
    assert opened["events"][0]["lifecycle"] == "opened"
    assert opened["events"][0]["evidence"]["unit"] == "%"
    assert advance([240], opened["updated_state"])["events"] == []


def test_recovery_is_sustained_hysteretic_and_retains_incident_identity():
    opened = advance([0, 180])
    state = opened["updated_state"]
    recovery = advance([240, 300], state, load=0.5)
    assert recovery["events"] == []
    assert len(recovery["active_incidents"]) == 1
    deadband = advance([360], recovery["updated_state"], load=1.1)
    assert deadband["updated_state"]["rules"]["capacity_overload"]["recovery_s"] == 0
    resolved = advance([420, 480, 540], deadband["updated_state"], load=0.5)
    assert resolved["events"][0]["lifecycle"] == "resolved"
    assert resolved["events"][0]["incident_id"] == opened["events"][0]["incident_id"]
    assert resolved["active_incidents"] == []
    reopened = advance([600, 780], resolved["updated_state"])
    assert reopened["events"][0]["incident_id"] != opened["events"][0]["incident_id"]


def test_missing_evidence_never_resolves_and_interrupts_timers():
    state = advance([0, 180])["updated_state"]
    recovering = advance([240, 300], state, load=0.5)
    missing = evaluate_persistent_rules(frame(360, missing=True), policy(), recovering["updated_state"])
    assert missing["events"] == []
    assert len(missing["active_incidents"]) == 1
    assert missing["evidence"][0]["value"] is None
    assert missing["active_incidents"][0]["recovery_s"] == 0
    assert advance([420, 480], missing["updated_state"], load=0.5)["events"] == []


@pytest.mark.parametrize("dt,opened", [(300, True), (301, False), (3600, False)])
def test_gap_policy_does_not_credit_unknown_intervals(dt, opened):
    state = advance([0])["updated_state"]
    result = advance([dt], state)
    assert bool(result["events"]) == opened
    if not opened:
        assert result["evidence"][0]["continuity"] == "gap_reset"
        assert result["updated_state"]["rules"]["capacity_overload"]["pending_s"] == 0


@pytest.mark.parametrize("t", [0, 60])
def test_equal_late_frames_return_unchanged_state(t):
    state = advance([120])["updated_state"]
    sample = frame(t)
    before = deepcopy(state)
    output = evaluate_persistent_rules(sample, policy(), state)
    assert output["state_advanced"] is False
    assert output["updated_state"] == state == before
    assert output["events"] == []


def test_retry_with_same_prestate_is_deterministic_and_poststate_noop():
    state = advance([0])["updated_state"]
    sample = frame(180)
    before = deepcopy(sample)
    first = evaluate_persistent_rules(sample, policy(), state)
    assert evaluate_persistent_rules(sample, policy(), state) == first
    retry = evaluate_persistent_rules(sample, policy(), first["updated_state"])
    assert retry["events"] == []
    assert retry["updated_state"] == first["updated_state"]
    assert sample == before


@pytest.mark.parametrize("key", ["historical", "error"])
def test_ineligible_analytics_cannot_advance_detector(key):
    sample = frame(0)
    if key == "historical":
        sample["execution_status"]["state_advanced"] = False
    else:
        sample["execution_status"]["outcome"] = "computation_error"
    result = evaluate_persistent_rules(sample, policy())
    assert result["state_advanced"] is False
    assert result["updated_state"] is None


@pytest.mark.parametrize("key", ["stream", "configuration_version", "model_version", "parameter_version", "policy"])
def test_changed_binding_requires_explicit_reset(key):
    state = advance([0])["updated_state"]
    sample, p = frame(60), policy()
    if key == "policy":
        p["rules"][0]["trigger"] = 130
    elif key == "stream":
        sample["metadata"]["stream"]["run_id"] = "another-run"
    else:
        sample["metadata"][key] = "changed"
    with pytest.raises(ValueError, match="binding"):
        evaluate_persistent_rules(sample, p, state)


@pytest.mark.parametrize("key,value", [("trigger", float("nan")), ("recovery", 121), ("persistence_s", 0), ("severity", "guess"), ("unit", "kW"), ("quantity", "original_payload.label")])
def test_invalid_or_unsupported_rules_rejected(key, value):
    p = policy()
    p["rules"][0][key] = value
    with pytest.raises(ValueError):
        evaluate_persistent_rules(frame(0), p)


def test_threshold_equality_is_not_abnormal_and_zero_recovers():
    sample = frame(0)
    p = policy()
    p["rules"][0]["trigger"] = sample["electrical_metrics"]["capacity_loading_pct"]
    first = evaluate_persistent_rules(sample, p)
    second = evaluate_persistent_rules(frame(180), p, first["updated_state"])
    assert second["events"] == []
    opened = advance([0, 180])
    assert advance([240, 360], opened["updated_state"], load=0)["events"][0]["lifecycle"] == "resolved"


def test_positive_residual_persists_without_using_scenario_labels():
    p = policy()
    p["rules"][0].update(name="unexpected_heating", quantity="thermal_assessment.thermal_residual_c", unit="C", trigger=8, recovery=4)
    initial = process_stored_reading(record(), bound_config())["updated_state"]
    state = None
    for t in (60, 120, 180, 240):
        expected = 70-15*math.exp(-t/10800)
        sample = process_stored_reading(with_measurements(t, oil_temperature_c=expected+10), bound_config(), initial)
        before = evaluate_persistent_rules(sample, p, state)
        sample["original_payload"] = {"ground_truth": "normal"}
        sample["metadata"]["scenario"] = "sensor_failure"
        assert evaluate_persistent_rules(sample, p, state) == before
        state = before["updated_state"]
    assert before["events"][0]["category"] == "unexpected_heating"
    assert before["events"][0]["evidence"]["value"] == pytest.approx(10)


def test_stale_availability_and_inconsistent_identity_are_not_trusted():
    sample = frame(0)
    sample["execution_status"]["availability"]["electrical_metrics.capacity_loading_pct"]["status"] = "unavailable"
    assert evaluate_persistent_rules(sample, policy())["evidence"][0]["available"] is False
    state = advance([0])["updated_state"]
    later = frame(60)
    later["metadata"]["reading_identity"] = state["last_reading_identity"]
    with pytest.raises(ValueError, match="identity"):
        evaluate_persistent_rules(later, policy(), state)


def test_executed_demo_recomputes_and_has_expected_lifecycle():
    path = Path(__file__).resolve().parents[1]/"examples/persistent-rules-test-example.json"
    example = json.loads(path.read_text())
    events = []
    for item in example["frames"]:
        actual = evaluate_persistent_rules(item["analytics_result"], example["policy"], item["previous_detector_state"])
        assert actual == item["detector_result"]
        events.extend(actual["events"])
    assert [event["lifecycle"] for event in events] == ["opened", "resolved"]
    assert [event["evidence"]["measurement_time"] for event in events] == ["2026-01-01T00:03:00Z", "2026-01-01T00:06:00Z"]
