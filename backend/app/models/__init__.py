"""Import every model so Alembic can discover its metadata."""

from backend.app.models.assets import Asset, AssetConfiguration
from backend.app.models.telemetry import ProcessingJob, TelemetryReading
from backend.app.models.maintenance import MaintenanceTask, MaintenanceTaskHistory

__all__ = ["Asset", "AssetConfiguration", "ProcessingJob", "TelemetryReading", "MaintenanceTask", "MaintenanceTaskHistory"]
