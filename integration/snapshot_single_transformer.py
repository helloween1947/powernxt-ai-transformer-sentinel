"""Explicit-column hashes only, guarded to the isolated single-transformer database."""
import argparse
import hashlib
import json
from pathlib import Path
from sqlalchemy import inspect, select, text
from backend.app.db.session import engine, SessionLocal
from backend.app.models.assets import Asset
from backend.app.models.analytics import AnalyticsStream

def snapshot(output):
    assert engine.url.host == 'db' and engine.url.database == 'single_transformer_app_test'
    with SessionLocal() as db:
        assert list(db.scalars(select(Asset.asset_id))) == ['powernxt-single-transformer']
        streams = [{'asset_id':s.asset_id,'source':s.source,'run_key':s.run_key,'advances':s.advances,'watermark_reading_id':s.watermark_reading_id} for s in db.scalars(select(AnalyticsStream))]
    tables = {}
    with engine.connect() as connection:
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        metadata = inspect(connection)
        quote = engine.dialect.identifier_preparer.quote
        for table in sorted(metadata.get_table_names()):
            columns = [c['name'] for c in metadata.get_columns(table)]
            rows = connection.execute(text('SELECT ' + ', '.join(map(quote, columns)) + ' FROM ' + quote(table))).all()
            serialized = sorted(json.dumps(list(row), default=str, sort_keys=True, separators=(',', ':')) for row in rows)
            tables[table] = {'count':len(rows),'sha256':hashlib.sha256('\n'.join(serialized).encode()).hexdigest(),'columns':columns}
    result = {'tables':tables,'streams':sorted(streams,key=lambda s:s['run_key'])}
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    print('PASS guarded snapshot: '+str(len(tables))+' tables; no raw data or credentials')
if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    snapshot(parser.parse_args().output)
