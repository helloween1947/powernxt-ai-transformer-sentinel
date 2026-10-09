# Durable analytics worker

Run `python -m backend.app.workers` as a separate process after migration `d730a91b4c22`. Compose service `worker` is enabled with `--profile analytics`. No API startup polling is used.

See [worker operations and policies](../../../docs/analytics-worker.md) and [Windows handoff](../../../docs/analytics-worker-windows.md).
