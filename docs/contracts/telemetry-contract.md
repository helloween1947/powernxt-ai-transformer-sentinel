# Telemetry Ingestion Contract

**Status**: Implemented ingestion schema `1.0.0`; analytics adapter decisions require Person B review.
**Owner**: Person A. **Consumers**: Person B (Analytics), Person C (Frontend), Person D (Integration).

The API accepts validated readings and queues durable **pending** jobs. Acceptance does not
mean analytics, alerts, forecasts, or event delivery have completed. There is no worker,
simulator, or WebSocket implementation in this task.

## Request envelope

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | Yes | Exactly `"1.0.0"`; other versions return 422 |
| `message_id` | Yes | UUIDv4 delivery identifier |
| `asset_id` | Yes | Registered asset; ASCII letters/digits/dot/underscore/hyphen, first character alphanumeric, maximum 100 characters |
| `timestamp` | Yes | ISO-8601 measurement time with seconds and explicit `Z` or `±HH:MM` offset; up to six fractional digits |
| `source` | Yes | `device`, `simulator`, or `file_replay` |
| `run_id` | Conditional | Must be absent/null for device; required nonempty identifier for simulator/file_replay, same character/length rules as asset ID |
| `configuration_version` | Yes | Positive integer version belonging to this asset |
| `measurements` | Yes | Object of known measurement channels; individual channels are optional/nullable |
| `measurement_quality` | No | Per-channel producer flags: `good`, `suspect`, `bad`, `missing` |

Unknown envelope/measurement fields are rejected, including fault labels or ground truth.
Numbers must be finite JSON numbers (not strings or booleans). Naive timestamps, Unix numeric
timestamps, invalid dates, non-finite numbers, and malformed quality flags return 422.
Timestamps and history filters normalize to timezone-aware UTC. `measurement_time` is derived
from `timestamp`; `arrival_time` is the server database transaction-start time of the first
accepted delivery. It is never substituted for measurement time or updated by retries.

## Channels and units

| Key | Unit / convention |
|---|---|
| `voltage_r_v`, `voltage_y_v`, `voltage_b_v` | RMS volts, voltage convention and measurement side from the bound configuration |
| `current_r_a`, `current_y_a`, `current_b_a` | RMS line amperes, measurement side from the bound configuration |
| `oil_temperature_c` | Top-oil temperature, Celsius |
| `ambient_temperature_c` | Ambient temperature, Celsius |
| `oil_level_pct` | Oil conservator level, percent |

Omitted channels become **null**, never zero. Explicit zero remains zero. A packet with all
channels missing is accepted as evidence of missing coverage; it does not produce analytics.
Quality defaults to `missing` for null channels and `good` for present channels. Explicit
`missing` requires null; explicit good/suspect/bad requires a present number. Unknown channel
names/flag values are rejected. `good` describes producer quality, not verified physical truth.

Structurally valid but implausible values are retained unchanged in original and normalized
telemetry. `quality_flags` records source suspect/bad/missing flags and conservative ingestion
sanity checks: negative electrical magnitudes (`negative_magnitude`), electrical magnitudes
above ten times the bound rating (`above_10x_rating`), temperatures below −273.15°C or above
250°C, and oil level outside 0–100% (`outside_sanity_range`). These checks are transparent
heuristics, not validated transformer limits, analytics, or alerts. Nothing is clamped.

## Configuration selection

The caller selects `configuration_version` explicitly. The server checks a composite foreign
key against `(asset_id, version)` and never silently chooses the latest configuration. A
registered asset without that version returns 422; an unknown asset returns 404. Historical
versions remain valid references. Selection is a caller assertion, **not** proof that the
configuration was physically effective at measurement time; no effective-date history exists.
Convention/units/side are taken from this explicitly bound immutable configuration.

## Stream isolation and permanent deduplication

A stream is `(asset_id, source, run_id)`. Live device readings use null run IDs; the database
normalizes that to a non-null empty `run_key`. Simulator and file-replay streams require their
own run IDs. Source remains part of the namespace, even when two sources use the same run ID.

Deduplication is permanent for retained records, enforced by a unique constraint on
`(asset_id, source, run_key, message_id)`. This replaces the previously unimplemented baseline
24-hour window. There is no dedup expiry or automatic deletion. Producers must generate a new
message UUID for a new delivery. The same UUID may be used in another distinct stream.

Content identity uses SHA-256 over the original parsed JSON object, encoded with sorted keys
and compact separators. JSON whitespace/object-key order do not matter. Omitted versus explicit
null fields, different timestamp spellings/offsets, different numeric spellings after JSON
parsing (e.g. integer `1` versus float `1.0`), and changed measurements/configuration versions
are different content. Original JSON structure/values are retained; exact HTTP bytes,
whitespace, object-key order, and lexical number spellings are not audit guarantees.

First acceptance returns 201. Identical retries return 200 with the original reading, arrival
time, flags, configuration reference, and job ID. Conflicting reuse returns 409 without
changing stored content. Asset-row locking serializes admission and configuration creation;
PostgreSQL constraints independently guard duplicate readings and duplicate jobs. Locking is
per asset, a deliberate throughput tradeoff for correctness in this initial implementation.

## Atomic admission and event-time ordering

Original payload, normalized telemetry, flags/configuration reference, and one pending job
are stored in a single transaction. Any failure rolls back both reading and job. A job has a
unique reading foreign key and always reports `status=pending`, `analytics_status=pending`.
No completed analytics or forward model state is fabricated.

Latest is the greatest `(measurement_time, reading_id)` within the selected stream: time
first, then the greatest server-generated ID. Late readings are retained and flagged
`out_of_order=true` when their time is less than the existing stream watermark. They cannot
replace a newer measurement as latest. Equal-time readings use the ID tie-breaker, are not
strictly out of order, and are also excluded from future forward state advancement.

Job `state_policy` is `forward_only` only for a strictly advancing measurement time at
admission; older/equal readings use **historical_only**. Future workers must honor this
restriction, serialize state per `(asset_id, source, run_id)`, and check a strictly advancing
**last processed** event-time watermark transactionally before modifying model state. Jobs
may execute out of order, so admission eligibility alone is insufficient. Historical-only
jobs must never mutate forward state; replay/simulator state must never mutate live state.
There is no worker or model-state storage yet, so this task queues these restrictions rather
than claiming analytics execution. Detector adapters must use only `normalized_telemetry`,
quality flags and the bound configuration, not arbitrary raw metadata.

## Retrieval

- `GET /api/v1/assets/{asset_id}/telemetry/latest`
- `GET /api/v1/assets/{asset_id}/telemetry`

Both default to `source=device`, `run_id=null`. To inspect replay/simulation, supply both
`source` and `run_id`; queries never combine streams. Unknown asset returns 404. Latest with
no reading returns 404; history with no readings returns an empty page.

History uses `start` inclusive and `end` exclusive timezone-aware ISO-8601 filters on
measurement time. `start < end` when both are supplied. Defaults: limit 20, offset 0;
limit is bounded to 1–100 and offset is nonnegative. History sorts ascending by
`(measurement_time, reading_id)`. Offset pages are deterministic for unchanged data;
concurrent late inserts can shift pages. Clients should refetch when late data matters.

## Examples and review decisions

See `data/sample/telemetry-sample.json` (synthetic simulator run) and
`data/sample/telemetry-device-sample.json` (illustrative live envelope). Neither is certified
sensor data. Configure/register the example asset before submission; the integration script
creates a unique demonstration asset and uses entirely assumed configuration parameters.

Person B should confirm channel/quality mapping, the conservative sanity ranges, stream/state
policy, and the analytics adapter's input shape. Permanent stream-scoped deduplication and
explicit configuration binding are implemented contract decisions for team review. No fault
labels are accepted in telemetry; benchmarking ground truth must remain in separate metadata
outside detector inputs. See `backend/docs/telemetry-ingestion.md` for API usage and commands.
