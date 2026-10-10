"""Expire/revoke ONLY the isolated verifier's own reader/operator credentials."""
import argparse
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from backend.app.models.incidents import Operator

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--database-url', required=True)
parser.add_argument('--action', choices=['reader-expires-soon', 'operator-revoke'], required=True)
args = parser.parse_args()
url = make_url(args.database_url)
assert url.host == '127.0.0.1' and url.database.startswith('persond_review_') and url.database.endswith('_test')
engine = create_engine(args.database_url)
with Session(engine) as db, db.begin():
    name = 'd-app-reader' if args.action == 'reader-expires-soon' else 'd-app-operator'
    actor = db.scalar(select(Operator).where(Operator.name == name).with_for_update())
    assert actor is not None
    if args.action == 'reader-expires-soon':
        actor.expires_at = datetime.now(timezone.utc) + timedelta(seconds=8)
    else:
        actor.active = False
engine.dispose()
print('PASS isolated owned credential state changed; no credential printed')
