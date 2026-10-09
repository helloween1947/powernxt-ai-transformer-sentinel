"""Live sample-task smoke check; --task-id checks an earlier task after restart."""

import argparse
import json
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--task-id", help="Only retrieve this previously created task")
    args = parser.parse_args()
    fixture = json.loads((Path(__file__).parent / "fixtures/sample-maintenance-task.json").read_text())
    root = "/api/v1/maintenance/tasks"
    with httpx.Client(base_url=args.base_url, timeout=10) as client:
        if args.task_id:
            response = client.get(f"{root}/{args.task_id}")
            response.raise_for_status()
            assert response.json()["alert"] == fixture["alert"]
            assert response.json()["action"] == fixture["action"]
            print("PASS: previously saved sample task retrieved.")
            print(json.dumps(response.json(), indent=2))
            return
        asset_id = fixture["alert"]["asset_id"]
        asset = client.get(f"/api/v1/assets/{asset_id}")
        if asset.status_code == 404:
            asset = client.post("/api/v1/assets", json={
                "asset_id": asset_id, "name": "Person D sample transformer",
                "location": "Demonstration only", "timezone": "Asia/Kolkata",
            })
        asset.raise_for_status()
        response = client.post(root, json=fixture)
        response.raise_for_status()
        assert response.status_code in (200, 201)
        task = response.json()
        assert task["alert"] == fixture["alert"] and task["status"] == "open"
        fetched = client.get(f"{root}/{task['id']}")
        fetched.raise_for_status()
        assert fetched.json() == task
        retry = client.post(root, json=fixture)
        assert retry.status_code == 200 and retry.json() == task
        page = client.get(root, params={"asset_id": asset_id})
        page.raise_for_status()
        assert any(item["id"] == task["id"] for item in page.json()["items"])
        print("PASS: create/retry, retrieve, and asset-filtered list.")
        print(json.dumps(task, indent=2))
        print(f"After restarting the backend, run again with --task-id {task['id']}")


if __name__ == "__main__":
    main()
