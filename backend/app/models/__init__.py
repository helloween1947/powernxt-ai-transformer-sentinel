"""Import every model so Alembic sees both worker and maintenance metadata."""

from backend.app.models.analytics import (
    AnalyticsResult,
    AnalyticsState,
    AnalyticsStream,
)
from backend.app.models.assets import Asset, AssetConfiguration
from backend.app.models.maintenance import MaintenanceTask, MaintenanceTaskHistory
from backend.app.models.telemetry import ProcessingJob, TelemetryReading
from backend.app.models.incidents import (Operator, DetectorEpoch, DetectorControl,
                                        Incident, IncidentEvidence, IncidentEvent, IncidentOperation)

__all__ = [
    "AnalyticsResult",
    "AnalyticsState",
    "AnalyticsStream",
    "Asset",
    "AssetConfiguration",
    "MaintenanceTask",
    "MaintenanceTaskHistory",
    "ProcessingJob",
    "TelemetryReading",
    "Operator", "DetectorEpoch", "DetectorControl", "Incident",
    "IncidentEvidence", "IncidentEvent", "IncidentOperation",
]
