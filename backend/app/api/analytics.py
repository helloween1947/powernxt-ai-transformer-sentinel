"""Read committed analytical evidence; never compute inside an HTTP request."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from backend.app.api.telemetry import Database, stream
from backend.app.models.analytics import AnalyticsResult
from backend.app.models.telemetry import ProcessingJob, TelemetryReading
from backend.app.schemas.analytics import LatestAnalytics, ReadingAnalytics
from backend.app.schemas.telemetry import Identifier, Source
from backend.app.services.assets import require_asset
from backend.app.services.telemetry import stream_query

router = APIRouter(tags=["Analytics"])


def explicit_stream(source: Source, run_id: Identifier | None = None):
    return stream(source, run_id)


@router.get("/api/v1/telemetry/{reading_id}/analytics", response_model=ReadingAnalytics)
def reading_result(reading_id: int, db: Database):
    reading = db.get(TelemetryReading, reading_id)
    if reading is None:
        raise HTTPException(404, "Reading not found")
    job, result = db.execute(
        select(ProcessingJob, AnalyticsResult)
        .outerjoin(
            AnalyticsResult, AnalyticsResult.reading_id == ProcessingJob.reading_id
        )
        .where(ProcessingJob.reading_id == reading.id)
        .order_by(AnalyticsResult.id.desc())
        .limit(1)
    ).one()
    return ReadingAnalytics(
        reading_id=reading.id,
        configuration_version=reading.configuration_version,
        asset_id=reading.asset_id,
        source=reading.source,
        run_id=reading.run_key or None,
        measurement_time=reading.measurement_time,
        status=job.status,
        attempts=job.attempts,
        error_code=job.last_error,
        result=result,
    )


@router.get(
    "/api/v1/assets/{asset_id}/analytics/latest", response_model=LatestAnalytics
)
def latest_result(
    asset_id: str, db: Database, selected: Annotated[tuple, Depends(explicit_stream)]
):
    require_asset(db, asset_id)
    source, run_id = selected
    statement = stream_query(asset_id, source, run_id)
    latest = db.scalar(
        statement.order_by(
            TelemetryReading.measurement_time.desc(), TelemetryReading.id.desc()
        ).limit(1)
    )
    completed = db.execute(
        statement.add_columns(AnalyticsResult)
        .join(AnalyticsResult, AnalyticsResult.reading_id == TelemetryReading.id)
        .where(AnalyticsResult.status == "completed")
        .order_by(
            TelemetryReading.measurement_time.desc(),
            TelemetryReading.id.desc(),
            AnalyticsResult.id.desc(),
        )
        .limit(1)
    ).first()
    job = (
        db.scalar(select(ProcessingJob).where(ProcessingJob.reading_id == latest.id))
        if latest
        else None
    )
    reading, result = completed if completed else (None, None)
    return LatestAnalytics(
        asset_id=asset_id,
        source=source,
        run_id=run_id,
        latest_telemetry_reading_id=latest.id if latest else None,
        latest_telemetry_measurement_time=latest.measurement_time if latest else None,
        latest_telemetry_status=job.status if job else None,
        latest_completed_reading_id=reading.id if reading else None,
        latest_completed_measurement_time=reading.measurement_time if reading else None,
        result=result,
    )
