# Person B: sustained evidence and conditional scenarios

Implemented 9 October 2026 after reviewing current main `9d2f9cd` and its merged durable worker. A's vendored B computation identifies commit `637fbe810714d0d5c403728ddf7bcba746ea55a9`; our three existing numerical fixtures match it exactly. The existing worker/model/result schemas and behavior are unchanged by this contribution. No branch merge, backend edit, database migration, API/UI change or alert publication is performed.

These are optional pure analytical functions, not automatically adopted worker behavior. They extend the existing Person B physical core using its established equations; no additional physical fault model, health score, confidence percentage, probability or cooling-intervention equation is introduced.

## Sustained threshold interface

```python
from analytics import evaluate_persistent_rules

def evaluate_persistent_rules(
    analytics_result: dict, policy: dict,
    previous_state: dict | None = None,
) -> dict: ...
```

Input is the structured worker result, explicit detector policy and separately persisted detector state. Only whitelisted analytical quantities, their availability/channel quality, reading identity, measurement time and stream/model/configuration references enter evaluation. Original payload, generator metadata and ground-truth labels are ignored. No clock, HTTP, I/O, IDs from random generators, implicit threshold or wall-clock aging is used.

Policy requires exactly version(string), provenance(assumed/measured/team_agreed), max_gap_s(positive finite seconds) and rules(one to six entries). Each rule requires exactly name(unique nonempty string), quantity, unit, trigger, recovery, persistence_s, recovery_s and severity(info/warning/critical). Thresholds are finite; recovery<trigger; both durations positive. Supported quantities:

| Quantity | Unit |
|---|---|
| electrical_metrics.capacity_loading_pct | % |
| electrical_metrics.max_phase_loading_pct | % |
| electrical_metrics.current_magnitude_imbalance_pct | % |
| electrical_metrics.voltage_magnitude_imbalance_pct | % |
| thermal_assessment.thermal_residual_c | C |
| thermal_assessment.measured_top_oil_temperature_c | C |

No default policy is installed. **The executed example policy is assumed, not recommended protection settings**:

```python
policy = {
    "version": "demo-capacity-v1", "provenance": "assumed", "max_gap_s": 300,
    "rules": [{"name": "capacity_overload",
               "quantity": "electrical_metrics.capacity_loading_pct", "unit": "%",
               "trigger": 120, "recovery": 100,
               "persistence_s": 180, "recovery_s": 120, "severity": "warning"}],
}
observations = evaluate_persistent_rules(committed_analytics, policy, saved_detector_state)
next_detector_state = observations["updated_state"]
```

First qualifying sample starts at0s. Later consecutive samples strictly above trigger credit actual measurement elapsed time; persistence opens one incident. Consecutive samples strictly below recovery eventually resolve the same incident. Trigger/recovery equality is in the dead band. Qualifying endpoints **approximate**, rather than prove, continuous evidence between samples. There is no interpolated threshold crossing or statistical anomaly probability.

Missing/invalid/unavailable values reset pending/recovery timers and never resolve an active incident. A large gap resets timers; a usable endpoint starts a fresh timer at0. Recovery must be observed again. Historical/nonadvancing/equal/late/error results do not advance detector state. Exact retries with the pre-state reproduce identical candidate transitions; retries with the post-state do not emit another transition. No packets means no new detector transitions; feed-silence monitoring remains outside this module.

Output fields:

| Field | Type / meaning |
|---|---|
| detector_version | sustained-threshold-1.0.0 |
| policy_version, policy_provenance | Explicit supplied policy identifiers |
| state_advanced, reasons | Boolean and reason list |
| measurement_time | Input measurement time normalized to UTC |
| events | Candidate opened/resolved records: incident_id, category, severity, lifecycle, evidence, persistence_required_s, recovery_required_s |
| evidence | Per-rule values/null, availability/reasons, unit/thresholds, reading/time reference and continuity assumption |
| updated_state | Nullable serialized detector state, unchanged for ineligible input |
| active_incidents | Active rules with timers/sequence and **last usable evidence**, which may be older than this result |

State schema sustained-threshold-state-1.0.0 binds stream/configuration/model/parameter versions, detector version and policy SHA256. It records last measurement identity/time and per-rule active/sequence/incident/timer/previous endpoint/last usable evidence fields. Policy/model/config/run changes reject prior state; deliberate replay/reset and preservation of earlier incident history are A/D responsibilities. Incident ID derives deterministically from binding/rule/sequence, without processing-time/random data. Validate inputs before execution; malformed policy or incompatible state raises ValueError. Strict finite JSON is enforced.

These are **candidate domain observations**, not the UUID/publication_time transport envelope in the shared event contract. A/D must agree publication schemas, event types and lifecycle ownership before wiring them in. Severity comes only from the explicit policy. Positive residual evidence can indicate mismatch or poor initialization/calibration; it is not automatically a cooling-fault diagnosis.

Resetting to null with the exact same binding restarts candidate episode sequences.
For an operational reset, A must record a new durable detector_epoch and use the
canonical asset/epoch/episode mapping in the merged incident design. Do not change
policy or run identity merely to manufacture a new ID. Same-epoch replay reuses
the retained canonical mappings. See [orchestration and handover](person-b-detector-orchestration-handoff.md)
and the pure evaluate_incident_candidates adapter for the current storage boundary.

## Forecast and what-if interfaces

```python
from analytics import forecast_from_worker_state, compare_worker_scenarios

def forecast_from_worker_state(
    current_state: dict, asset_config: dict,
    future_load_profile: list[dict],
) -> dict: ...

def compare_worker_scenarios(
    current_state: dict, asset_config: dict,
    scenarios: list[dict],
) -> dict: ...

profile = [{"duration_s": 7200, "thermal_load_pu": 1.0, "ambient_temp_c": 30}]
comparison = compare_worker_scenarios(saved_twin_state, immutable_config, [
    {"name": "baseline", "profile": profile},
    {"name": "lower_load", "profile": [
        {"duration_s": 7200, "thermal_load_pu": 0.5, "ambient_temp_c": 30}]},
])
```

The valid initialized worker state and bound immutable config must agree in asset/version/model/parameter fingerprint. All four thermal coefficients must be explicitly available; absent/invalid history is rejected rather than seeded with invented temperatures. Forecast starts from the healthy worker temperature (or observed bootstrap), **not latest measured oil**, so it is a healthy continuation forecast, not a fault-aware maintenance-action forecast. Live state is never changed.

Each segment requires exactly duration_s(positive finite seconds), thermal_load_pu(0..10), ambient_temp_c(-50..80C). Accept1..96 segments, total horizon at most24h, and1..12 uniquely named scenarios with equal horizons. Bounds are versioned implementation limits, not calibrated reliability horizons. Profiles deliberately posit complete future load/ambient, so their durations can exceed the300s historical continuity cutoff; this does not restore missing past history.

Version healthy-top-oil-scenarios-1.0.1 uses the same exact first-order exponential and loss-ratio equilibrium as the worker, with constant explicit inputs per segment. Output reports estimated source, original state/config references and timestamp, assumed profile, initial/endpoints, final/peak temperatures(C), horizon(s), configured top-oil limit and first crossing(s), units and limitations. First crossing is analytically solved within a monotonic segment, not snapped to60s; absent limit has an explicit unavailable status. Reaching a limit only asymptotically does not imply a finite crossing. Initial limit breach is0s. Piecewise-constant segments are monotonic, so exact endpoint maxima suffice for peak.

Comparison's first scenario is baseline; every scenario shares exactly the same initial state and horizon, with final delta from baseline(C). Increasing K changes squared-current loss; ambient shifts equilibrium. No cooling multiplier, fault probabilities, uncertainty bands, optimized actions or maintenance recommendations are invented. Numerical exceptions/invalid profiles produce ValueError for callers to handle, not a successful forecast. Outputs are deterministic finite JSON.

## Actual artifacts and verification

- `analytics/examples/persistent-rules-test-example.json`: actual synthetic executions with policy, worker results, prior detector state and output; opens at180s and resolves at360s. No alerts were published.
- `analytics/examples/worker-scenarios-test-example.json`: actual two-hour baseline/lower-load/warmer-ambient executions with exact input/output; all start from one identical state and assumed coefficients.
- Regenerate with `python -m analytics.examples.persistent_rules_demo` and `python -m analytics.examples.worker_scenarios_demo`.

Actual commands/tests with Python3.12:

1. Targeted new persistence/scenario suites:48 tests (26 persistence,22 scenarios), including exact executed-fixture reproduction.
2. `.venv/bin/python -m pytest analytics/tests/test_persistence.py analytics/tests/test_worker_scenarios.py analytics/tests/test_worker.py analytics/tests/test_worker_schemas.py analytics/tests/test_worker_handoff.py -q --tb=short`: **105 passed**.
3. Exported current main9d2f9cd with only B's analytics copied into its temporary checkout: `TEST_DATABASE_URL=<isolated PostgreSQL sentinel_test URL> <feature-venv-python> -m pytest backend/tests analytics/tests -q --tb=short --maxfail=3`: **305 passed**, none skipped. Includes A's merged durable worker and simulator. No branch merge or application database modification. Starlette/Alembic deprecation warnings remain.
4. Direct parity execution: our three worker fixtures equal A's vendored `compute_analytics` outputs exactly.

Detector checks cover endpoint-based persistence, recovery/dead band, reopen identity, missing evidence,300/301s gap boundary, ordering, retries, policies/config/model/run bindings, explicit units and label exclusion. Forecast checks cover hand-calculated exponential response, partition invariance, zero-load cooling, exact crossings, initial/asymptotic limits, missing thresholds, invalid/incompatible state, horizon bounds and explainable scenario deltas. Synthetic agreement is interface consistency, not field predictive accuracy. Independent measured calibration/validation data and validated fault thresholds remain unavailable.

## Integration work remaining

This optional detector and forecast layer is not automatically loaded into A's vendored computation; existing stored-result schemas remain unchanged. A/D must agree policy provenance/threshold selection and store detector state/candidate transitions atomically with appropriate locks and idempotent publication keys. Retries from the same pre-state re-emit deterministic candidates, so database/outbox uniqueness is necessary before notification. Selecting persisted input results must preserve measurement ordering; no feed-silence timer is built here.

C can use the executed examples to plan incident evidence and side-by-side scenario displays. A/C must agree scenario API and segment-chart interpolation; straight lines between exponential endpoints are only display approximations. D owns acknowledgement, incident/task persistence and maintenance actions. No API, deployment, scheduler, lease, audit service, frontend or teammate message is added. Uncalibrated health/confidence scores remain null in the conservative worker. Remaining scientific work requires independent measured history and asset-specific calibration rather than additional synthetic scoring.
