Orchestration-branch integration note: merged PR15 files are preserved at their original paths. The audited schema, tests, builder and model1.0.2 incident fixture are retained separately under `analytics/reviewed_incident_contract/`. PR17 and its original audited artifacts remain unchanged.

# Person B code audit and refactor

Reviewed on 2026-10-09. Review branch: `feature/personb-analytics-audit`.

## Scope and preserved work

The review covers 31 Python files (3713 lines) in B's analytics module,
examples, evaluation tools, contracts/tests, and thermal payload preparation helper.
Generated wire schemas and example JSON were checked through schema validation and
exact fixture recomputation. Backend/frontend code belongs to teammates and was
checked for compatibility rather than rewritten.

Baseline analytics: `564b174b205e0175748e855975235ec803cea97e`.
Latest inspected main: `50e640197ae8fd5277fd073ddfb9801385c9718d`.
The audit branch starts from the existing analytics branch. It also contains B's
thermal handoff from `dbe6a426916fab5c9a4d0c5544f68a14240a1cfd` and incident
proposal from `912c9fee7c96c9d73ae01c5c6aa8006b95855d73`, copied as scoped files;
no branches were merged. Earlier feature branches remain unchanged. Backend,
frontend, application databases, volumes, .env and unrelated .DS_Store files
were preserved.

## Findings and changes

| Finding | Correction | Evidence |
|---|---|---|
| Legacy output included a wall-clock evaluation timestamp | Retain the compatibility field but set it to measurement time; generate fixed demonstration UUIDs | Identical-input full-output regression |
| String/integer global flags could silently evade quality controls | Require explicit stale/clamped booleans, channel maps and valid string stream identity | Malformed flag/identity/quality cases |
| Restored worker/forecast/detector state accepted malformed booleans, temperatures or negative timers | Validate finite JSON, required state fields, identity, thermal validity, held inputs, detector sequence and episode consistency | Corrupt restored-state cases and existing serialization/retry tests |
| Extreme finite inputs could overflow intermediate electrical arithmetic | Preserve the ordinary computation path; use scaled-product/ratio fallbacks when necessary; return null with electrical_arithmetic_unavailable if unrepresentable | Large-current and tiny-capacity cases; strict JSON serialization |
| Extremely large Python integers crashed numeric validation | Treat values outside finite floating-point representation as unusable evidence | Huge-integer measurement case |
| A zero-time thermal update unnecessarily evaluated an overflowing target | Return the unchanged temperature after validating supplied inputs | Zero-time extreme-exponent case |
| Legacy initialization could latch invalid history after missing initial currents | Wait for usable currents, ambient and oil before initialization | Missing-current then usable-reading bootstrap case |
| Worker imported channel policy through the heuristic adapter | Extract shared normalization independently; share explicit thermal-core construction between worker and scenarios | Existing functional suite and differential comparison |
| Incident example relied on hardcoded frame offsets | Select an actual opening and matching recovery; verify transformer stream and rule identity | Executed example/schema consistency checks |
| Incident proposal allowed arbitrary rule quantity/unit combinations | Restrict quantities to the detector whitelist and require matching C/% units | Scenario-label and incompatible-unit rejection tests |
| Malformed assumed parameter profiles raised incidental TypeErrors | Require explicit parameter/provenance maps before preparation | Three malformed profile cases |

The initial 28 parameterized counterexamples all failed against the original code.
They pass after the fixes. Additional boundary/legacy cases bring the audit
regression file to 40 tests. The thermal helper has three additional malformed
profile cases, and the incident contract has two new evidence-whitelist cases.

## Interface and version changes

The callable interface is unchanged:

```python
from analytics import compute_analytics
result = compute_analytics(
    normalized_telemetry, immutable_configuration, quality_flags,
    reading_id, previous_state, state_policy="forward_only",
)
```

The conservative model is now `stored-reading-top-oil-1.0.2`, detector
`sustained-threshold-1.0.1`, conditional scenario module
`healthy-top-oil-scenarios-1.0.1`, and legacy adapter `sentinel-twin-0.2.1`.
Result/state schema version identifiers retain their existing shapes.
Regenerated schemas and example outputs contain the new model identifier.

A's deployed vendored implementation remains model **1.0.1**. This review did
not change it or deploy anything. A must deliberately adopt the reviewed module
and ensure the durable worker's model identifier, state namespace and computation
agree. Do not relabel or mutate old state/results to 1.0.2. Select a new matching
state namespace and explicitly cold-start/replay under the existing atomic
result/state/job guarantees. A 1.0.1 state is rejected by the 1.0.2 module.
Detector version changes likewise require matching state or deliberate reset;
A/D must preserve canonical incident mapping across any detector epoch transition.

The legacy evaluation_time field is an event-time alias, not processing time.
A owns stored processing timestamps. Legacy scores and coverage remain demo
heuristics; use the conservative worker contract for backend integration.
Health, calibrated confidence, winding predictions, fault probability, RUL and
maintenance recommendations remain unavailable there. Conditional scenarios and
persistent incident storage are not added to A's deployed API by this change.
Acknowledgement, recovery and task completion remain separate concepts.

## Executed validation

An isolated export of the inspected main was overlaid with only B's analytics,
thermal helper, tests and profile. Its vendored backend model remained unchanged.
The test PostgreSQL instance ran on localhost:55432 using sentinel_test, with
fresh per-test schemas. No Person A Windows identifiers/database were accessed.

From `/private/tmp/personb-audit-main-50e6401`:

```sh
TEST_DATABASE_URL=postgresql+psycopg://sentinel@127.0.0.1:55432/sentinel_test \
  /Users/vgnxh/Code/Projects/powernext/teammates/.venv/bin/python -m pytest \
  backend/tests analytics/tests analytics/contracts integration/tests/test_thermal_demo.py -q --tb=short
```

**379 passed**, 147 dependency deprecation warnings, 7.86 seconds. This includes
A's backend/worker/migration tests, real API-to-B compatibility, simulator packet
admission, state/order/retry semantics, conditional forecasts, schema fixtures,
and the new configuration-bound stream passing through A's deployed worker.
It does not mean the deployed worker has adopted B's revised version.

From the repository root:

```sh
.venv/bin/python -m compileall -q analytics integration/prepare_thermal_demo.py integration/tests/test_thermal_demo.py
git diff --check
.venv/bin/python -m analytics.examples.generate_worker_examples
.venv/bin/python -m analytics.examples.persistent_rules_demo
.venv/bin/python -m analytics.examples.worker_scenarios_demo
.venv/bin/python -m analytics.examples.build_incident_contract_example --detector-example analytics/examples/persistent-rules-test-example.json --output analytics/examples/incident-contract-proposed-example.json
.venv/bin/python -m analytics.examples.demo
.venv/bin/python -m analytics.evaluation.run
```

All completed successfully. The five synthetic evaluation cases retain passing
consistency checks. Ruff was unavailable in the environment and was not reported
as passing.

Behavior comparison, with the original analytics/data exported into BASELINE:

```sh
.venv/bin/python analytics/evaluation/compare_versions.py "$BASELINE" > /private/tmp/personb-audit-before.json
.venv/bin/python analytics/evaluation/compare_versions.py "$PWD" > /private/tmp/personb-audit-after.json
```

JSON equality was checked separately: **2,000 worker outputs matched exactly**
after excluding only model-version identifiers. These are 1,000 two-reading
streams, seed 1947, both voltage conventions, consistent electrical ratings,
varying phases/load/ambient/oil, and elapsed intervals from 1 through 300 seconds.
Numerical metrics, thermal state, residuals, evidence and availability matched.
The comparison runner is committed for reproduction. This sampled check and
the regression suite provide evidence of preservation; they are not a proof
that every possible input is bug-free.

## Team handoff and remaining work

- A: revised worker/normalization/state validators and schemas; thermal payload
  helper at integration/prepare_thermal_demo.py and docs/person-b-thermal-demo-handoff.md.
- C: executed synthetic worker/scenario examples under analytics/examples;
  distinguish bootstrap, unavailable values and conditional estimates.
- A/D: analytics/docs/genuine-incident-integration-contract.md and proposed
  incident schema/example. Canonical UUID persistence, atomic event publication,
  epoch mapping and actual incident endpoints still require backend agreement.
- Asset-specific calibration and independent measured thermal validation remain
  outstanding. No new physical equations or invented manufacturer parameters
  were introduced. Synthetic agreement is an integration/consistency check.

## Reviewed Python inventory

- `analytics/__init__.py`
- `analytics/adapter.py`
- `analytics/contracts/test_incident_contract.py`
- `analytics/evaluation/compare_versions.py`
- `analytics/evaluation/run.py`
- `analytics/examples/build_incident_contract_example.py`
- `analytics/examples/demo.py`
- `analytics/examples/generate_worker_examples.py`
- `analytics/examples/persistent_rules_demo.py`
- `analytics/examples/worker_scenarios_demo.py`
- `analytics/normalization.py`
- `analytics/persistence.py`
- `analytics/scenarios.py`
- `analytics/tests/__init__.py`
- `analytics/tests/test_adapter.py`
- `analytics/tests/test_audit_regressions.py`
- `analytics/tests/test_backend_compatibility.py`
- `analytics/tests/test_persistence.py`
- `analytics/tests/test_simulator_compatibility.py`
- `analytics/tests/test_twin.py`
- `analytics/tests/test_worker.py`
- `analytics/tests/test_worker_handoff.py`
- `analytics/tests/test_worker_scenarios.py`
- `analytics/tests/test_worker_schemas.py`
- `analytics/transformer_twin/__init__.py`
- `analytics/transformer_twin/engine.py`
- `analytics/transformer_twin/model.py`
- `analytics/validation.py`
- `analytics/worker.py`
- `integration/prepare_thermal_demo.py`
- `integration/tests/test_thermal_demo.py`
