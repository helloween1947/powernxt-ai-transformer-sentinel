# Sample Data Directory

This directory stores representative datasets and test payloads for the Transformer Sentinel project.

## Files
- `telemetry-sample.json`: A single valid sample telemetry reading conforming strictly to `docs/contracts/telemetry-contract.md`.
  - Values represent realistic synthetic 3-phase measurements.
  - Fault labels and ground-truth simulation parameters are intentionally excluded to ensure realistic detector evaluation.

## Telemetry ingestion examples

`telemetry-sample.json` uses a synthetic simulator run; `telemetry-device-sample.json`
illustrates a live device envelope with missing channels. Both require a registered asset
and explicit existing configuration version before submission.
`telemetry-response-sample.json` illustrates the API response; its IDs/times are invented
examples, not executed verification results. Missing measurements remain null. No sample
contains fault ground truth. See `docs/contracts/telemetry-contract.md`.
