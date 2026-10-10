"""Pure adoption guards, not a database migration or historical API dispatcher."""
from copy import deepcopy
import json
import math

import pytest

from analytics import process_stored_reading, forecast_from_worker_state
from analytics.tests.test_worker import bound_config, record, with_measurements
from analytics.worker import MODEL_VERSION, _parameter_version


def test_old_model_state_is_rejected_and_preserved_before_explicit_cold_start():
    config = bound_config()
    old = process_stored_reading(record(), config)["updated_state"]
    # A valid-shaped old binding is sufficient to verify refusal of state reuse.
    # This does not simulate or claim to execute an old model implementation.
    old["binding"]["model_version"] = "stored-reading-top-oil-1.0.1"
    saved = deepcopy(old)
    with pytest.raises(ValueError, match="binding changed"):
        process_stored_reading(record(60), config, old)
    assert old == saved

    first = process_stored_reading(record(60), config, previous_state=None)
    assert MODEL_VERSION == "stored-reading-top-oil-1.0.2"
    assert first["metadata"]["model_version"] == MODEL_VERSION
    assert first["thermal_assessment"]["predicted_top_oil_temperature_c"] is None
    assert first["thermal_assessment"]["thermal_residual_c"] is None
    assert first["updated_state"]["thermal"]["oil_temp_c"] == 55
    assert "initialized_from_measurement_prediction_not_independent" in first["thermal_assessment"]["reasons"]

    second = process_stored_reading(with_measurements(120, oil_temperature_c=100), config, first["updated_state"])
    expected = 70 - 15 * math.exp(-60 / 10800)
    assert second["thermal_assessment"]["elapsed_s"] == 60
    assert second["thermal_assessment"]["predicted_top_oil_temperature_c"] == pytest.approx(expected)
    assert second["thermal_assessment"]["thermal_residual_c"] == pytest.approx(100 - expected)
    assert second["updated_state"]["thermal"]["oil_temp_c"] == pytest.approx(expected)
    assert old == saved
    json.dumps(second, allow_nan=False)


def test_model_namespace_changes_do_not_invent_parameter_fingerprints():
    config = bound_config()
    saved = deepcopy(config)
    expected = _parameter_version(config)
    result = process_stored_reading(record(), config)
    assert result["metadata"]["parameter_version"] == expected
    assert result["updated_state"]["binding"]["parameter_version"] == expected
    assert config == saved


def test_current_forecast_rejects_old_model_without_relabelling_capture():
    config = bound_config()
    capture = process_stored_reading(record(), config)["updated_state"]
    capture["binding"]["model_version"] = "stored-reading-top-oil-1.0.1"
    saved = deepcopy(capture)
    with pytest.raises(ValueError, match="matching model"):
        forecast_from_worker_state(capture, config, [{
            "duration_s": 3600, "thermal_load_pu": 1, "ambient_temp_c": 30}])
    assert capture == saved
