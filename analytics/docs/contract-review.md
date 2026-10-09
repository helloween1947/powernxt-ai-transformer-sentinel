# Person B review of the proposed analytics contract

Reviewed GitHub main commit `26efab6`, including implemented telemetry `1.0.0`, registry schemas, ingestion service and proposed analytics contract. This note records implementation decisions without editing the shared contract, for A/C/D to review during integration.

| Boundary | Implemented decision |
|---|---|
| Entrypoint | Exact `process_reading(reading, quality_flags, asset_config, previous_state=None)`; response adapter also enforces queued-job policy |
| Reading shape | `normalized_telemetry` with named channels inside `measurements`; never raw payload |
| Quality | Producer `good/suspect/bad/missing` and A's per-channel reason lists; suspect/bad/flagged values excluded, not clamped |
| Units | Bound current/voltage ratings and measurement side; oil time constant minutes converted to seconds |
| Voltage | Phase-neutral power sums V*I; line-line power is a labeled balanced-system approximation |
| Configuration | Exact ConfigurationResponse asset/version required; provenance retained; no latest lookup |
| Missing thermal fields | Null prediction/residual/forecast; missing parameter paths listed; sensor confidence independent |
| State | Asset/source/run isolation; historical-only policy and processed watermark both enforced |
| Config change | Reject forward reuse of old state; deliberately cold-start or replay with new bound config |
| Output | All eight proposed categorical keys present; unsupported evidence null and listed |
| Alerts | Persistent thresholds, hysteresis/recovery, evidence and lifecycle; stream-scoped IDs |

## Evidence requiring clarification in the proposed shared contract

RMS magnitude-only telemetry cannot uniquely determine sequence components, kW, kvar or power factor without phase angles or additional power channels. These stay null. `current_magnitude_imbalance_pct` and `voltage_magnitude_imbalance_pct` are explicitly named magnitude indicators, not negative-sequence ratios.

The model implements simplified first-order top-oil dynamics, not winding dynamics or insulation aging. Hot-spot, aging acceleration and loss-of-life stay null even if winding coefficients are supplied. RUL and normalized/probabilistic anomaly score also stay null. Unsupported quantities are listed under `execution_status.unavailable_estimates`. No IEEE standards-compliance claim is made.

`data_confidence` is an object with score, missing channels, reasons and oil-level availability. `condition_contributors` is an object with health index, status and contributor array. `execution_status` includes status, state advancement, policy, unavailable measurements/estimates and reasons. The proposed contract defines categories but not exact subfield types; these are concrete types for A/C/D to consume.

`computed` means the supported electrical/top-oil calculations are complete; permanently unsupported estimates still remain listed. `degraded` means partial supported results. `insufficient_data` means no complete current triplet or no eligible forward evaluation. State advancement is independent; all-null input may advance the processing watermark while yielding no valid model estimate.

## Versioned heuristic policy

`operational_limits.max_load_pct` controls overload; `max_top_oil_temp_c` controls oil-temperature alert. Null limits disable those alerts instead of silently inserting limits. A persistent configured top-oil maximum breach is critical; other observations are warning. Recovery is 95% of the configured load limit and 5 C below the configured oil limit.

Policy `threshold-persistence-1.0` uses current/voltage magnitude imbalance thresholds 10/3%, positive residual trigger/recovery 8/4 C, maximum continuity gap 300 s and persistence/recovery 180 s. These are explicit heuristics, not asset-nameplate parameters or calibrated probabilities. The health score's oil full-penalty margin is 15 C above the configured oil limit; it is not a protection setting. Loading score starts penalizing above 100% of rating, independently of an asset's maximum load limit. Other score equations are in `model.md`.

Data confidence counts eight usable required electrical/temperature channels. Oil level is optional and has no leakage detector. The first usable oil measurement establishes a trusted initial condition; an already-present initial sensor offset cannot be detected this way. Later oil measurements do not change the healthy baseline. Missing current/ambient history or large gaps invalidate it until deliberate replay/cold start. A/D should audit resets and retain existing incidents durably.

## Owner handoff

A/D must implement durable analytics storage, worker completion/error statuses and event publication; copy analytics into the backend container; and include `analytics/tests` in CI. Those facilities do not yet exist in the inspected backend. This contribution supplies their callable boundary and compatible fixtures without changing shared or teammate-owned files.
