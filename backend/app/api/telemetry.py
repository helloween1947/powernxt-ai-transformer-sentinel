"""Ingestion and stream-isolated retrieval; all database errors are sanitized."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.api.validation import original_payload
from backend.app.db.session import get_db
from backend.app.schemas.telemetry import (
    Identifier,
    ISOTime,
    Source,
    TelemetryCreate,
    TelemetryPage,
    TelemetryResponse,
)
from backend.app.services import telemetry
from backend.app.services.assets import AssetNotFound

router = APIRouter(tags=["Telemetry"])


def telemetry_db(db: Annotated[Session, Depends(get_db)]):
    try:
        yield db
    except AssetNotFound:
        db.rollback()
        raise HTTPException(404, "Asset not found") from None
    except telemetry.ConfigurationNotFound:
        db.rollback()
        raise HTTPException(
            422, "Configuration version does not belong to this asset"
        ) from None
    except telemetry.ReadingNotFound:
        db.rollback()
        raise HTTPException(404, "No telemetry in the selected stream") from None
    except (telemetry.TelemetryConflict, IntegrityError):
        db.rollback()
        raise HTTPException(
            409, "Telemetry deduplication key conflicts with existing content"
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, "Telemetry database operation unavailable") from None


Database = Annotated[Session, Depends(telemetry_db)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def stream(source: Source = "device", run_id: Identifier | None = None):
    if (source == "device" and run_id is not None) or (
        source != "device" and run_id is None
    ):
        raise HTTPException(
            422, "device requires run_id=null; simulator/file_replay require run_id"
        )
    return source, run_id


Stream = Annotated[tuple, Depends(stream)]


@router.post(
    "/api/v1/telemetry",
    response_model=TelemetryResponse,
    status_code=201,
    responses={
        200: {
            "model": TelemetryResponse,
            "description": "Identical retry: original ingestion result",
        }
    },
)
def ingest(
    payload: TelemetryCreate,
    response: Response,
    db: Database,
    original: Annotated[dict, Depends(original_payload)],
):
    result, created = telemetry.ingest(db, payload, original)
    response.status_code = 201 if created else 200
    return result


@router.get(
    "/api/v1/assets/{asset_id}/telemetry/latest", response_model=TelemetryResponse
)
def latest(asset_id: str, db: Database, selected: Stream):
    return telemetry.latest(db, asset_id, *selected)


@router.get("/api/v1/assets/{asset_id}/telemetry", response_model=TelemetryPage)
def history(
    asset_id: str,
    db: Database,
    selected: Stream,
    start: ISOTime | None = None,
    end: ISOTime | None = None,
    limit: Limit = 20,
    offset: Offset = 0,
):
    if start is not None and end is not None and start >= end:
        raise HTTPException(422, "start must be before end (exclusive)")
    return TelemetryPage(
        items=telemetry.history(db, asset_id, *selected, start, end, limit, offset),
        limit=limit,
        offset=offset,
    )
