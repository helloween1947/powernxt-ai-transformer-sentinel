"""Hash explicit columns of every table in an owned review database; no raw data."""
import argparse
import hashlib
import json
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

def snapshot(url, output):
    parsed = make_url(url)
    assert parsed.host == '127.0.0.1' and parsed.database.startswith('persond_review_') and parsed.database.endswith('_test')
    engine = create_engine(url)
    result = {}
    with engine.connect() as connection:
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        metadata = inspect(connection)
        quote = engine.dialect.identifier_preparer.quote
        for table in sorted(metadata.get_table_names()):
            columns = [c['name'] for c in metadata.get_columns(table)]
            rows = connection.execute(text('SELECT ' + ', '.join(map(quote, columns)) + ' FROM ' + quote(table))).all()
            serialized = sorted(json.dumps(list(row), default=str, sort_keys=True, separators=(',', ':')) for row in rows)
            result[table] = {'count': len(rows), 'columns': columns, 'sha256': hashlib.sha256('\n'.join(serialized).encode()).hexdigest()}
    engine.dispose()
    Path(output).write_text(json.dumps(result, indent=2) + '\n')
    print('PASS explicit-column snapshots: ' + str(len(result)) + ' tables; no raw data exported')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database-url', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    snapshot(args.database_url, args.output)
