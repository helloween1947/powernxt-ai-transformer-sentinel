"""Server-admin provisioning only; tokens are never accepted as asserted actor IDs.

python -m backend.app.operators issue --name alice --role operator --token-file <private new file>
python -m backend.app.operators revoke --name alice
"""

import argparse
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models.incidents import Operator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    issue = commands.add_parser("issue")
    issue.add_argument("--name", required=True)
    issue.add_argument("--role", choices=["reader", "operator", "admin"], required=True)
    issue.add_argument("--hours", type=int, default=8)
    issue.add_argument("--token-file", required=True)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("--name", required=True)
    args = parser.parse_args()
    if (
        not args.name.strip()
        or len(args.name) > 100
        or any(ord(c) < 32 for c in args.name)
    ):
        parser.error("Nonblank operator name of at most 100 characters required")
    if args.command == "issue" and not 1 <= args.hours <= 24:
        parser.error("Credential lifetime must be 1–24 hours")
    with SessionLocal.begin() as db:
        actor = db.scalar(
            select(Operator).where(Operator.name == args.name.strip()).with_for_update()
        )
        if args.command == "revoke":
            if actor is None:
                parser.error("Operator not found")
            actor.active = False
        else:
            # Exclusive creation: never overwrite an existing private credential file.
            descriptor = os.open(
                args.token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            token = secrets.token_urlsafe(32)
            try:
                with os.fdopen(descriptor, "w") as output:
                    output.write(token + "\n")
                if actor is None:
                    actor = Operator(id=uuid4(), name=args.name.strip())
                    db.add(actor)
                actor.role, actor.active = args.role, True
                actor.token_hash = hashlib.sha256(token.encode()).hexdigest()
                actor.expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=args.hours
                )
                db.flush()
            except Exception:
                os.unlink(args.token_file)
                raise
    print(
        "Credential issued to private file"
        if args.command == "issue"
        else "Credential revoked"
    )


if __name__ == "__main__":
    main()
