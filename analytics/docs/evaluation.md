# Evaluation and Person B demonstration

Run `python -m analytics.evaluation.run` to regenerate `analytics/evaluation/results.json`. The harness simulates an independent 5 s Euler reference plant with the same nominal model family, adds Gaussian sensor noise with seed 42 and standard deviation 0.35 C, and processes 60 s samples for ten hours. Faults run from minute 120 through just before minute 300. Scenario labels are used only by the harness to inject faults and score outcomes; the detector receives sensor values and quality only.

## Observed synthetic results

| Case | Expected evidence | Open delay from injection | Recovery |
|---|---|---:|---|
| Normal | No incident | No openings in 601 samples | Not applicable |
| Overload | 130% phase loading | 180 s | Minute 303 |
| Imbalance | Unequal phase currents | 180 s | Minute 303 |
| Reduced cooling | Persistent positive oil residual | 7560 s (126 min) | Minute 499 |
| Oil sensor loss | Unavailable input group | 180 s | Minute 303 |

Normal oil residual RMSE is approximately 0.3515 C. The imbalanced case also correctly opens an overload incident because its most-loaded phase is above rating. Reduced cooling takes time to produce an 8 C residual; its long latency is reported, not hidden as just the persistence delay. Recovery after cooling restoration requires physical cooldown as well as continuous low residual evidence.

These are consistency checks. Shared nominal equations and synthetic noise make them optimistic relative to real transformers. There is no claim of field accuracy, failure prediction accuracy, RUL, calibrated uncertainty or general fault classification. An oil residual alone cannot distinguish reduced cooling, bad initialization, model mismatch or sensor offset. The supplied spreadsheet cannot support a held-out thermal accuracy evaluation.

Before field evaluation, A must provide timestamped phase currents, voltage topology/units, ambient and top-oil measurements; verified ratings; quality flags; and representative normal/fault history. Split calibration and evaluation chronologically. Calibrate rise/loss ratio/time constant/initial condition on training history; freeze parameters before scoring held-out MAE/RMSE, per-incident precision/recall, detection latency, false openings per operating hour and recovery time. Keep labels in the evaluator only. D consolidates this with end-to-end results.

## Automated checks

`python -m pytest analytics/tests -q` covers electrical calculations against known results; exact thermal step and step-composition equivalence; gradual load heating; residual independence from measured temperature; missing/nonfinite inputs; latched unknown load history; persistence, hysteresis and recovery; isolated outliers; restart equivalence; duplicate/out-of-order and stale rejection; quality overrides and sensor-loss incidents; reinitialization; distinct what-if load/ambient/cooling inputs; equal-horizon enforcement; label exclusion; and finite JSON serialization.

## Short demonstration

1. Run the test suite and synthetic evaluation; show their results.
2. Run `python -m analytics.examples.demo`; the fixture uses a deliberate +12 C measurement offset to make evidence easy to inspect. It is an offset demonstration, not the cooling-fault evaluation.
3. Explain frame electrical loading, predicted oil temperature and residual. Show the gradual expected rise after the load change, then the persistent overload and unexpected-heating openings.
4. Point out the separate contributors and confidence. Run the sensor-loss test or replay to show an unknown condition without incorrectly clearing active incidents.
5. Compare keep-load, reduced-load and improved-cooling action forecasts. All start at the same observed oil temperature and horizon. Explain their assumed load/ambient/cooling inputs and final deltas. Cooling improvements are hypothetical, uncalibrated sensitivity inputs.
6. Hand the alert `incident_id`, type and evidence to D's maintenance workflow; C renders the same fixture via A's API.

The final integrated demonstration still depends on A/C/D's components. Person B's reusable calculations, fixture, assumptions, model checks and evidence are ready for that integration.
