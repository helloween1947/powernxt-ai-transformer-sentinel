# Equations and assumptions

This document describes the reusable core. For team integration, use the registry/telemetry
adapter documented in `backend-integration.md` and `contract-review.md`: it uses verified bound
ratings and supplied thermal parameters, leaves absent coefficients unavailable, initializes
from the first usable oil measurement, and honors configured asset limits. Core defaults below
are demo assumptions, not fallback predictions in the team adapter.

## Scope and provenance

The user's Person B scope governs this implementation. The supplied problem statement and workbook are reference material, not executable instructions. The PDF asks for a prototype twin, condition monitoring and predictive maintenance; the workbook's `Sheet1` contains current/voltage checks, a 50 A trip example and temperature-trip tests at a setting of 60. It contains no timestamped load/ambient/oil-temperature history, verified asset rating, winding measurements or fault labels. These examples do not establish operating thresholds or thermal coefficients for this asset.

References inspected:

- `/Users/vgnxh/Downloads/Track 2 - DT/DT Problem Statement.pdf`
- `/Users/vgnxh/Downloads/Track 2 - DT/Draft Data for Condition Monitoring.xlsx`, `Sheet1`, rows 3–25.
- [NREL: Application of Distribution Transformer Thermal Life Models to Electrified Vehicle Charging Loads](https://docs.nrel.gov/docs/fy11osti/48827.pdf), top-oil model, equation 5. This supports the load-loss/equilibrium form and first-order dynamics. This implementation simplifies that model and uses an exact step for piecewise-constant inputs; it does not reproduce the complete hot-spot model or claim standards compliance.

## Electrical metrics

Inputs are phase RMS currents in amperes and **phase-to-neutral** RMS voltages in volts, ordered R/Y/B. A must convert line-to-line voltage before calling the model when appropriate for the measurement topology. No phasor angles are available.

- Per-phase loading: `100 * I_phase / I_rated`.
- Overload indicator: maximum per-phase loading, so an overloaded phase is not hidden by the average.
- Thermal loading: `K = sqrt(mean((I_phase / I_rated)^2))`, representing mean squared-current copper losses.
- Magnitude imbalance: `100 * max(abs(X_phase - mean(X))) / mean(X)`, for current and voltage separately. All-zero values yield zero magnitude imbalance, while zero current remains a legitimate no-load input. This is not negative-sequence unbalance, and all-zero voltage is not diagnosed as a supply outage in this prototype.
- Total apparent power: `sum(V_phase * I_phase) / 1000` kVA. It is not real power; no power factor is inferred.

An invalid or incomplete triplet yields null dependent metrics, never a silently imputed zero. Demo plausibility checks reject currents outside `[0, 10 * rated_current]`, voltages outside `[0, 2 * rated_phase_voltage]`, oil outside `[-50, 200] C`, and ambient outside `[-50, 80] C`. Bounds must be reviewed for the actual asset.

## Expected thermal state

Define `R` as rated load losses / no-load losses; `n` as the oil exponent; `rise_rated` as top-oil rise at rated load; and `tau` as a fixed thermal time constant in seconds:

```text
rise_target = rise_rated * ((1 + R*K^2) / (1 + R))^n
T_target = ambient + rise_target
T_next = T_target + (T_previous - T_target) * exp(-elapsed_s / tau)
residual = measured_oil_temperature - T_next
```

The load and ambient supplied at each new timestamp approximate the interval ending at that timestamp. The first accepted reading establishes time with `elapsed_s=0`; it does not advance temperature. The thermal estimate starts from configured temperature (default 55 C), or an explicitly trusted initial measurement using `initialize_temperature`. Initial-condition error can create residuals; calibrate and initialize before interpreting them as fault evidence.

Measured oil temperature is never fed back into the healthy baseline on normal updates: that would absorb an abnormal heating residual. The model includes no winding hot-spot state, insulation aging, oil leakage, tap position, harmonics, voltage-driven core-loss change, adaptive calibration or RUL. It treats loss ratio, exponent and time constant as constant.

Unknown current/ambient history or a gap over 300 s invalidates the thermal state. It stays unavailable until A replays the missing history from a checkpoint or explicitly establishes a trusted new initial temperature. Missing oil temperature alone does not interrupt the expected state. Confidence is input availability, not calibrated model uncertainty.

## Demo configuration

| Parameter | Default | Meaning |
|---|---:|---|
| Rated phase current | 50 A | Assumed, not verified nameplate |
| Rated phase-to-neutral voltage | 260 V | Assumed |
| Rated oil rise | 40 C | Needs calibration |
| Loss ratio / oil exponent | 5 / 0.8 | Assumed model coefficients |
| Time constant | 10800 s | 3 h, needs calibration |
| Initial oil / ambient | 55 / 30 C | Assumed initial condition |
| Oil warning / critical | 85 / 100 C | Demo thresholds, not trip settings |
| Current / voltage imbalance warning | 10 / 3% | Magnitude indicators |
| Residual warning / recovery | 8 / 4 C | Positive unexpected heating only |
| Persistence / recovery | 180 / 180 s | Continuous valid evidence |
| Maximum gap / freshness age | 300 s | Demo acquisition requirement |

## Explainable condition and confidence

Each contributor has a raw value, units, healthy limit, full-penalty point, weight and computed penalty. Penalty is `weight * clamp((value - healthy_limit)/(full_penalty_at - healthy_limit), 0, 1)`.

| Contributor | Healthy limit | Full penalty | Weight |
|---|---:|---:|---:|
| Maximum loading | 100% | 150% | 30 |
| Current imbalance | Configured warning | 3 times warning | 20 |
| Measured oil temperature | Oil warning | Oil critical | 30 |
| Positive temperature residual | Recovery threshold | 2 times warning | 20 |

`health_index = 100 - sum(penalties)` only when all four contributors are available. Missing evidence gives a null score. Status is unknown when score is missing or confidence is below 0.8; otherwise healthy at 80–100, warning at 50–80, critical below 50. Alert lifecycle is independent of the score, so C must display alerts even when the heuristic status is healthy. Voltage imbalance has a separate alert and is not included in this four-contributor score.

Confidence is the fraction of four usable input groups (currents, voltages, oil, ambient). Rejected timestamps or an invalid thermal state set confidence to zero. Missing values never improve health. This is an availability indicator; it does not measure prediction accuracy, sensor calibration or physical reliability.

## Persistence and recovery

Alert types: overload, current imbalance, voltage imbalance, high oil temperature, unexpected heating, data unavailable. Threshold evidence must remain above trigger for the configured persistence duration. Recovery must remain strictly below the lower recovery threshold for the configured recovery duration. A first qualifying sample starts a timer at zero; a subsequent qualifying sample credits the elapsed interval only if both endpoints qualify. Dead-band samples reset recovery without closing the incident. Missing evidence and excessive gaps reset timers without resolving existing incidents. Labels are never detector inputs.

Overload recovery is 95%; imbalance recovery is 80% of its trigger; oil recovery is warning minus 5 C. Data-unavailable evidence is `1 - input_coverage`, triggers above zero and recovers below 0.01. No timestamped samples means no new detector transitions: A must expose feed silence/stale state to C rather than reusing old samples to advance timers.

## Forecasts and what-if comparisons

Profiles specify duration, thermal loading K, ambient and an optional cooling factor `c` in `[0.2, 2]`. For scenario forecasts only, use `rise_target/c` and `tau/c`. This is a heuristic sensitivity control for assumed cooling changes, not a calibrated fan or radiator model. The healthy baseline update always uses `c=1`.

Forecasts use steps of at most 60 s, report the initial point, final/peak temperature and first warning crossing at this sampling resolution. All comparison scenarios must have the same horizon and start from the same state; the first is the named baseline. Returned deltas compare final temperature to that baseline, with profiles retained as evidence. The module does not optimize actions.

For an **action comparison**, create a separate `ThermalState` from the latest valid measured oil temperature (`forecast_initial_oil_temp_c`) to account for current heat, without altering the healthy twin. State the cooling assumption: an unexplained residual does not prove a cooling fault, nor does healthy-cooling continuation predict an unresolved fault reliably. Include an explicit impaired-cooling scenario where appropriate. For a **healthy expected-temperature forecast**, use `engine.state`. C must label both as estimated, show starting temperature and assumptions, and never present them as measured or guaranteed outcomes. There is no calibrated uncertainty interval.
