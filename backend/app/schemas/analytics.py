"""Stored-result API envelope 1.0.0; computation retains Person B's wire version."""

from typing import Literal

from backend.app.schemas.assets import StrictSchema, UTCDateTime
from backend.app.schemas.telemetry import Source

JobStatus = Literal[
    "pending", "processing", "retry", "completed", "unavailable", "failed"
]


class StoredAnalytics(StrictSchema):
    id: int
    reading_id: int
    model_id: str
    model_version: str
    parameter_version: str
    schema_version: str
    status: Literal["completed", "unavailable"]
    payload: dict
    created_at: UTCDateTime


class ReadingAnalytics(StrictSchema):
    schema_version: Literal["1.0.0"] = "1.0.0"
    reading_id: int
    configuration_version: int
    asset_id: str
    source: Source
    run_id: str | None
    measurement_time: UTCDateTime
    status: JobStatus
    attempts: int
    error_code: str | None
    result: StoredAnalytics | None


class LatestAnalytics(StrictSchema):
    schema_version: Literal["1.0.0"] = "1.0.0"
    asset_id: str
    source: Source
    run_id: str | None
    latest_telemetry_reading_id: int | None
    latest_telemetry_measurement_time: UTCDateTime | None
    latest_telemetry_status: JobStatus | None
    latest_completed_reading_id: int | None
    latest_completed_measurement_time: UTCDateTime | None
    result: StoredAnalytics | None
