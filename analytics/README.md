# Analytics & Digital Twin Subsystem

**Owner**: Person B (Model Engineer / Data Scientist)

## Adopted runtime versus research roadmap

Main's backend uses the vendored conservative model described by the
[result contract](../docs/contracts/analytics-contract.md) and
[worker policy](../docs/analytics-worker.md): magnitude electrical metrics and
simplified top-oil prediction/residual, with explicit unavailable quantities.
The adopted entry point is compute_analytics, not the historical process_reading
proposal below. Assumed coefficients and synthetic demonstrations do not certify
physical calibration, fault probability or IEEE standards compliance.

Model1.0.2 and the full B audit/planner lineage remain separately reviewed branch
work until A/B record adoption and state-namespace/handover policy. Incident
contract artifacts on main do not mean incident storage or a publisher is deployed.
See the [D alignment follow-up](../docs/persond-team-alignment-followup.md).

The following broader scope and function signature are a research roadmap and
historical proposal; they are not implemented capability claims.

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

## Person B reviewed implementation and adoption

The [Person B component reference](person-b-component-reference.md) preserves the
reviewed callable interfaces and separates them from the historical roadmap above.
See [10 October alignment review](docs/person-b-alignment-review-20261010.md),
[exact model1.0.2 adoption handoff](docs/model-1.0.2-adoption-handoff.md) and
[source/hash manifest](docs/model-1.0.2-adoption-manifest.json). B recommends
recorded cold start and version-specific historical What-if computation; A owns
final adoption/API decisions. No model adoption, deployment or teammate approval
is implied by these references. PR24 already includes PR17 lineage.
