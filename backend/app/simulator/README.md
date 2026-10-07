# Telemetry Simulator

This directory contains the synthetic telemetry generator and playback engine managed by **Person A (Backend Engineer)**.

## Purpose & Scope
- Emulate 3-phase electrical readings (voltage, current) and physical sensor signals (temperatures, oil levels) conforming strictly to `docs/contracts/telemetry-contract.md`.
- Support configurable replay scenarios: normal load cycles, harmonic distortions, thermal overloads, and cooling anomalies.
- **Architectural Boundary**: Simulation ground-truth fault labels (e.g., synthetic fault injection parameters) are logged separately for benchmark evaluation and are never injected into raw telemetry payloads delivered to Person B's detector models.
