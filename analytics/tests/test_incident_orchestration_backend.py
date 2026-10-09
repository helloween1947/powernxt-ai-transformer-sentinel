"""Real stored model1.0.1 results -> pure plan; incident storage is not implemented."""
from uuid import uuid4

from backend.app.services.analytics_worker import run_once
from backend.tests.conftest import asset, configuration, registry
from analytics import evaluate_incident_candidates


def test_deployed_worker_results_produce_episode_plans_without_model_upgrade(registry, asset, configuration):
    client, factory = registry
    response = client.post(f"/api/v1/assets/{asset['asset_id']}/configurations", json=configuration)
    assert response.status_code == 201
    cfg = response.json()
    policy = {"version": "stored-demo-policy-v1", "provenance": "assumed", "max_gap_s": 300,
              "rules": [{"name": "capacity_overload", "quantity": "electrical_metrics.capacity_loading_pct", "unit": "%",
                         "trigger": 120, "recovery": 100, "persistence_s": 180, "recovery_s": 120, "severity": "warning"}]}
    context, commands, result_ids = None, [], []
    for seconds, load in ((0, 1.5), (180, 1.5), (240, .5), (360, .5)):
        packet = {"schema_version": "1.0.0", "message_id": str(uuid4()), "asset_id": asset["asset_id"],
                  "source": "simulator", "run_id": "stored-incident-plan-test", "configuration_version": cfg["version"],
                  "timestamp": f"2026-01-01T00:{seconds//60:02d}:00Z",
                  "measurements": {**{f"voltage_{p}_v": cfg["rated_voltage_v"] for p in "ryb"},
                                   **{f"current_{p}_a": cfg["rated_current_a"]*load for p in "ryb"},
                                   "oil_temperature_c": 55, "ambient_temperature_c": 30}}
        admitted = client.post("/api/v1/telemetry", json=packet)
        assert admitted.status_code == 201
        reading_id = admitted.json()["id"]
        assert run_once(factory)
        envelope = client.get(f"/api/v1/telemetry/{reading_id}/analytics").json()
        result = envelope["result"]
        assert result["model_version"] in ("stored-reading-top-oil-1.0.1", "stored-reading-top-oil-1.0.2")
        plan = evaluate_incident_candidates(result["payload"], policy,
                   detector_epoch="50000000-0000-4000-8000-000000000001",
                   result_id=result["id"], previous_context=context)
        context = plan["updated_context"]
        for command in plan["mutations"]:
            assert command["evidence"]["reading_id"] == reading_id
            assert command["evidence"]["result_id"] == result["id"]
            assert command["evidence"]["message_id"] == packet["message_id"]
        commands.extend(plan["mutations"])
        result_ids.append(result["id"])
    assert [command["kind"] for command in commands] == ["opened", "updated", "recovered"]
    assert all(command["mapping_key"] == commands[0]["mapping_key"] for command in commands)
    assert len(set(result_ids)) == 4
