# Analytics & Digital Twin Subsystem

**Owner**: Person B (Model Engineer / Data Scientist)

## Scope & Responsibilities
- 3-Phase electrical physical models (symmetrical components, power factor, unbalance).
- Transformer thermal models (top-oil temperature estimation, winding hot-spot dynamics, thermal residuals).
- Anomaly detection algorithms (statistical deviations, threshold breaches, pattern drift).
- Transformer health index / condition assessment contributors.
- Forecasting models (load demand projection, temperature trajectories).

## Interface Contract
The integration interface connecting the backend ingestion pipeline to analytics models is formally defined in:
`docs/contracts/analytics-contract.md`

### Core Function Signature (Proposed)
```python
def process_reading(
    reading: dict,
    quality_flags: dict,
    asset_config: dict,
    previous_state: dict | None = None,
) -> dict:
    """Process single normalized telemetry reading and output condition metrics."""
    ...
```

*Note: This interface is marked as proposed until Person B reviews and confirms the contract.*
