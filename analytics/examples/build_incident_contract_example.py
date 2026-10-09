"""Build PROPOSED storage snapshots from executed synthetic B detector evidence.

No persistence or API; UUID/result IDs below are labelled illustrative references.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detector-example", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = json.loads(Path(args.detector_example).read_text())
    states, accumulated = [], []
    opening = source["frames"][3]["detector_result"]["events"][0]
    key = opening["incident_id"]
    for index, kind in ((3, "opened"), (4, "updated"), (6, "recovered")):
        frame = source["frames"][index]
        analytic, detector = frame["analytics_result"], frame["detector_result"]
        meta, thermal = analytic["metadata"], analytic["thermal_assessment"]
        rule = detector["evidence"][0]
        versions = {k: meta[k] for k in ("model_id", "model_version", "result_schema_version", "parameter_version", "configuration_version")}
        binding = detector["updated_state"]["binding"]
        versions.update({k: binding[k] for k in ("detector_version", "policy_version", "policy_fingerprint")})
        accumulated.append({"reading_id": meta["reading_identity"]["reading_id"], "result_id": 1000+index,
                            "message_id": meta["reading_identity"]["message_id"], "measurement_time": meta["measurement_time"],
                            "observation_kind": kind,
                            "temperatures": {k: thermal[k] for k in ("measured_top_oil_temperature_c", "predicted_top_oil_temperature_c", "thermal_residual_c")},
                            "temperature_unit": "C", "rule_evidence": {**{k: rule[k] for k in ("quantity", "value", "unit", "trigger", "recovery", "available", "reasons", "continuity")},
                                                                         "persistence_required_s": opening["persistence_required_s"], "recovery_required_s": opening["recovery_required_s"]},
                            "data_confidence": analytic["data_confidence"], "versions": versions,
                            "parameter_provenance": meta["parameter_provenance"], "policy_provenance": detector["policy_provenance"],
                            "quality_availability": analytic["execution_status"]["availability"]})
        states.append({"schema_version": "incident-proposal-1.0.0", "incident_id": "10000000-0000-4000-8000-000000000001",
                       "incident_version": len(states)+1, "severity": opening["severity"],
                       "asset_id": meta["stream"]["asset_id"], "source": "analytics", "measurement_source": meta["stream"]["source"], "run_id": meta["stream"]["run_id"],
                       "category": opening["category"], "detector_epoch": "20000000-0000-4000-8000-000000000001", "detector_episode_key": key,
                       "condition_status": "recovered" if kind == "recovered" else "active", "opened_at": opening["evidence"]["measurement_time"],
                       "recovered_at": meta["measurement_time"] if kind == "recovered" else None,
                       "last_evaluated_measurement_time": meta["measurement_time"], "last_evidence_status": "available",
                       "acknowledgement": {"status": "unacknowledged", "acknowledged_at": None, "actor_ref": None},
                       "evidence": deepcopy(accumulated)})
    output = {"contract_status": "PROPOSED; no incident API/persistence exists",
              "origin": "Values copied from actual synthetic detector execution at B564b174; UUIDs/result IDs are illustrative unpersisted references, not genuine incidents.",
              "task_status_example": "completed", "incident_snapshots": states}
    Path(args.output).write_text(json.dumps(output, indent=2, allow_nan=False)+"\n")
    print("Wrote proposed opened/update/recovery snapshots sharing one canonical incident UUID.")


if __name__ == "__main__":
    main()
