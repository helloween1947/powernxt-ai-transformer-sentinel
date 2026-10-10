# Domain Event Publication & Recovery Contract

**Status**: Proposed generic specification (Managed by Person A); not implemented on main
**Consumers**: Person C (Frontend Live Updates), Person D (Integration Pipelines)

## 1. Overview
This historical specification proposes notifications across WebSocket streaming
channels and queues. Main does not implement these transports or the global
/api/v1/events recovery endpoint. The envelope/types below are proposals, not
promises from a running server.

A's separate registry branch implements authenticated per-incident event history;
its newer A002 branch adds a durable delivery checkpoint/dispatcher with a supplied
transport callback. It does not configure a shared queue/WebSocket transport.
Consumers must use that branch's exact incident API/delivery contract after review
and deployment, not assume this generic endpoint is an alias. Delivery is at least
once: deduplicate stable event_id and apply incident_version monotonically per
incident. For journal polling retain the highest observed incident-version cursor;
measurement time alone is not a safe mutation/reconnection checkpoint.

This status clarification does not change any wire schema or adopt an undeployed
transport. A/C/D must review any future global feed separately.

## 2. Event Envelope Schema

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `event_id` | string (UUIDv4) | Globally unique identifier for this event occurrence. |
| `event_type` | string | Categorical event key (see Proposed Event Types below). |
| `asset_id` | string | Target transformer identifier. |
| `run_id` | string or null | Simulation or replay session identifier (null if physical feed). |
| `measurement_time` | string (ISO 8601 UTC) | Timestamp of the original telemetry measurement that triggered the event. |
| `publication_time` | string (ISO 8601 UTC) | Timestamp when the backend emitted the event payload. |
| `data` | object | Event-specific context payload. |

## 3. Proposed Event Types

- `telemetry.threshold_breach`: Critical physical threshold crossed (e.g., top-oil temp > 85°C).
- `analytics.anomaly_detected`: Unsupervised or statistical detector identified abnormal operation.
- `state.mode_transition`: Operating mode shift (e.g., normal -> cooling_overload -> emergency_shedding).
- `maintenance.action_recommended`: Automated recommendation generated for inspection or cooling check.
- `simulator.scenario_completed`: Synthetic test run completed its playback sequence.

## 4. Reconnection & REST-Based Catch-Up Recovery

Proposed future behavior, not an executable main workflow: when clients disconnect:
1. The WebSocket client preserves the timestamp or `event_id` of the last successfully received message.
2. Upon reconnecting, the client queries the REST catch-up recovery endpoint:
   ```http
   GET /api/v1/events?asset_id={asset_id}&since={last_measurement_time}
   ```
3. The backend returns any missed events chronologically ordered.
4. Once catch-up is confirmed, the client re-subscribes to live WebSocket / SSE streaming.
