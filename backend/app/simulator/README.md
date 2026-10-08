# Synthetic normal-operation simulator

Run from the repository root with Python 3.12 and installed backend dependencies:

```powershell
python -m backend.app.simulator --help
```

This implementation generates a declared **synthetic normal operating envelope**, writes artifacts, and sends existing JSONL to the real ingestion API. It provides no fault scenarios, replay controls, analytics, or WebSocket delivery. Producer quality `good` means a present synthetic value, not verified physical truth. See [complete usage and assumptions](../../../docs/normal-operation-simulator.md) and [execution evidence](../../../docs/normal-operation-simulator-verification.md).
