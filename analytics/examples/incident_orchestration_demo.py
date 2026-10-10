"""Execute synthetic storage-command examples; no registry/API/database writes."""
import json
from pathlib import Path

from analytics import evaluate_incident_candidates


def main():
    root = Path(__file__).resolve().parents[2]
    source = json.loads((root/"analytics/examples/persistent-rules-test-example.json").read_text())
    context, commands = None, []
    epoch = "50000000-0000-4000-8000-000000000001"
    for index, frame in enumerate(source["frames"]):
        result_id = 10001+index
        output = evaluate_incident_candidates(frame["analytics_result"], source["policy"],
                     detector_epoch=epoch, result_id=result_id, previous_context=context)
        context = output["updated_context"]
        commands.extend(output["mutations"])
    example = {"schema_version": "incident-storage-commands-1.0.0",
               "origin": "Executed synthetic module example; result IDs/epoch are illustrative, unpersisted identities, not a backend response or canonical incidents.",
               "source_fixture": "persistent-rules-test-example.json", "mutations": commands}
    destination = root/"analytics/examples/incident-storage-commands-test-example.json"
    destination.write_text(json.dumps(example, indent=2, allow_nan=False)+"\n")
    print(f"Wrote {len(commands)} synthetic opening/update/recovery commands; no canonical IDs allocated.")


if __name__ == "__main__":
    main()
