import json
import math
import unittest
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone

from analytics.transformer_twin import *


CONFIG = AssetConfig()


def reading(second=0, **changes):
    result = {"asset_id": CONFIG.asset_id,
              "timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=second)).isoformat(),
              "currents_a": [35.0] * 3, "voltages_v": [260.0] * 3,
              "ambient_temp_c": 30.0, "oil_temp_c": 55.0, "source": "simulated"}
    result.update(changes)
    return result


class TwinTests(unittest.TestCase):
    def setUp(self):
        self.state = ThermalState(55, 30, CONFIG)

    def test_electrical_metrics(self):
        m = calculate_electrical_metrics(reading(currents_a=[25, 50, 75]), CONFIG)
        self.assertEqual(m["phase_loading_pct"], [50, 100, 150])
        self.assertEqual(m["current_imbalance_pct"], 50)
        self.assertAlmostEqual(m["apparent_power_kva"], 39)
        self.assertAlmostEqual(m["thermal_load_pu"], math.sqrt(3.5 / 3))

    def test_zero_current_is_valid(self):
        m = calculate_electrical_metrics(reading(currents_a=[0, 0, 0]), CONFIG)
        self.assertEqual(m["thermal_load_pu"], 0)
        self.assertEqual(m["current_imbalance_pct"], 0)

    def test_gradual_heating_and_exact_solution(self):
        hot = reading(currents_a=[75] * 3)
        one = update_thermal_state(self.state, hot, 60)
        target = 30 + 40 * ((1 + 5 * 1.5 ** 2) / 6) ** 0.8
        self.assertTrue(55 < one.predicted_oil_temp_c < target)
        self.assertAlmostEqual(one.predicted_oil_temp_c, target + (55 - target) * math.exp(-60 / 10800))
        two = update_thermal_state(one, hot, 60)
        joined = update_thermal_state(self.state, hot, 120)
        self.assertAlmostEqual(two.predicted_oil_temp_c, joined.predicted_oil_temp_c)

    def test_measurement_does_not_absorb_fault(self):
        a = update_thermal_state(self.state, reading(oil_temp_c=55), 60)
        b = update_thermal_state(self.state, reading(oil_temp_c=120), 60)
        self.assertEqual(a, b)

    def test_invalid_and_gap_latch(self):
        for row in (reading(currents_a=[-1, 40, 40]), reading(ambient_temp_c=float("nan"))):
            state = update_thermal_state(self.state, row, 60)
            self.assertFalse(state.valid)
            self.assertFalse(update_thermal_state(state, reading(), 60).valid)
        self.assertFalse(update_thermal_state(self.state, reading(), 301).valid)
        with self.assertRaises(ValueError):
            update_thermal_state(self.state, reading(), -1)

    def test_persistence_hysteresis_recovery_and_missing(self):
        metrics = calculate_electrical_metrics(reading(), CONFIG)
        history = {}
        def step(value):
            nonlocal history
            output = detect_anomalies(metrics, {"residual_c": value, "elapsed_s": 60}, history)
            history = output["history"]
            return output
        self.assertEqual(step(12)["events"], [])
        self.assertEqual(step(12)["events"], [])
        self.assertEqual(step(12)["events"], [])
        opened = step(12)["events"][0]
        self.assertEqual(opened["lifecycle"], "opened")
        self.assertEqual(step(None)["active_alerts"][0]["evidence_available"], False)
        step(3)
        step(3)
        step(6)  # Dead band interrupts recovery.
        step(3)
        step(3)
        step(3)
        resolved = step(3)["events"][0]
        self.assertEqual(resolved["lifecycle"], "resolved")
        self.assertEqual(resolved["incident_id"], opened["incident_id"])

    def test_outlier_cannot_open_alert(self):
        m = calculate_electrical_metrics(reading(), CONFIG)
        history = {}
        for value in (0, 20, 0, 0):
            output = detect_anomalies(m, {"residual_c": value, "elapsed_s": 60}, history)
            self.assertFalse(output["events"])
            history = output["history"]

    def test_oil_alert_escalates_and_preserves_severity(self):
        metrics = calculate_electrical_metrics(reading(), CONFIG)
        history = {}
        for value in (90, 90, 90, 90, 105):
            result = detect_anomalies(metrics, {"oil_temp_c": value, "elapsed_s": 60}, history)
            history = result["history"]
        self.assertEqual(result["active_alerts"][0]["severity"], "critical")
        for value in (70, 70, 70, 70):
            result = detect_anomalies(metrics, {"oil_temp_c": value, "elapsed_s": 60}, history)
            history = result["history"]
        self.assertEqual(result["events"][0]["severity"], "critical")
        self.assertEqual(result["events"][0]["lifecycle"], "resolved")

    def test_forecast_crossing_and_boundary_inputs(self):
        high = ThermalState(90, 30, CONFIG)
        output = forecast_temperature(high, [{"duration_s": 10, "load_pu": 0, "ambient_temp_c": 30}])
        self.assertEqual(output["warning_crossing_s"], 0)
        self.assertEqual(len(output["points"]), 2)
        self.assertLess(output["final_oil_temp_c"], 90)
        for profile in ([], [{"duration_s": 0, "load_pu": 1, "ambient_temp_c": 30}],
                        [{"duration_s": 60, "load_pu": -1, "ambient_temp_c": 30}],
                        [{"duration_s": 60, "load_pu": 1, "ambient_temp_c": 30, "cooling_factor": 0}]):
            with self.assertRaises(ValueError):
                forecast_temperature(self.state, profile)

    def test_restart_and_duplicate(self):
        engine = TwinEngine()
        engine.process(reading(0, currents_a=[65] * 3))
        engine.process(reading(60, currents_a=[65] * 3))
        snapshot = json.loads(json.dumps(engine.snapshot(), allow_nan=False))
        restored = TwinEngine.restore(snapshot)
        for second in (120, 180, 240):
            self.assertEqual(engine.process(reading(second, currents_a=[65] * 3)),
                             restored.process(reading(second, currents_a=[65] * 3)))
        before = engine.snapshot()
        self.assertFalse(engine.process(reading(240))["accepted"])
        self.assertFalse(engine.process(reading(120))["accepted"])
        self.assertEqual(before, engine.snapshot())

    def test_flags_confidence_and_sensor_incident(self):
        engine = TwinEngine()
        for second in (0, 60, 120, 180):
            output = engine.process(reading(second, quality={"oil_temp_c": "invalid"}))
        self.assertIsNone(output["thermal"]["residual_c"])
        self.assertEqual(output["condition"]["status"], "unknown")
        self.assertEqual(output["data_quality"]["confidence"], 0.75)
        self.assertEqual(output["alerts"]["events"][0]["type"], "data_unavailable")
        json.dumps(output, allow_nan=False)

    def test_stale_and_bad_source_do_not_mutate(self):
        engine = TwinEngine()
        before = engine.snapshot()
        self.assertFalse(engine.process(reading(), now=reading(600)["timestamp"])["accepted"])
        with self.assertRaises(ValueError):
            engine.process(reading(source="bad"))
        self.assertEqual(before, engine.snapshot())

    def test_gap_and_reinitialize(self):
        engine = TwinEngine()
        engine.process(reading())
        output = engine.process(reading(600))
        self.assertIsNone(output["thermal"]["predicted_oil_temp_c"])
        self.assertEqual(output["condition"]["status"], "unknown")
        with self.assertRaises(ValueError):
            forecast_temperature(engine.state, [{"duration_s": 60, "load_pu": 1, "ambient_temp_c": 30}])
        engine.initialize_temperature(55, 30)
        self.assertTrue(engine.process(reading(660))["thermal"]["valid"])

    def test_what_if_and_equal_horizon(self):
        def scenario(name, load, cooling=1, ambient=30):
            return {"name": name, "profile": [{"duration_s": 7200, "load_pu": load, "ambient_temp_c": ambient, "cooling_factor": cooling}]}
        comparison = compare_scenarios(self.state, [scenario("baseline", 1.3), scenario("shed_load", 0.7),
                                                   scenario("reduced_cooling", 1.3, 0.5), scenario("hot_ambient", 1.3, ambient=40)])
        rows = comparison["scenarios"]
        self.assertLess(rows[1]["final_delta_from_baseline_c"], 0)
        self.assertGreater(rows[2]["final_delta_from_baseline_c"], 0)
        self.assertGreater(rows[3]["final_delta_from_baseline_c"], 0)
        self.assertEqual(self.state.predicted_oil_temp_c, 55)
        with self.assertRaises(ValueError):
            compare_scenarios(self.state, [scenario("a", 1), {"name": "b", "profile": [{"duration_s": 60}]}])

    def test_labels_excluded_and_inputs_not_mutated(self):
        row = reading(scenario_label="reduced_cooling")
        copy = dict(row)
        first = TwinEngine().process(row)
        self.assertEqual(first, TwinEngine().process(reading(scenario_label="normal")))
        self.assertEqual(row, copy)

    def test_bad_configs_and_nonfinite(self):
        for changes in ({"time_constant_s": 0}, {"rated_current_a": float("nan")},
                        {"residual_recovery_c": 10}, {"oil_warning_c": 110}):
            with self.assertRaises(ValueError):
                replace(CONFIG, **changes)
        output = TwinEngine().process(reading(oil_temp_c=float("inf")))
        json.dumps(output, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
