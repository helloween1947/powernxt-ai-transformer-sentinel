"""Functional API and restart-persistence check; run from the repository root.

Creates only a uniquely labelled demonstration asset, using assumed parameters.
Uses Python's standard library and normal Compose restart; never removes volumes.
"""

import argparse
import json
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def verify(base_url: str) -> None:
    def request(path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = Request(
            base_url.rstrip("/") + path,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=5) as response:
            result = json.load(response)
            if payload is not None and response.status != 201:
                raise RuntimeError("Creation did not return HTTP 201")
            return result

    def wait_ready():
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                ready = request("/health/ready")
                if ready["status"] == "ready" and ready["database"] == "connected":
                    return
            except (URLError, TimeoutError, ConnectionError):
                pass
            time.sleep(1)
        raise RuntimeError("Backend did not become ready within 60 seconds")

    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    wait_ready()
    require(request("/health/live")["status"] == "live", "Liveness failed")
    asset_id = "demo-registry-" + uuid4().hex
    asset = {
        "asset_id": asset_id,
        "name": "DEMONSTRATION - assumed transformer",
        "location": "Demo lab",
        "timezone": "Asia/Kolkata",
    }
    created = request("/api/v1/assets", asset)
    require(
        created["current_configuration"] is None,
        "New asset unexpectedly has a configuration",
    )
    path = "/api/v1/assets/" + asset_id
    repo = Path(__file__).resolve().parents[1]
    configuration = json.loads(
        (repo / "data/sample/asset-configuration-assumed.json").read_text()
    )
    first = request(path + "/configurations", configuration)
    require(first["version"] == 1, "Expected version 1")
    require(
        request(path)["current_configuration"] == first, "Version 1 retrieval failed"
    )
    configuration["operational_limits"]["max_load_pct"] = 110
    second = request(path + "/configurations", configuration)
    require(second["version"] == 2, "Expected version 2")
    before = request(path + "/configurations")["items"]
    require(before == [first, second], "Version history was not preserved")
    subprocess.run(
        ["docker", "compose", "restart", "db", "backend"], cwd=repo, check=True
    )
    wait_ready()
    require(
        request("/health/live")["status"] == "live", "Liveness failed after restart"
    )
    require(
        request(path)["current_configuration"] == second,
        "Current configuration did not persist",
    )
    require(
        request(path + "/configurations")["items"] == before,
        "History changed after restart",
    )
    print(
        f"PASS: asset {asset_id}; versions 1 and 2 preserved across backend/database restart"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    verify(parser.parse_args().base_url)
