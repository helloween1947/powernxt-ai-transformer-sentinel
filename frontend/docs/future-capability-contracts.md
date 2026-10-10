# Proposed frontend capability contracts

10 October 2026. **PROPOSED — NOT LIVE. Design proposals only: no new route, backend schema or calculation is implemented or called.** The capability registry exposes these states today so adding reviewed outputs will not require redesigning the workstation.

All future records should bind asset ID, source/run, measurement time in UTC, configuration version, reading ID (where applicable), schema/model/method version, parameter provenance, units, availability and reason codes. Nullable values stay null. Sensor data needs quality and mounting/measurement metadata; model results need assumptions and uncertainty meaning. Values must be finite and appropriately range validated. Calibration evidence and validated limits must be supplied by the backend owners.

| Capability | Required quantities/meaning | Minimum validation/provenance |
|---|---|---|
| Active power / power factor | kW and dimensionless PF; synchronized phase voltage/current with angle or genuine power meter channels | Meter convention, sign/direction, aggregation, quality; magnitude-only RMS cannot supply PF |
| Frequency / THD | Hz; voltage/current THD %, separately identified phase and harmonic definition | Sampling rate, bandwidth, harmonic orders, window, sensor calibration, valid denominator |
| Impedance / short-circuit | Verified nameplate percent impedance on declared voltage/kVA base; result MVA or kA with explicit boundary | Network/source impedance, method/standard/version, connection, units and assumptions; never infer arbitrary fault level |
| Winding / bushing temperatures | Actual °C channels, independently identified | Sensor type, location, calibration and quality; do not relabel oil temperature |
| Winding hot-spot / ageing | Estimated °C, ageing factor and cumulative loss of life with explicit meanings | Approved winding/thermal method, cooling state, loading history, parameters and uncertainty; top-oil-only model insufficient |
| Overload duration / thermal capacity | Permissible minutes, limiting quantity and declared capacity definition | Time-dependent validated model, initial thermal state, ambient/cooling, ratings, selected threshold; 120% is a hypothetical scenario input |
| Oil leakage | Sensor/inspection state: detected, not detected, unavailable | Evidence source, event time, quality, inspected asset and sensor method; low oil level alone is insufficient |
| Tank pressure | kPa with absolute/gauge convention | Sensor range/reference, location, quality and calibrated configured limits |
| Sensor response time | ms, independently distinguished from arrival delay or measurement age | Sensor/firmware metadata, specified test conditions and definition |
| Vibration / electrical-mechanical analysis | Unit declared: e.g. acceleration m/s² or RMS velocity mm/s; synchronized signal summaries | Sampling/bandwidth, axis/location, windows, validated relationship method; no causal inference from arbitrary correlation |
| Health index | Bounded score with explicit scale, assessed/not_assessed state and component breakdown | Validated methodology, contributing evidence, missing-data behavior, version/calibration; no UI-generated percentage |
| Fault prediction / RUL | Defined event probability/horizon; remaining time with unit and interval or assessed reason | Validated model population, history requirements, uncertainty/calibration and model provenance; not just a threshold breach |

## Operator workflows

A reviewed incident contract must return persisted incident/event IDs, asset/stream/configuration/reading/detector provenance, lifecycle state and history, authenticated actor evidence, permitted transitions and concurrency version. Acknowledgement cannot be inferred from local state. Genuine maintenance must bind a verified incident ID, retain history and authorization, and validate versioned transitions. The current backend sample-alert task contract is not genuine incident provenance.

A reviewed What-if contract should accept a baseline reading/configuration and hypothetical inputs (capacity loading %, ambient °C, duration minutes and cooling assumptions). It must return persisted scenario ID, schema/model/parameter versions, baseline binding, unit-validated result series, comparison semantics, availability/reasons, assumptions and uncertainty. A 120% preset requests a scenario; it supplies no general operating permission. Scenarios must never overwrite measured telemetry.

Potential route families such as incidents, incident-linked tasks and scenarios require backend-owner agreement, schema tests and authentication review before client implementation. No concrete proposed URL is wired into this frontend. Existing supported contracts are listed in [frontend README](../frontend/README.md).

## Frontend-only edition additions

Every section above is PROPOSED — NOT LIVE. Scientific calculations belong in reviewed backend models; sensor response is source metadata. Current workspace support is asset/configuration plus normalized telemetry. Optional legacy-compatible analytics and sample-maintenance clients are only enabled after the connected runtime's OpenAPI advertises their implemented route families; response adapters still validate actual fields.

A future sensor inventory requires sensor_id, asset/component binding, quantity/unit, mounting location, range/basis, specified_response_ms with test conditions, sample_interval_ms, calibration identity/date, source and availability. No installed identity, physical location or range is implied by the procedural visual. Separate transport delay uses actual arrival_time minus measurement_time, with clock limitations. Worker processing duration requires independently recorded started_at/finished_at or duration_ms; result created_at alone is insufficient.

Reactive power requires kvar and meter/phase-angle semantics. Authoritative health output requires a documented scale, method/version, time period, input/configuration binding, quality/coverage and uncertainty. The only frontend calculation in this iteration is the explicitly unvalidated condition-rating-prototype-v1 display policy, documented separately. It is never persisted or exported as an official score. Sensor and model outputs cannot be enabled by populating a UI descriptor alone.

Future output response pattern (proposal): identity {asset_id, source, run_id, configuration_version, reading_id, measurement_time}, schema_version, method/model/parameter versions, quantity/unit/value nullable, availability/reason_codes, source/quality, evaluated_at, assumptions and uncertainty meaning. Route names must be agreed and implemented later; no proposed URL is called now. Validation must establish consistent identity, finite values, measurement conventions, compatible units and documented method before rendering live values.
