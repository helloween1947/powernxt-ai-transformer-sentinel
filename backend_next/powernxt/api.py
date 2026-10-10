"""FastAPI application factory and bounded live simulation lifecycle."""
import asyncio
import json
import logging
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from .datasets import DatasetError, MAX_BYTES, MAX_ROWS, dataset_headers, parse_dataset
from .schemas import AssetCreate, Configuration, DeviceReading, RunCreate, RunUpdate
from .simulator import generate
from .store import Store, utc_now

Source = Literal['device', 'simulator', 'file_replay']

class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        received = 0
        async def bounded_receive():
            nonlocal received
            message = await receive()
            received += len(message.get('body', b''))
            if received > MAX_BYTES + 1024 * 1024:
                raise HTTPException(413, 'Request exceeds 11 MiB.')
            return message
        await self.app(scope, bounded_receive if scope['type'] == 'http' else receive, send)


class Service:
    def __init__(self, store):
        self.store = store
        self.simulator_error = None

    def tick(self, run, now=None):
        now = now or datetime.now(timezone.utc)
        with self.store.lock:
            latest = self.store.history(run['asset_id'], 'simulator', run['run_id'], limit=1)
            if latest and (now - datetime.fromisoformat(latest[0]['measurement_time'])).total_seconds() < run['interval_seconds']:
                return
            cfg = self.store.asset(run['asset_id'])['current_configuration']
            previous = latest[0]['normalized_telemetry']['measurements'] if latest else None
            measurements = generate(cfg, run['scenario'], run['seed'], run['step'], run['interval_seconds'], previous)
            self.store.append(run['asset_id'], 'simulator', run['run_id'], [{'timestamp': now.isoformat(), 'measurements': measurements}])
            run['step'] += 1
            self.store.save_run(run)

    async def loop(self):
        while True:
            try:
                for run in self.store.runs():
                    if run['source'] == 'simulator' and run['status'] == 'running':
                        self.tick(run)
                self.simulator_error = None
            except Exception as exc:
                # Surface failure on health; keep serving stored readings.
                self.simulator_error = type(exc).__name__
                logging.getLogger(__name__).exception('Synthetic feed generation failed')
            await asyncio.sleep(.25)

def create_app(db_path=None, background=True):
    store = Store(db_path or os.getenv('POWERNXT_DB', str(Path(__file__).resolve().parents[1] / 'data' / 'powernxt.sqlite3')))
    service = Service(store)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(service.loop()) if background else None
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        store.close()

    app = FastAPI(title='PowerNXT Digital Twin', version='1.0.0', lifespan=lifespan)
    app.state.store, app.state.service = store, service
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
                       allow_methods=['GET', 'POST', 'PUT', 'PATCH'], allow_headers=['Content-Type'])

    @app.middleware('http')
    async def bounded_request(request, call_next):
        try:
            size = int(request.headers.get('content-length', '0'))
        except ValueError:
            return JSONResponse({'detail': 'Invalid content length.'}, status_code=400)
        if size > MAX_BYTES + 1024 * 1024:
            return JSONResponse({'detail': 'Request exceeds 11 MiB.'}, status_code=413)
        return await call_next(request)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({'detail': str(exc.args[0])}, status_code=404)

    @app.exception_handler(sqlite3.IntegrityError)
    async def conflict(request, exc):
        return JSONResponse({'detail': 'Duplicate identity or invalid referenced asset.'}, status_code=409)

    def stream(source, run_id):
        if source == 'device' and run_id is not None:
            raise HTTPException(422, 'Device data must not include a run ID.')
        if source != 'device' and not run_id:
            raise HTTPException(422, 'Synthetic/replay streams require a run ID.')
        if source != 'device':
            run = store.run(run_id)
            if run['source'] != source:
                raise HTTPException(422, 'Run source does not match the requested stream.')
        return run_id

    def selected_run(asset_id, source, run_id):
        stream(source, run_id)
        if source != 'device' and store.run(run_id)['asset_id'] != asset_id:
            raise HTTPException(422, 'Run belongs to another transformer.')

    def iso(value):
        if value is None:
            return None
        if value.tzinfo is None:
            raise HTTPException(422, 'Date filters must include a timezone.')
        return value.astimezone(timezone.utc).isoformat()

    @app.get('/health')
    def health():
        return {'status': 'degraded' if service.simulator_error else 'ok', 'simulator_error': service.simulator_error}

    @app.get('/api/v1/assets')
    def assets(limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0):
        return {'items': store.assets(limit, offset), 'limit': limit, 'offset': offset}

    @app.post('/api/v1/assets', status_code=201)
    def create_asset(data: AssetCreate):
        try:
            ZoneInfo(data.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise HTTPException(422, 'Unknown asset timezone.')
        return store.create_asset(data.model_dump())

    @app.get('/api/v1/assets/{asset_id}')
    def asset(asset_id: str):
        return store.asset(asset_id)

    @app.put('/api/v1/assets/{asset_id}/configuration')
    def configure(asset_id: str, data: Configuration):
        return store.configure(asset_id, data.model_dump())

    @app.post('/api/v1/assets/{asset_id}/telemetry', status_code=201)
    def ingest(asset_id: str, data: DeviceReading):
        if data.timestamp > datetime.now(timezone.utc):
            raise HTTPException(422, 'Future device measurements are not accepted.')
        return store.append(asset_id, 'device', None, [{'message_id': data.message_id,
            'timestamp': data.timestamp.astimezone(timezone.utc).isoformat(), 'measurements': data.measurements.model_dump()}])[0]

    @app.get('/api/v1/assets/{asset_id}/telemetry')
    def history(asset_id: str, source: Source = 'device', run_id: str | None = None,
                limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0,
                start: datetime | None = None, end: datetime | None = None):
        selected_run(asset_id, source, run_id)
        start, end = iso(start), iso(end)
        if start and end and start >= end:
            raise HTTPException(422, 'Start must be earlier than end.')
        return {'items': store.history(asset_id, source, run_id, limit, offset, start, end), 'limit': limit, 'offset': offset}

    @app.get('/api/v1/assets/{asset_id}/telemetry/latest')
    def latest(asset_id: str, source: Source = 'device', run_id: str | None = None):
        selected_run(asset_id, source, run_id)
        items = store.history(asset_id, source, run_id, limit=1)
        if not items:
            raise HTTPException(404, 'No measurements in the selected stream.')
        return items[0]

    @app.get('/api/v1/telemetry/{reading_id}/analytics')
    def analytics(reading_id: int):
        return store.analytics(reading_id)

    @app.get('/api/v1/assets/{asset_id}/analytics/latest')
    def latest_analytics(asset_id: str, source: Source = 'device', run_id: str | None = None):
        reading = latest(asset_id, source, run_id)
        result = store.analytics(reading['id'])['result']
        return {'schema_version': '1.0.0', 'asset_id': asset_id, 'source': source, 'run_id': run_id,
            'latest_telemetry_reading_id': reading['id'], 'latest_telemetry_status': 'completed',
            'latest_telemetry_measurement_time': reading['measurement_time'],
            'latest_completed_reading_id': reading['id'], 'latest_completed_measurement_time': reading['measurement_time'], 'result': result}

    @app.get('/api/v1/runs')
    def runs(asset_id: str | None = None):
        return {'items': store.runs(asset_id)}

    @app.post('/api/v1/simulator/runs', status_code=201)
    def start_run(data: RunCreate):
        store.asset(data.asset_id)
        run = {'run_id': str(uuid.uuid4()), **data.model_dump(), 'source': 'simulator', 'status': 'running', 'step': 0, 'created_at': utc_now()}
        if sum(r['status'] == 'running' and r['source'] == 'simulator' for r in store.runs()) >= 10:
            raise HTTPException(409, 'Stop a running simulator before starting another (maximum 10).')
        store.save_run(run)
        service.tick(run)
        return run

    @app.patch('/api/v1/simulator/runs/{run_id}')
    def change_run(run_id: str, data: RunUpdate):
        with store.lock:
            run = store.run(run_id)
            if run['source'] != 'simulator':
                raise HTTPException(422, 'Uploaded datasets cannot be controlled as simulators.')
            run.update(data.model_dump(exclude_none=True))
            return store.save_run(run)

    @app.post('/api/v1/assets/{asset_id}/datasets/preview')
    async def preview(asset_id: str, file: Annotated[UploadFile, File()], sheet: Annotated[str | None, Form()] = None):
        store.asset(asset_id)
        data = await file.read(MAX_BYTES + 1)
        try:
            return await asyncio.to_thread(dataset_headers, data, file.filename or '', sheet)
        except DatasetError as exc:
            raise HTTPException(422, str(exc))
        finally:
            await file.close()

    @app.post('/api/v1/assets/{asset_id}/datasets', status_code=201)
    async def upload(asset_id: str, file: Annotated[UploadFile, File()],
                     column_map: Annotated[str, Form()] = '{}',
                     timezone_name: Annotated[str, Form()] = 'UTC', sheet: Annotated[str | None, Form()] = None):
        store.asset(asset_id)
        try:
            mapping = json.loads(column_map)
        except (ValueError, TypeError):
            raise HTTPException(422, 'Column mapping is not valid JSON.')
        data = await file.read(MAX_BYTES + 1)
        try:
            rows = await asyncio.to_thread(parse_dataset, data, file.filename or '', mapping, timezone_name, sheet)
        except DatasetError as exc:
            raise HTTPException(422, str(exc))
        finally:
            await file.close()
        run = {'run_id': str(uuid.uuid4()), 'asset_id': asset_id, 'source': 'file_replay', 'status': 'completed',
               'filename': Path(file.filename or '').name, 'created_at': utc_now(), 'row_count': len(rows)}
        await asyncio.to_thread(store.append, asset_id, 'file_replay', run['run_id'], rows, run)
        return {**run, 'analysis': report(asset_id, 'file_replay', run['run_id'], summary=True)}

    @app.get('/api/v1/assets/{asset_id}/faults')
    def report(asset_id: str, source: Source = 'device', run_id: str | None = None,
               limit: Annotated[int, Query(ge=1, le=100)] = 100, offset: Annotated[int, Query(ge=0)] = 0, summary: bool = False):
        selected_run(asset_id, source, run_id)
        readings = store.history(asset_id, source, run_id, MAX_ROWS if summary else limit, 0 if summary else offset)
        findings = []
        counts = {}
        total_findings = 0
        unavailable_checks = 0
        for reading in readings:
            for observation in store.analytics(reading['id'])['result']['payload']['anomaly_observations']:
                unavailable_checks += observation['status'] == 'unavailable'
                if observation['breached']:
                    code = observation['code']
                    counts[code] = counts.get(code, 0) + 1
                    total_findings += 1
                    if summary and len(findings) >= 200:
                        continue
                    findings.append({**observation, 'reading_id': reading['id'], 'measurement_time': reading['measurement_time'],
                                     'configuration_version': reading['configuration_version'], 'severity': 'warning'})
        return {'asset_id': asset_id, 'source': source, 'run_id': run_id, 'items': findings,
                'readings_analyzed': len(readings), 'unavailable_checks': unavailable_checks, 'limit': limit, 'offset': offset,
                'method': 'configured_condition_checks', 'scope': 'first_20000_readings' if summary and source != 'file_replay' else 'entire_dataset' if summary else 'retrieved_page',
                'total_findings': total_findings, 'counts': counts, 'preview_truncated': total_findings > len(findings)}

    return app
