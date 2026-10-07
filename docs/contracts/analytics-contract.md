# Analytics & Digital Twin Integration Contract

> **PROPOSED SPECIFICATION**: This contract defines the interface boundary between the backend ingestion pipeline (Person A) and the analytical twin models (Person B). It remains *Proposed* pending formal review and confirmation by **Person B**.

## 1. Primary Entrypoint Function

```python
def process_reading(
    reading: dict,
    quality_flags: dict,
    asset_config: dict,
    previous_state: dict | None = None,
) -> dict:
    """Processes a single validated telemetry frame against the physical digital twin

    and anomaly detection pipeline.

    Parameters:
        reading: Dictionary compliant with docs/contracts/telemetry-contract.md.
        quality_flags: Dictionary of preprocessing flags (e.g., {'stale': False, 'clamped': False}).
        asset_config: Transformer static nameplate parameters (rated MVA, cooling class, impedance).
        previous_state: Rolling state dictionary returned by the preceding call, or None on cold start.

    Returns:
        Structured result dictionary conforming to Section 2.
    """
    ...
```

## 2. Expected Output Categories

The returned dictionary from `process_reading(...)` is structured into 8 distinct categorical partitions:

1. **Electrical Metrics (`electrical_metrics`)**:
   - Symmetrical components: positive, negative, zero sequence voltages/currents.
   - 3-Phase unbalance ratio (%).
   - Apparent power ($S$), active power ($P$), reactive power ($Q$), and calculated power factor ($\cos\phi$).

2. **Thermal Prediction & Residual (`thermal_assessment`)**:
   - Estimated top-oil temperature (°C) from IEEE C57.91 thermal model.
   - Estimated winding hot-spot temperature (°C).
   - Thermal residual: $(\text{measured\_oil\_temp} - \text{predicted\_oil\_temp})$.

3. **Operational Condition Contributors (`condition_contributors`)**:
   - Thermal aging acceleration factor ($F_{AA}$).
   - Equivalent aging loss-of-life rate.
   - Load loading percentage relative to rated capacity.

4. **Separate Data Confidence (`data_confidence`)**:
   - Numerical score ($0.0 - 1.0$) indicating sensor coverage completeness and quality.
   - Missing signal penalties applied.

5. **Anomaly Observations (`anomaly_observations`)**:
   - List of detected anomalies with category, severity (`info`, `warning`, `critical`), and descriptive rationale.
   - Raw detector anomaly score ($0.0 - 1.0$) and threshold applied.

6. **Updated Model State (`updated_state`)**:
   - Opaque state dictionary to be stored by the backend and passed into the subsequent call for stateful filters (e.g. Kalman filter, rolling exponentially-weighted moving average).

7. **Model & Configuration Versions (`metadata`)**:
   - Model version string (e.g., `"thermal-v0.2.1"`, `"anomaly-v0.1.0"`).
   - Timestamp of evaluation.

8. **Calculation Status & Unavailable Evidence (`execution_status`)**:
   - Status code: `"computed"`, `"degraded"` (partial sensors), or `"insufficient_data"`.
   - List of unavailable measurement keys required for complete evaluation.
