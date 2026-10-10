import json
import time
import urllib.request
import urllib.error
from uuid import uuid4

BASE_URL = "http://127.0.0.1:8801"
TOKEN = "sentinel_phase4_operator_token_live"

def request(path, method="GET", payload=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read().decode()
            return resp.status, json.loads(content) if content else None
    except urllib.error.HTTPError as err:
        content = err.read().decode()
        try:
            return err.code, json.loads(content)
        except:
            return err.code, content

def run_test():
    results = {}
    print("=== Phase 4 Complete Integration Verification ===")
    
    # 1. Operator Auth
    print("1. Verifying Operator Session...")
    status, op = request("/api/v1/operators/me", token=TOKEN)
    assert status == 200, f"Operator check failed: {op}"
    print(f"   Logged in: {op['name']} (Role: {op['role']}, Ref: {op['actor_ref']})")
    results["1_operator_auth"] = "PASS"

    # 2. Asset & Configuration Setup
    print("2. Creating asset and configuration with thermal parameters...")
    asset_id = f"tx-p4-{uuid4().hex[:8]}"
    status, _ = request("/api/v1/assets", method="POST", payload={
        "asset_id": asset_id,
        "name": f"Transformer {asset_id}",
        "location": "Bay 4",
        "timezone": "UTC"
    })
    assert status == 201

    cfg_payload = {
        "rated_kva": 25000.0,
        "rated_voltage_v": 115000.0,
        "rated_current_a": 125.5,
        "voltage_convention": "line_to_line",
        "measurement_side": "primary",
        "cooling_type": "ONAN",
        "operational_limits": {"max_top_oil_temp_c": 105.0},
        "thermal_parameters": {
            "rated_top_oil_rise_c": 40.0,
            "oil_time_constant_min": 180.0,
            "loss_ratio": 5.0,
            "oil_exponent": 0.8
        },
        "parameter_provenance": {
            "rated_kva": "nameplate",
            "rated_voltage_v": "nameplate",
            "rated_current_a": "nameplate",
            "voltage_convention": "nameplate",
            "measurement_side": "nameplate",
            "cooling_type": "nameplate",
            "operational_limits.max_top_oil_temp_c": "assumed",
            "thermal_parameters.rated_top_oil_rise_c": "assumed",
            "thermal_parameters.oil_time_constant_min": "assumed",
            "thermal_parameters.loss_ratio": "assumed",
            "thermal_parameters.oil_exponent": "assumed"
        }
    }
    status, _ = request(f"/api/v1/assets/{asset_id}/configurations", method="POST", payload=cfg_payload)
    assert status == 201
    results["2_asset_configuration"] = "PASS"

    # 3. Model 1.0.2 & Sustained Detector Handover
    print("3. Executing detector handover for simulator stream...")
    run_id = f"sim-{uuid4().hex[:6]}"
    handover_payload = {
        "schema_version": "incident-control-1.0.0",
        "expected_version": 0,
        "idempotency_key": str(uuid4()),
        "source": "simulator",
        "run_id": run_id,
        "configuration_version": 1,
        "model_version": "stored-reading-top-oil-1.0.2",
        "detector_version": "sustained-threshold-1.0.1",
        "policy": {
            "version": "p4-policy-v1",
            "provenance": "team_agreed",
            "max_gap_s": 600,
            "rules": [
                {
                    "name": "overload",
                    "quantity": "electrical_metrics.capacity_loading_pct",
                    "unit": "%",
                    "trigger": 120.0,
                    "recovery": 100.0,
                    "persistence_s": 120.0,
                    "recovery_s": 60.0,
                    "severity": "warning"
                }
            ]
        },
        "reason": "Phase 4 sustained overload detector activation"
    }
    status, control_resp = request(f"/api/v1/assets/{asset_id}/detector-handovers", method="POST", payload=handover_payload, token=TOKEN)
    assert status == 201, f"Handover failed ({status}): {control_resp}"
    print(f"   Detector epoch: {control_resp['detector_epoch']}")
    results["3_detector_handover"] = "PASS"

    # 4. Ingest Telemetry Triggering Overload Condition
    print("4. Ingesting telemetry readings to trigger sustained overload incident...")
    base_time = 1760000000
    for offset_s in (0, 150):
        t_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(base_time + offset_s))
        reading = {
            "schema_version": "1.0.0",
            "asset_id": asset_id,
            "message_id": str(uuid4()),
            "source": "simulator",
            "run_id": run_id,
            "configuration_version": 1,
            "timestamp": t_iso,
            "measurements": {
                "voltage_r_v": 115000.0,
                "voltage_y_v": 115000.0,
                "voltage_b_v": 115000.0,
                "current_r_a": 190.0, # High loading (~151%)
                "current_y_a": 190.0,
                "current_b_a": 190.0,
                "oil_temperature_c": 75.0,
                "ambient_temperature_c": 25.0,
                "oil_level_pct": 90.0
            },
            "measurement_quality": {}
        }
        status, _ = request("/api/v1/telemetry", method="POST", payload=reading)
        assert status == 201
    
    print("   Waiting 5 seconds for worker processing loop...")
    time.sleep(5)

    # 5. Incident Verification
    print("5. Querying incidents for stream...")
    status, inc_page = request(f"/api/v1/incidents?asset_id={asset_id}&source=simulator&run_id={run_id}", token=TOKEN)
    assert status == 200, f"Incidents failed: {inc_page}"
    assert len(inc_page["items"]) >= 1, f"Expected incident generated, got: {inc_page}"
    incident = inc_page["items"][0]
    inc_id = incident["incident_id"]
    print(f"   Found incident: {inc_id} (Category: {incident['category']}, Status: {incident['condition_status']}, Ack: {incident['acknowledgement']['status']})")
    results["4_incident_detection"] = "PASS"

    # 6. Incident Evidence & Events
    print("6. Inspecting incident evidence and events...")
    status, ev_page = request(f"/api/v1/incidents/{inc_id}/events", token=TOKEN)
    assert status == 200
    assert len(ev_page["items"]) >= 1
    print(f"   Recorded events count: {len(ev_page['items'])} (Initial: {ev_page['items'][0]['event_type']})")

    status, evidence_page = request(f"/api/v1/incidents/{inc_id}/evidence", token=TOKEN)
    assert status == 200
    assert len(evidence_page["items"]) >= 1
    print(f"   Recorded evidence count: {len(evidence_page['items'])}")
    results["5_incident_evidence_and_events"] = "PASS"

    # 7. Incident Acknowledgement
    print("7. Acknowledging incident...")
    ack_payload = {
        "schema_version": "incident-acknowledgement-1.0.0",
        "expected_version": incident["incident_version"],
        "idempotency_key": str(uuid4())
    }
    status, ack_resp = request(f"/api/v1/incidents/{inc_id}/acknowledgements", method="POST", payload=ack_payload, token=TOKEN)
    assert status == 201, f"Ack failed ({status}): {ack_resp}"
    assert ack_resp["acknowledgement"]["status"] == "acknowledged"
    print(f"   Incident acknowledged at version {ack_resp['incident_version']} by {ack_resp['acknowledgement']['actor_ref']}")
    results["6_incident_acknowledgement"] = "PASS"

    # 8. Genuine Maintenance Task Linked to Incident
    print("8. Creating genuine maintenance task linked to incident...")
    task_create_payload = {
        "alert": {
            "source": "analytics",
            "incident_id": inc_id,
            "asset_id": asset_id
        },
        "action": f"Emergency inspection for incident {inc_id[:8]}",
        "owner": "Person C Verified Operator"
    }
    status, task_resp = request("/api/v1/maintenance/tasks", method="POST", payload=task_create_payload, token=TOKEN)
    assert status in (200, 201), f"Task create failed ({status}): {task_resp}"
    task_id = task_resp["id"]
    print(f"   Created maintenance task: {task_id} (Version: {task_resp['version']}, Status: {task_resp['status']})")
    results["7_maintenance_task_creation"] = "PASS"

    # 9. Maintenance Task Lifecycle & Update
    print("9. Updating maintenance task lifecycle (to in_progress)...")
    task_update_payload = {
        "expected_version": task_resp["version"],
        "status": "in_progress",
        "owner": "Field Crew Alpha",
        "notes": "Crew dispatched to investigate overload condition."
    }
    status, updated_task = request(f"/api/v1/maintenance/tasks/{task_id}", method="PATCH", payload=task_update_payload, token=TOKEN)
    assert status == 200, f"Task update failed ({status}): {updated_task}"
    assert updated_task["status"] == "in_progress"
    assert updated_task["owner"] == "Field Crew Alpha"
    assert updated_task["version"] == task_resp["version"] + 1
    print(f"   Task updated to version {updated_task['version']} (Status: {updated_task['status']})")
    results["8_maintenance_task_lifecycle"] = "PASS"

    # 10. Maintenance History Audit Trail
    print("10. Checking maintenance task audit history...")
    status, hist_page = request(f"/api/v1/maintenance/tasks/{task_id}/history", token=TOKEN)
    assert status == 200
    assert len(hist_page["items"]) >= 1
    latest_hist = hist_page["items"][0]
    print(f"   Latest history version: {latest_hist['version']} ({latest_hist['previous_status']} -> {latest_hist['new_status']}, Actor: {latest_hist['actor']}, Source: {latest_hist['identity_source']})")
    assert latest_hist["identity_source"] == "authenticated_operator"
    results["9_maintenance_audit_history"] = "PASS"

    # 11. Live What-If Execution on Stream
    print("11. Executing live What-if scenario comparison on the stream...")
    what_if_payload = {
        "schema_version": "what-if-request-1.0.0",
        "source": "simulator",
        "run_id": run_id,
        "baseline": {
            "duration_s": 7200,
            "thermal_load_pu": 1.5,
            "ambient_temperature_c": 25.0
        },
        "reduced_load": {
            "duration_s": 7200,
            "thermal_load_pu": 0.8,
            "ambient_temperature_c": 25.0
        }
    }
    status, what_if_resp = request(f"/api/v1/assets/{asset_id}/what-if", method="POST", payload=what_if_payload)
    assert status == 200, f"What-if failed ({status}): {what_if_resp}"
    assert what_if_resp["schema_version"] == "what-if-response-1.0.0"
    b_final = what_if_resp["baseline"]["final_top_oil_temperature_c"]
    r_final = what_if_resp["reduced_load"]["final_top_oil_temperature_c"]
    diff = what_if_resp["final_temperature_difference_c"]
    print(f"   What-if results: Baseline final: {b_final:.2f} C, Reduced final: {r_final:.2f} C, Diff: {diff:.2f} C")
    print(f"   Crossing status: {what_if_resp['baseline']['limit_crossing']['status']}")
    results["10_what_if_forecasting"] = "PASS"

    print("\n=======================================================")
    print("ALL 10 VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=======================================================")
    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    run_test()
