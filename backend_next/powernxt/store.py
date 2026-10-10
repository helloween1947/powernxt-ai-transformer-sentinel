"""SQLite persistence. Each import and its analytics commit as one transaction."""
import json
import math
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .engine import result_for

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def configuration(data, version, asset_id):
    data = dict(data)
    data.update(version=version, asset_id=asset_id, rated_current_a=data['rated_kva']*1000/(math.sqrt(3)*data['rated_voltage_v']),
                voltage_convention='line_to_line', measurement_side='primary', cooling_type='ONAN', created_at=utc_now())
    data['parameter_provenance'] = {**{key: 'operator_configured' for key in ['rated_kva', 'rated_voltage_v', 'rated_current_a']},
        **{f'operational_limits.{key}': 'operator_configured' for key in data['operational_limits']}}
    return data

class Store:
    def __init__(self, path):
        if str(path) != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.db.executescript('''
            PRAGMA foreign_keys=ON;
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS readings(id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL REFERENCES assets(id), source TEXT NOT NULL, run TEXT NOT NULL,
                message TEXT NOT NULL, time TEXT NOT NULL, payload TEXT NOT NULL, analytics TEXT NOT NULL,
                UNIQUE(asset,source,run,message));
            CREATE INDEX IF NOT EXISTS reading_stream ON readings(asset,source,run,time DESC,id DESC);
        ''')

    def close(self):
        with self.lock:
            self.db.close()

    def assets(self, limit, offset):
        with self.lock:
            return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM assets ORDER BY id LIMIT ? OFFSET ?', (limit, offset))]

    def asset(self, asset_id):
        with self.lock:
            row = self.db.execute('SELECT payload FROM assets WHERE id=?', (asset_id,)).fetchone()
            if row is None:
                raise KeyError('Transformer not found.')
            return json.loads(row[0])

    def create_asset(self, data):
        asset_id = data['asset_id']
        asset = {key: data[key] for key in ['asset_id', 'name', 'location', 'timezone']}
        asset['current_configuration'] = configuration(data['configuration'], 1, asset_id)
        with self.lock, self.db:
            self.db.execute('INSERT INTO assets VALUES (?,?)', (asset_id, json.dumps(asset)))
        return asset

    def configure(self, asset_id, data):
        with self.lock, self.db:
            asset = self.asset(asset_id)
            asset['current_configuration'] = configuration(data, asset['current_configuration']['version'] + 1, asset_id)
            self.db.execute('UPDATE assets SET payload=? WHERE id=?', (json.dumps(asset), asset_id))
            return asset

    def runs(self, asset_id=None):
        with self.lock:
            runs = [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM runs ORDER BY rowid DESC')]
            return [r for r in runs if asset_id is None or r['asset_id'] == asset_id]

    def run(self, run_id):
        with self.lock:
            row = self.db.execute('SELECT payload FROM runs WHERE id=?', (run_id,)).fetchone()
            if row is None:
                raise KeyError('Run not found.')
            return json.loads(row[0])

    def save_run(self, run):
        with self.lock, self.db:
            self.db.execute('INSERT INTO runs VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (run['run_id'], json.dumps(run)))
        return run

    def history(self, asset_id, source, run_id, limit=20, offset=0, start=None, end=None):
        self.asset(asset_id)
        query = 'SELECT payload FROM readings WHERE asset=? AND source=? AND run=?'
        args = [asset_id, source, run_id or '']
        for op, value in [('>=', start), ('<', end)]:
            if value is not None:
                query += f' AND time {op} ?'
                args.append(value)
        query += ' ORDER BY time DESC,id DESC LIMIT ? OFFSET ?'
        with self.lock:
            return [json.loads(row[0]) for row in self.db.execute(query, [*args, limit, offset])]

    def analytics(self, reading_id):
        with self.lock:
            row = self.db.execute('SELECT analytics FROM readings WHERE id=?', (reading_id,)).fetchone()
            if row is None:
                raise KeyError('Reading not found.')
            return json.loads(row[0])

    def append(self, asset_id, source, run_id, rows, new_run=None):
        """Validate before entry; write readings, configuration snapshots, results atomically."""
        with self.lock, self.db:
            config = self.asset(asset_id)['current_configuration']
            if new_run:
                self.db.execute('INSERT INTO runs VALUES (?,?)', (new_run['run_id'], json.dumps(new_run)))
            previous_rows = self.history(asset_id, source, run_id, limit=1)
            previous = previous_rows[0] if previous_rows else None
            output = []
            for row in rows:
                normalized = {'schema_version': '1.0.0', 'asset_id': asset_id, 'source': source, 'run_id': run_id,
                    'configuration_version': config['version'], 'message_id': row.get('message_id') or str(uuid.uuid4()),
                    'timestamp': row['timestamp'], 'measurements': row['measurements'],
                    'measurement_quality': {key: 'missing' if value is None else 'good' for key, value in row['measurements'].items()}}
                cur = self.db.execute('INSERT INTO readings(asset,source,run,message,time,payload,analytics) VALUES (?,?,?,?,?,?,?)',
                    (asset_id, source, run_id or '', normalized['message_id'], row['timestamp'], '{}', '{}'))
                reading = {'id': cur.lastrowid, 'asset_id': asset_id, 'source': source, 'run_id': run_id,
                    'message_id': normalized['message_id'], 'measurement_time': row['timestamp'], 'arrival_time': utc_now(),
                    'configuration_version': config['version'], 'configuration': config,
                    'normalized_telemetry': normalized, 'analytics_status': 'completed',
                    'quality_flags': {key: ['missing'] for key, value in row['measurements'].items() if value is None},
                    'out_of_order': previous is not None and row['timestamp'] <= previous['measurement_time']}
                compatible = previous if previous and previous['configuration_version'] == config['version'] else None
                result = result_for(reading, config, compatible)
                self.db.execute('UPDATE readings SET payload=?,analytics=? WHERE id=?', (json.dumps(reading), json.dumps(result), reading['id']))
                output.append(reading)
                if not reading['out_of_order']:
                    previous = reading
            return output
