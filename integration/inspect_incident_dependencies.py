"""Read-only local inventory for incident integration; does not certify readiness.

Run from repository root: python -m integration.inspect_incident_dependencies
Requires backend dependencies. Never connects to or migrates a database.
"""

import json
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.app import models  # noqa: F401: register all metadata
from backend.app.db.base import Base
from backend.app.main import app


def inventory():
    root = Path(__file__).resolve().parents[1]
    migrations = ScriptDirectory.from_config(Config(str(root / "backend/alembic.ini")))
    schema = app.openapi()
    operations = []
    for path, item in sorted(schema["paths"].items()):
        for method, operation in sorted(item.items()):
            if method in {"get", "post", "put", "patch", "delete", "head", "options", "trace"}:
                operations.append({
                    "method": method.upper(),
                    "path": path,
                    "declared_security": operation.get("security", schema.get("security", [])),
                })
    return {
        "scope": "Local migration graph, registered metadata and OpenAPI only; no database/network I/O",
        "migration_heads": migrations.get_heads(),
        "registered_tables": sorted(Base.metadata.tables),
        "operations": operations,
        "declared_security_schemes": sorted(schema.get("components", {}).get("securitySchemes", {})),
        "limitations": [
            "Declared routes and tables do not prove persistence or canonical mapping correctness.",
            "OpenAPI security declarations do not prove trusted identity/authorization.",
            "Contract acceptance and runtime/database/browser verification require separate review.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(inventory(), indent=2, sort_keys=True))
