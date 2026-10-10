# PowerNXT replacement backend

An independent FastAPI/SQLite backend for the existing digital-twin frontend. It does not import or modify `backend/`, `analytics/` or `integration/`.

## Run locally

Python 3.12 and Node 20.19+ (or 22.12+) are used by the checked setup.

```sh
cd teammates/backend_next
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m uvicorn powernxt.main:app --host 127.0.0.1 --port 8001
```

In another terminal:

```sh
cd teammates/frontend
npm ci
npm run dev
```

Open the frontend, select **Connected workspace**, and use **Connection settings** to set `http://127.0.0.1:8001` if an older browser preference overrides the default. Register a transformer in **Data inputs & transformer configuration**, enter its actual ratings/limits, and start a synthetic feed or upload a dataset. API documentation: `http://127.0.0.1:8001/docs`.

The first startup has no registered transformers. The form defaults are demonstration settings, not inferred nameplate values or certified protection settings. A default 1,000 kVA / 11 kV configuration uses 120% loading, 105 °C oil temperature, 60% minimum oil level, 10% current magnitude imbalance, and 0.9–1.1 pu voltage limits. Replace them for the transformer being studied.

`POWERNXT_DB` can select another SQLite path. By default data persists in ignored `data/powernxt.sqlite3`. Uploaded raw files are not written to disk by application code; normalized readings, run metadata, configuration snapshots and computed findings are stored. SQLite uses WAL and transactions. Each upload is committed atomically, and later configuration edits never rewrite previous findings.

## Live feed

A background task generates real, timestamped synthetic records at the requested interval (default two seconds). The frontend polls the selected simulator stream every two seconds. There is no WebSocket or device connection claimed. The generator is deterministic for a seed/step and couples load to a first-order oil-temperature response; ambient conditions vary gradually. Synthetic scenarios include normal operation, overload, overheating, low oil, current imbalance and undervoltage. Start, stop, resume and scenario-change controls are supported. Runs and their sequence counters persist across restart; downtime is not filled with invented measurements. Maximum ten simultaneously running feeds.

Generated, uploaded and device measurements are isolated as `simulator`, `file_replay` and `device` streams. Non-device streams require a run ID and enforce asset/source binding.

## Dataset uploads

- UTF-8 CSV or XLSX, maximum 10 MiB and 20,000 physical data rows; request bodies are capped at 11 MiB.
- Use one transformer per upload. XLSX worksheet selection and column preview are supported.
- Map a time column and at least one measurement column. Unmapped/empty channels remain missing; genuine zero is retained.
- Canonical channels: `voltage_r_v`, `voltage_y_v`, `voltage_b_v`, `current_r_a`, `current_y_a`, `current_b_a`, `oil_temperature_c`, `ambient_temperature_c`, `oil_level_pct`.
- Voltage is line-to-line volts on the configured measurement side; current is amperes, temperatures Celsius, oil level percent. The importer does not infer units or fabricate missing phases.
- ISO timestamps with offsets are preferred. Naive timestamps and Excel datetime cells use the explicitly selected timezone. Ambiguous/nonexistent DST times need an offset. No fabricated timestamps, future measurements or duplicate measurement times are accepted.
- Invalid values, nonfinite numbers, negative magnitude channels, unsupported formats and malformed files reject the whole import. The error identifies the invalid row. XLSX formulas are never executed; missing formula caches remain missing.
- Compressed XLSX expansion is limited to 50 MiB / 1,000 archive members and 100 worksheet columns.

`examples/transformer-readings.csv` has six deliberately constructed rows: normal operation plus one example of each of the five injected conditions. This is a test dataset, not a measured transformer history. Importing it with default settings produces five configured-limit findings.

Counts cover the **entire uploaded dataset**, not just the newest history page. The API summary retains at most 200 preview findings; the UI displays 20, with explicit totals. Paginated reading-bound checks remain available through telemetry analytics and `/faults`.

## Detection method

The first version performs explicit configured-condition checks: capacity overload, measured oil overheating, low oil, current-magnitude imbalance, and each phase's under/overvoltage. Every finding records its quantity, value, threshold, relation, reading time, configuration version and inspection explanation. Missing inputs produce unavailable checks, not a healthy zero.

Apparent power uses `sqrt(3) × mean(line voltages) × mean(line currents) / 1000`, a balanced approximation. Current imbalance is maximum deviation from mean current as a percentage of the mean; without phase angles this is not a negative-sequence calculation. The oil estimate is a first-order response from the previous observed oil value toward `ambient + rated_rise × load^1.6`. The first reading, non-forward time or a configuration change leaves that estimate unavailable. Estimated temperature never substitutes for measured temperature in the overheating check.

These are observed-condition findings. They do not establish insulation breakdown, short-circuit root cause, fault probability, remaining life or a validated transformer health index. Training such a model requires appropriate labelled/reference evidence. The existing frontend condition rating remains its documented rule-based prototype, and is separate from individual breaches.

## API and structure

- `powernxt/schemas.py`: validated input models and canonical units.
- `powernxt/store.py`: SQLite storage, stream queries, immutable per-reading snapshots and atomic imports.
- `powernxt/engine.py`: pure calculations and explainable checks.
- `powernxt/datasets.py`: bounded CSV/XLSX parsing and column preview.
- `powernxt/simulator.py`: seeded synthetic generation.
- `powernxt/api.py`: route composition and simulation lifecycle.

Implemented route families: transformer registration/configuration; device ingestion; latest and paginated telemetry; reading and latest analytics; simulator start/control; saved runs; dataset preview/import; reading-bound fault reports; health and OpenAPI.

The telemetry/analytics wire schemas match the existing frontend. All API source/run, time, reading, asset, configuration and model identities are preserved. Old backend routes, asynchronous workers, a broker, Redis and a separate database service are not required for this local implementation.

## Tests

```sh
cd teammates/backend_next
.venv/bin/python -m pytest tests -q -o pythonpath=.
cd ../frontend
npm test
npm run lint
npm run build
```

See [verification](VERIFICATION.md) for the executed checks. This service currently binds to localhost and has no authentication/authorization, incident acknowledgement or maintenance lifecycle. It is ready for local development and dataset experimentation; production deployment and scientific validation remain separate work.
