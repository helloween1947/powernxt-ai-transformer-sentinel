"""Schemas and examples are a wire-contract check, not physical validation."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from analytics import process_stored_reading
from analytics.tests.test_worker import bound_config, record, with_measurements

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def validators():
    result = []
    for name in ("worker-input.schema.json", "worker-output.schema.json"):
        schema = json.loads((ROOT / "schemas" / name).read_text())
        Draft202012Validator.check_schema(schema)
        result.append(Draft202012Validator(schema, format_checker=FormatChecker()))
    return result


def test_execution_examples_match_schema_and_recompute_exactly(validators):
    examples = json.loads((ROOT / "examples/worker-test-examples.json").read_text())["examples"]
    for item in examples:
        validators[0].validate(item["input"])
        validators[1].validate(item["output"])
        assert process_stored_reading(**item["input"]) == item["output"]


@pytest.mark.parametrize("case", ["missing", "device", "zero", "gap", "historical", "no_limits", "no_initial_oil"])
def test_boundary_result_schemas(validators, case):
    cfg, row = bound_config(), record()
    previous = None
    if case == "missing":
        row = with_measurements(current_y_a=None, oil_temperature_c=None)
    elif case == "device":
        row = record(source="device", run_id=None)
    elif case == "zero":
        row = with_measurements(current_r_a=0, current_y_a=0, current_b_a=0)
    elif case == "gap":
        previous = process_stored_reading(row, cfg)["updated_state"]
        row = record(600)
    elif case == "historical":
        row["processing_job"]["state_policy"] = "historical_only"
    elif case == "no_initial_oil":
        row = with_measurements(oil_temperature_c=None)
    else:
        cfg["operational_limits"] = {}
        cfg["parameter_provenance"] = {k: v for k, v in cfg["parameter_provenance"].items() if not k.startswith("operational_limits.")}
    inputs = {"stored_reading": row, "asset_config": cfg, "previous_state": previous}
    validators[0].validate(inputs)
    output = process_stored_reading(**inputs)
    validators[1].validate(output)
