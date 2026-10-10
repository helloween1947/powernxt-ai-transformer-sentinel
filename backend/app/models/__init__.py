"""Import every model so Alembic sees both worker and maintenance metadata."""

from backend.app.models.analytics import (
    AnalyticsResult,
    AnalyticsState,
    AnalyticsStream,
)
from backend.app.models.assets import Asset, AssetConfiguration
from backend.app.models.incidents import (
    DetectorControl,
    DetectorEpoch,
    Incident,
    IncidentDelivery,
    IncidentEvent,
    IncidentEvidence,
    IncidentOperation,
    Operator,
)
from backend.app.models.maintenance import MaintenanceTask, MaintenanceTaskHistory
from backend.app.models.telemetry import ProcessingJob, TelemetryReading
from backend.app.models.what_if import WhatIfSnapshot

__all__ = [
    "AnalyticsResult",
    "AnalyticsState",
    "AnalyticsStream",
    "Asset",
    "AssetConfiguration",
    "DetectorControl",
    "DetectorEpoch",
    "Incident",
    "IncidentDelivery",
    "IncidentEvent",
    "IncidentEvidence",
    "IncidentOperation",
    "MaintenanceTask",
    "MaintenanceTaskHistory",
    "Operator",
    "ProcessingJob",
    "TelemetryReading",
    "WhatIfSnapshot",
]
