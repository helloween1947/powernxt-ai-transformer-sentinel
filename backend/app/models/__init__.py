"""Import every model so Alembic sees both worker and maintenance metadata."""
from backend.app.models.analytics import AnalyticsResult, AnalyticsState, AnalyticsStream
from backend.app.models.assets import Asset, AssetConfiguration
from backend.app.models.maintenance import MaintenanceTask, MaintenanceTaskHistory
from backend.app.models.telemetry import ProcessingJob, TelemetryReading

__all__ = ["Asset", "AssetConfiguration", "ProcessingJob", "TelemetryReading", "AnalyticsResult", "AnalyticsState", "AnalyticsStream", "MaintenanceTask", "MaintenanceTaskHistory"]
