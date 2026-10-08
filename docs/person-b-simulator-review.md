# Person B review: normal-operation simulator

Reviewed on 8 October 2026: simulator branch `feature/normal-operation-simulator`, commit `55a9c54`; analytics branch `feature/personb-twin-analytics`, baseline `8183b77`; main `26efab6`. Both feature branches descend from main and neither is merged. The analytics working tree was clean before this task. No applicable AGENTS.md was present. Simulator source was inspected and tested from an exported snapshot, without switching/merging branches or changing A's files.

## Accepted assumptions for synthetic generation

| Topic | Findings and accepted scope |
|---|---|
| Three-phase ratings | `generator.py:94-99` uses sqrt(3)*V_LL*I_line/1000 or 3*V_LN*I_line/1000; rejects >5% rating mismatch. Sample 11 kV/52.49 A implies 1000.0688 kVA versus 1000 kVA, consistent within that tolerance. |
| Voltage and side | RMS convention and measurement side come from the bound immutable config. No turns-ratio conversion is assumed. LL inputs cannot uniquely reconstruct unbalanced phase-neutral phasors. |
| Current | RMS **line** current on the same side; do not treat it as delta winding current. Current loading and capacity loading are distinct outputs. |
| Operating envelope | K=0.60+0.15*sin(2*pi*t/3600); default per-phase current envelope 0.4446-0.759 pu and voltage envelope 0.978-1.022 pu. Bounds are synthetic envelope constraints, not physical safe-loading certification. |
| Phase variation/noise | Default offsets -1/0/+1%; independently hashed uniform electrical noise +/-0.2%. Deterministic bounded variation is suitable for repeatable ingestion/UI exercises, not sensor-accuracy or realistic fault statistics. |
| Ambient | 25+2*sin(2*pi*t/86400) C, an assumed smooth day cycle. No site weather, wind, enclosure or cooling control is represented. |
| Oil temperature | Assumed target ambient+40*K^2 C, tau=60 min; exact first-order update holds the **previous sample** target over each interval. Initial oil is a supplied observation/assumption, not steady-state evidence. |
| Thermal provenance | Simulation rise/tau live in run metadata. Registry thermal parameters are preserved but ignored by this generator. They must not silently become prediction parameters. The curated registry snapshot has all thermal coefficients null. |
| Sampling | Explicit timezone normalized to UTC; half-open sampling. Duration301/interval60 gives six samples at 0..300 s. No partial final interval. Default/demo 30-60 s is sensible for this synthetic load period; permitted coarse intervals can alias it. |
| Oil level/labels | Optional oil level remains null with missing quality. Scenario metadata remains outside telemetry and detector inputs. Producer `good` means present synthetic data, not verified physical truth. |

Source references: [generator at reviewed commit](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/blob/55a9c54/backend/app/simulator/generator.py), [simulator documentation](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/blob/55a9c54/docs/normal-operation-simulator.md), [simulator tests](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/blob/55a9c54/backend/tests/test_simulator.py).

## Necessary corrections at the analytics boundary

1. **Separate capacity loading from worst-phase current loading.** Simulator envelope code `generator.py:108-116` applies max_load_pct to a conservative apparent-power estimate. The prior B adapter used it as a worst-phase-current threshold. The new worker reports both quantities and labels its max_load_pct evidence as **capacity_loading_pct**. This interpretation is implemented for review, not a claim that the shared contract already defines it.

   Reproducible evidence: `analytics/tests/test_simulator_compatibility.py::test_load_limit_basis_counterexample` supplies rated_kva1040 with the same 11kV/52.49A rating (within the permitted 5% tolerance) and max_load_pct75. The simulator accepts a conservative capacity bound about74.59%, while generated worst-phase current loading exceeds75%. Therefore the two quantities cannot share an unnamed threshold. If A intends a phase-current limit, add an explicit limit or apply both checks after agreement. This is a contract ambiguity, not proof of a defect under the documented apparent-load interpretation.

2. **Do not report a bootstrap measurement as a prediction.** The new worker stores the initial measured oil temperature as initial condition, returns prediction/residual null on that frame, and makes its first independent model step at the next measurement time. Initialization cannot detect a pre-existing oil-sensor offset.

3. **Bind state to model and parameter versions.** Existing B state did not carry a model version in its binding. The worker-facing state now includes stream, config version, parameter fingerprint and model version; old incompatible state requires explicit replay/cold start.

4. **Remove unsupported numerical assurances from the worker handoff.** Prior B health/coverage scoring remains a legacy demonstration API. The new callable subset does not turn those heuristics into validated health or confidence; scores/probabilities remain null with reasons.

No blocking generation-code correction was demonstrated for its stated synthetic purpose. A's simulator, backend, migrations, database and configuration were not modified. These boundary corrections are implemented in B's code; shared contract revisions remain proposals.

## Limitations and team decisions

- A/C/D must confirm the meaning of max_load_pct and whether independent phase-current limits are required.
- Clarify documentation wording on "phase differences": an allowed +/-2% offset permits 4% R-to-B spread before noise; max deviation from the mean is a different definition.
- The thermal generator uses baseline K, not noisy per-phase mean squared current, and lacks no-load-loss behavior. B's existing prediction core uses loss ratio/exponent and a configurable tau. Differences between them are expected model mismatch, not automatically fault evidence.
- The new worker uses the previous-sample zero-order hold, aligning temporal convention with the simulator; its equilibrium remains the existing B loss-ratio model. This is versioned behavior, distinct from the older adapter's current-endpoint approximation.
- Generator intervals >300 s are legal but exceed the worker's versioned continuity horizon. B returns unavailable rather than bridging unknown history. Agree the acquisition cadence and whether a future model-policy version needs a configurable horizon.
- The initial oil check is against minimum synthetic ambient, not a proof of physical equilibrium. Short six-frame demonstrations are far shorter than either simulator or predictive thermal time constant.
- No winding hot-spot, phase angles, power factor, kW/kvar, aging/RUL, validated confidence or fault probability is established.

## Actual verification and physical-validation boundary

The exported simulator snapshot's complete backend suite passed **115 tests** using an isolated local PostgreSQL `_test` database and A's migrations. The analytics checkout's combined suite passed **161 tests**, including three reviewed-simulator compatibility checks (two real-ingestion parameter cases and the loading counterexample), 30 worker tests and eight JSON Schema tests. Commands and full handoff semantics are in `person-b-analytics-handoff.md`.

The local compatibility test creates its own asset/run: six readings/six pending jobs, six identical retries without extras, no simulator records in default device history, final measurement at00:05:00Z. It does not contact Person A's localhost. The user-reported Windows stream `demo-normal-baa53c0540514e999ba5ecc9a4f77462` / `normal-baa53c0540514e999ba5ecc9a4f77462` / config1 is **external reported evidence**, not a local asset or a stream inspected by this task.

Simulator-to-adapter tests establish schema, unit, ordering and execution compatibility only. Closed-form tests establish numerical equation implementation, not physical predictive accuracy. No independent measured validation dataset is available. No simulator RMSE is presented as predictive validation.
