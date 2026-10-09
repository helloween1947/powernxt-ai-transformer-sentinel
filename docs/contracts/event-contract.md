# Domain Event Publication & Recovery Contract

**Status**: Baseline Specification (Managed by Person A)  
**Consumers**: Person C (Frontend Live Updates), Person D (Integration Pipelines)

## 1. Overview
This contract specifies notifications and domain events emitted across WebSocket streaming channels and message queues when noteworthy operational thresholds, state transitions, or alerts occur.

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

When clients (such as Person C's dashboard) disconnect due to network interruption:
1. The WebSocket client preserves the timestamp or `event_id` of the last successfully received message.
2. Upon reconnecting, the client queries the REST catch-up recovery endpoint:
   ```http
   GET /api/v1/events?asset_id={asset_id}&since={last_measurement_time}
   ```
3. The backend returns any missed events chronologically ordered.
4. Once catch-up is confirmed, the client re-subscribes to live WebSocket / SSE streaming.
