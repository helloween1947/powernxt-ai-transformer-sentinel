# Telemetry Ingestion Contract

**Status**: Baseline Specification (Managed by Person A)  
**Consumer**: Person B (Analytics), Person C (Frontend), Person D (Integration)

## 1. Overview
This specification defines the JSON schema for time-series transformer telemetry dispatched from sensor edge devices, file playback systems, or synthetic simulators into the ingestion pipeline.

## 2. Core Schema Fields

| Field Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `schema_version` | string | Yes | Semantic version of this payload schema (e.g., `"1.0.0"`). |
| `message_id` | string (UUIDv4) | Yes | Unique identifier for message delivery and deduplication. |
| `asset_id` | string | Yes | Unique transformer asset identifier (e.g., `"XFR-SUB04-TX01"`). |
| `timestamp` | string (ISO 8601) | Yes | Timezone-aware UTC timestamp (e.g., `"2026-10-07T10:45:00.000Z"`). |
| `source` | string (enum) | Yes | Telemetry origin: `"simulator"`, `"file_replay"`, or `"device"`. |
| `run_id` | string or null | Optional | Session/simulation run identifier, required when source is `"simulator"` or `"file_replay"`. |
| `measurements` | object | Yes | Physical sensor measurements with explicit units (detailed below). |

## 3. Measurements Object & Explicit Units

| Measurement Key | Type | Unit | Nullable | Description |
| :--- | :--- | :--- | :--- | :--- |
| `voltage_r_v` | float | Volts (V) | Yes | Phase R line voltage |
| `voltage_y_v` | float | Volts (V) | Yes | Phase Y line voltage |
| `voltage_b_v` | float | Volts (V) | Yes | Phase B line voltage |
| `current_r_a` | float | Amperes (A) | Yes | Phase R line current |
| `current_y_a` | float | Amperes (A) | Yes | Phase Y line current |
| `current_b_a` | float | Amperes (A) | Yes | Phase B line current |
| `oil_temperature_c` | float | Celsius (°C) | Yes | Top-oil temperature sensor |
| `ambient_temperature_c`| float | Celsius (°C) | Yes | Ambient external air temperature |
| `oil_level_pct` | float | Percent (%) | Yes | Transformer oil conservator level (0.0 - 100.0%) |

## 4. Architectural Rules & Constraints

1. **Missing Measurements**: Any sensor dropout or unequipped channel MUST use JSON `null`, never default to `0.0`.
2. **Voltage Convention**: Whether voltages are line-to-line ($V_{LL}$) or line-to-neutral ($V_{LN}$) belongs in the **Asset Registry Configuration**, not within high-frequency streaming packets.
3. **Simulated Values**: Example numbers provided in sample datasets and test generators represent synthetic simulations, NOT manufacturer-certified operational limits.
4. **Message Deduplication Scope**: Ingestion pipelines enforce message deduplication within a 24-hour sliding window based on the composite key `(asset_id, message_id)`. Re-transmissions of identical `message_id` within the window are acknowledged but not stored twice.
5. **Separation of Fault Ground Truth**: Simulator evaluation may tag scenario runs with ground-truth anomalies (e.g., inter-turn fault, cooling pump failure). **These ground-truth labels MUST be stored out-of-band** in benchmarking metadata and MUST NEVER be injected into this telemetry stream, preserving true blind detection for Person B's analytical models.
