"""Contract and state safety checks use teammate-supplied configuration/telemetry."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import unittest
from uuid import uuid4

from analytics import process_reading, process_telemetry_response, compare_what_if

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_CATEGORIES = {
    "electrical_metrics", "thermal_assessment", "condition_contributors", "data_confidence",
    "anomaly_observations", "updated_state", "metadata", "execution_status",
}


def config(thermal=True, **changes):
    value = json.loads((ROOT / "data/sample/asset-configuration-assumed.json").read_text())
    value.update(asset_id="DT-001", version=1)
    if thermal:
        value["thermal_parameters"] = {
            "rated_top_oil_rise_c": 40, "oil_time_constant_min": 180,
            "loss_ratio": 5, "oil_exponent": 0.8,
        }
        value["parameter_provenance"].update({f"thermal_parameters.{k}": "assumed" for k in value["thermal_parameters"]})
    value.update(changes)
    return value


def packet(second=0, **changes):
    value = {"schema_version": "1.0.0", "message_id": str(uuid4()), "asset_id": "DT-001",
             "timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=second)).isoformat(),
             "source": "simulator", "run_id": "test-run", "configuration_version": 1,
             "measurements": {"voltage_r_v": 11000, "voltage_y_v": 11000, "voltage_b_v": 11000,
                              "current_r_a": 52.49, "current_y_a": 52.49, "current_b_a": 52.49,
                              "oil_temperature_c": 55, "ambient_temperature_c": 30, "oil_level_pct": 80}}
    value.update(changes)
    return value


def stable(result):
    value = deepcopy(result)
    value["metadata"].pop("evaluation_time")
    return value


class AdapterTests(unittest.TestCase):
    def test_actual_sample_and_eight_output_categories(self):
        sample = json.loads((ROOT / "data/sample/telemetry-sample.json").read_text())
        bound = config(thermal=False, asset_id=sample["asset_id"])
        result = process_reading(sample, {}, bound)
        self.assertEqual(set(result), EXPECTED_CATEGORIES)
        self.assertIsNone(result["thermal_assessment"]["predicted_top_oil_temperature_c"])
        self.assertEqual(result["execution_status"]["status"], "degraded")
        self.assertEqual(result["data_confidence"]["score"], 1.0)
        self.assertEqual(len(result["thermal_assessment"]["missing_configuration_parameters"]), 4)
        json.dumps(result, allow_nan=False)

    def test_voltage_convention_power_and_minutes(self):
        result = process_reading(packet(), {}, config())
        expected = math.sqrt(3) * 11000 * 52.49 / 1000
        self.assertAlmostEqual(result["electrical_metrics"]["apparent_power_kva"], expected)
        self.assertAlmostEqual(result["electrical_metrics"]["capacity_loading_pct"], expected / 10)
        self.assertEqual(result["updated_state"]["engine"]["config"]["time_constant_s"], 10800)
        self.assertIsNone(result["electrical_metrics"]["power_factor"])
        cfg = config(rated_voltage_v=260, voltage_convention="phase_to_neutral", rated_current_a=50)
        row = packet()
        for phase in ("r", "y", "b"):
            row["measurements"][f"voltage_{phase}_v"] = 260
            row["measurements"][f"current_{phase}_a"] = 50
        self.assertEqual(process_reading(row, {}, cfg)["electrical_metrics"]["apparent_power_kva"], 39)

    def test_quality_channel_flags_and_zero(self):
        row = packet(measurement_quality={"oil_temperature_c": "suspect"})
        result = process_reading(row, {"current_y_a": ["bad"]}, config())
        self.assertIsNone(result["electrical_metrics"]["thermal_load_pu"])
        self.assertIsNone(result["thermal_assessment"]["measured_top_oil_temperature_c"])
        self.assertEqual(result["data_confidence"]["score"], 6 / 8)
        self.assertEqual(result["data_confidence"]["quality_reasons"]["oil_temperature_c"], ["suspect"])
        row = packet()
        for phase in ("r", "y", "b"):
            row["measurements"][f"current_{phase}_a"] = 0
        self.assertEqual(process_reading(row, {}, config())["electrical_metrics"]["thermal_load_pu"], 0)

    def test_complete_thermal_requires_measured_initial_condition(self):
        result = process_reading(packet(), {}, config())
        self.assertEqual(result["thermal_assessment"]["predicted_top_oil_temperature_c"], 55)
        row = packet(60)
        row["measurements"]["oil_temperature_c"] = 100
        next_result = process_reading(row, {}, config(), result["updated_state"])
        self.assertTrue(55 < next_result["thermal_assessment"]["predicted_top_oil_temperature_c"] < 56)
        self.assertGreater(next_result["thermal_assessment"]["thermal_residual_c"], 44)

    def test_configuration_binding_and_stream_isolation(self):
        state = process_reading(packet(), {}, config())["updated_state"]
        for changes in ({"source": "device", "run_id": None}, {"run_id": "other"}, {"source": "file_replay"}):
            with self.assertRaises(ValueError):
                process_reading(packet(60, **changes), {}, config(), state)
        for changes in ({"version": 2}, {"asset_id": "other"}):
            with self.assertRaises(ValueError):
                process_reading(packet(), {}, config(**changes))
        changed = config()
        changed["rated_current_a"] = 60
        with self.assertRaises(ValueError):
            process_reading(packet(60), {}, changed, state)
        with self.assertRaises(ValueError):
            process_reading(packet(60, configuration_version=2), {}, config(version=2), state)

    def test_equal_and_late_do_not_advance(self):
        state = process_reading(packet(120), {}, config())["updated_state"]
        before = deepcopy(state)
        for stamp in (120, 0):
            result = process_reading(packet(stamp), {}, config(), state)
            self.assertFalse(result["execution_status"]["state_advanced"])
            self.assertEqual(result["updated_state"], before)
            self.assertIsNone(result["thermal_assessment"]["predicted_top_oil_temperature_c"])
        self.assertEqual(state, before)

    def test_actual_response_ignores_original_metadata_and_historical_policy(self):
        response = json.loads((ROOT / "data/sample/telemetry-response-sample.json").read_text())
        result = process_telemetry_response(response, config(thermal=False, asset_id=response["asset_id"]))
        self.assertEqual(result["execution_status"]["status"], "insufficient_data")
        changed = deepcopy(response)
        changed["original_payload"]["fault_label"] = "overload"
        self.assertEqual(stable(result), stable(process_telemetry_response(changed, config(thermal=False, asset_id=response["asset_id"]))))
        changed["processing_job"]["state_policy"] = "historical_only"
        result = process_telemetry_response(changed, config(thermal=False, asset_id=response["asset_id"]))
        self.assertIsNone(result["updated_state"])
        self.assertFalse(result["execution_status"]["state_advanced"])

    def test_restart_persistence_uses_configured_overload_limit(self):
        state = None
        for second in (0, 60, 120, 180):
            row = packet(second)
            for phase in ("r", "y", "b"):
                row["measurements"][f"current_{phase}_a"] = 1.1 * 52.49
            result = process_reading(row, {}, config(), state)
            state = json.loads(json.dumps(result["updated_state"], allow_nan=False))
        self.assertFalse(any(a["category"] == "overload" for a in result["anomaly_observations"]))
        for second in (240, 300, 360, 420):
            row = packet(second)
            for phase in ("r", "y", "b"):
                row["measurements"][f"current_{phase}_a"] = 1.3 * 52.49
            first = process_reading(row, {}, config(), state)
            restored = process_reading(row, {}, config(), json.loads(json.dumps(state)))
            self.assertEqual(stable(first), stable(restored))
            state = first["updated_state"]
        observation = next(a for a in first["anomaly_observations"] if a["category"] == "overload")
        self.assertEqual(observation["lifecycle"], "opened")
        self.assertEqual(observation["threshold"], 120)
        self.assertIn(":simulator:test-run:cfg1:", observation["incident_id"])
        rejected = process_reading(packet(360), {}, config(), state)
        self.assertTrue(rejected["anomaly_observations"])
        self.assertFalse(rejected["anomaly_observations"][0]["evidence_available"])
        self.assertEqual(rejected["updated_state"], state)
        different_config = process_reading(packet(420, configuration_version=2), {}, config(version=2), state)
        self.assertEqual(different_config["updated_state"], state)
        self.assertEqual(different_config["anomaly_observations"][0]["incident_id"], observation["incident_id"])

    def test_no_limits_do_not_invent_oil_or_overload_alerts(self):
        cfg = config(operational_limits={})
        state = None
        for second in (0, 60, 120, 180):
            row = packet(second)
            row["measurements"]["oil_temperature_c"] = 110
            for phase in ("r", "y", "b"):
                row["measurements"][f"current_{phase}_a"] = 80
            result = process_reading(row, {}, cfg, state)
            state = result["updated_state"]
        self.assertFalse(any(a["category"] in ("overload", "high_oil_temperature") for a in result["anomaly_observations"]))
        self.assertIsNone(result["condition_contributors"]["health_index"])

    def test_gap_disables_forecast_and_what_if_matches_bound_state(self):
        initial = process_reading(packet(), {}, config())
        scenarios = [{"name": name, "profile": [{"duration_s": 7200, "load_pu": load, "ambient_temp_c": 30}]}
                     for name, load in (("baseline", 1.3), ("shed", 0.7))]
        comparison = compare_what_if(initial["updated_state"], scenarios)
        self.assertLess(comparison["scenarios"][1]["final_delta_from_baseline_c"], 0)
        self.assertEqual(comparison["initial_oil_temp_c"], 55)
        broken = process_reading(packet(600), {}, config(), initial["updated_state"])
        with self.assertRaises(ValueError):
            compare_what_if(broken["updated_state"], scenarios)
        missing = process_reading(packet(), {}, config(thermal=False))
        with self.assertRaises(ValueError):
            compare_what_if(missing["updated_state"], scenarios)

    def test_stale_upstream_does_not_advance(self):
        state = process_reading(packet(), {}, config())["updated_state"]
        result = process_reading(packet(60), {"stale": True}, config(), state)
        self.assertEqual(result["updated_state"], state)
        self.assertFalse(result["execution_status"]["state_advanced"])


if __name__ == "__main__":
    unittest.main()
