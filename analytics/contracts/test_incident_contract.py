"""Proposal consistency only; not tests of implemented incident persistence."""
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest
from analytics.worker import MODEL_VERSION

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    return json.loads((ROOT/"analytics/examples/incident-contract-proposed-example.json").read_text())


def validator():
    schema = json.loads((ROOT/"analytics/contracts/incident-proposal.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_snapshots_validate_and_keep_one_episode_identity():
    cases = fixture()["incident_snapshots"]
    for case in cases:
        validator().validate(case)
        json.dumps(case, allow_nan=False)
    assert len({case["incident_id"] for case in cases}) == 1
    assert len({case["detector_episode_key"] for case in cases}) == 1
    assert [c["condition_status"] for c in cases] == ["active", "active", "recovered"]
    assert len({e["reading_id"] for e in cases[-1]["evidence"]}) == 3
    assert len({e["result_id"] for e in cases[-1]["evidence"]}) == 3


def test_task_completion_and_recovery_do_not_acknowledge():
    f = fixture()
    assert f["task_status_example"] == "completed"
    assert f["incident_snapshots"][0]["condition_status"] == "active"
    assert all(c["acknowledgement"]["status"] == "unacknowledged" for c in f["incident_snapshots"])


def test_residual_units_confidence_and_provenance_remain_honest():
    for e in fixture()["incident_snapshots"][-1]["evidence"]:
        t = e["temperatures"]
        assert t["thermal_residual_c"] == pytest.approx(t["measured_top_oil_temperature_c"]-t["predicted_top_oil_temperature_c"])
        assert e["temperature_unit"] == "C"
        assert e["data_confidence"]["score"] is None
        assert e["policy_provenance"] == "assumed"
        assert e["versions"]["model_version"] == MODEL_VERSION
        assert e["parameter_provenance"]["thermal_parameters.oil_exponent"] == "assumed"


@pytest.mark.parametrize("field,value", [("incident_id", "19"), ("incident_id", 19), ("source", "sample"), ("condition_status", "completed"), ("measurement_source", "normal_scenario")])
def test_reading_ids_sample_labels_and_task_statuses_are_not_incident_identity(field, value):
    case = deepcopy(fixture()["incident_snapshots"][0])
    case[field] = value
    assert list(validator().iter_errors(case))


def test_predicted_and_confidence_values_can_remain_unavailable():
    case = fixture()["incident_snapshots"][0]
    case["evidence"][0]["temperatures"]["predicted_top_oil_temperature_c"] = None
    case["evidence"][0]["temperatures"]["thermal_residual_c"] = None
    validator().validate(case)
    case["evidence"][0]["data_confidence"]["score"] = 0.99
    assert list(validator().iter_errors(case))


@pytest.mark.parametrize("field,value", [("quantity", "original_payload.scenario"), ("unit", "C")])
def test_rule_evidence_rejects_labels_and_incompatible_units(field, value):
    case = fixture()["incident_snapshots"][0]
    case["evidence"][0]["rule_evidence"][field] = value
    assert list(validator().iter_errors(case))
