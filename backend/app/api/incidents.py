"""Incident APIs use trusted opaque credentials, never client asserted actors."""

import hashlib
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.api.validation import original_payload
from backend.app.db.session import get_db
from backend.app.models.analytics import AnalyticsResult
from backend.app.models.assets import Asset
from backend.app.models.incidents import (
    Incident,
    IncidentEvent,
    IncidentEvidence,
    Operator,
)
from backend.app.schemas.incidents import (
    Acknowledgement,
    ControlResponse,
    ErrorResponse,
    EventPage,
    EvidencePage,
    ExactResultResponse,
    Handover,
    IncidentPage,
    IncidentResponse,
    OperatorResponse,
)
from backend.app.services import incidents


class IncidentRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def wrapped(request):
            try:
                return await handler(request)
            except incidents.IncidentError as exc:
                return JSONResponse(
                    status_code=exc.status,
                    content=ErrorResponse(
                        code=exc.code,
                        message=exc.message,
                        current_version=exc.current_version,
                    ).model_dump(mode="json"),
                    headers={"WWW-Authenticate": "Bearer"}
                    if exc.status == 401
                    else None,
                )
            except (RequestValidationError, HTTPException):
                return JSONResponse(
                    status_code=422,
                    content=ErrorResponse(
                        code="invalid_request",
                        message="Request does not match the versioned incident contract",
                    ).model_dump(),
                )
            except SQLAlchemyError:
                return JSONResponse(
                    status_code=503,
                    content=ErrorResponse(
                        code="database_unavailable",
                        message="Incident database operation unavailable",
                    ).model_dump(),
                )

        return wrapped


router = APIRouter(
    prefix="/api/v1",
    tags=["Incidents"],
    route_class=IncidentRoute,
    responses={s: {"model": ErrorResponse} for s in (401, 403, 404, 409, 422, 503)},
)
Database = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False, scheme_name="IncidentBearer")


def trusted_actor(
    db: Database,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    if credentials is None or len(credentials.credentials) > 256:
        raise incidents.IncidentError(
            401, "unauthenticated", "Valid bearer credential required"
        )
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    # Lock actor for the entire request; revoke/expiry changes serialize with mutations.
    actor = db.scalar(
        select(Operator)
        .where(
            Operator.token_hash == token_hash,
            Operator.active.is_(True),
            Operator.expires_at > func.clock_timestamp(),
        )
        .with_for_update()
    )
    if actor is None:
        raise incidents.IncidentError(
            401, "unauthenticated", "Valid bearer credential required"
        )
    return actor


def operator(actor: Annotated[Operator, Depends(trusted_actor)]):
    if actor.role not in ("operator", "admin"):
        raise incidents.IncidentError(403, "forbidden", "Operator role required")
    return actor


def administrator(actor: Annotated[Operator, Depends(trusted_actor)]):
    if actor.role != "admin":
        raise incidents.IncidentError(403, "forbidden", "Administrator role required")
    return actor


Actor = Annotated[Operator, Depends(trusted_actor)]


@router.get("/operators/me", response_model=OperatorResponse)
def identity(actor: Actor):
    return OperatorResponse(
        actor_ref=actor.id,
        name=actor.name,
        role=actor.role,
        expires_at=actor.expires_at,
    )


@router.get("/analytics/results/{result_id}", response_model=ExactResultResponse)
def exact_result(result_id: Annotated[int, Path(gt=0)], db: Database, actor: Actor):
    result = db.get(AnalyticsResult, result_id)
    if result is None:
        raise incidents.IncidentError(
            404, "result_not_found", "Stored analytics result not found"
        )
    return ExactResultResponse(result=result)


@router.get("/incidents", response_model=IncidentPage)
def list_incidents(
    db: Database,
    actor: Actor,
    asset_id: str,
    source: Literal["device", "simulator", "file_replay"],
    run_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    condition_status: Literal["active", "recovered"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
):
    if (source == "device") != (run_id is None):
        raise incidents.IncidentError(
            422, "invalid_stream", "Device uses null run; simulator/replay require run"
        )
    if db.get(Asset, asset_id) is None:
        raise incidents.IncidentError(404, "asset_not_found", "Asset not found")
    query = select(Incident).where(
        Incident.asset_id == asset_id,
        Incident.measurement_source == source,
        Incident.run_key == (run_id or ""),
    )
    if condition_status:
        query = query.where(Incident.condition_status == condition_status)
    if cursor:
        query = query.where(Incident.id > cursor)
    rows = db.scalars(query.order_by(Incident.id).limit(limit + 1)).all()
    return IncidentPage(
        items=[incidents.serialize(r) for r in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
def read_incident(incident_id: UUID, db: Database, actor: Actor):
    return incidents.serialize(incidents.get_incident(db, incident_id))


@router.get("/incidents/{incident_id}/evidence", response_model=EvidencePage)
def evidence(
    incident_id: UUID,
    db: Database,
    actor: Actor,
    cursor: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    incidents.get_incident(db, incident_id)
    rows = db.scalars(
        select(IncidentEvidence)
        .where(
            IncidentEvidence.incident_id == incident_id,
            IncidentEvidence.incident_version > cursor,
        )
        .order_by(IncidentEvidence.incident_version)
        .limit(limit + 1)
    ).all()
    return EvidencePage(
        items=[
            {
                "evidence_id": r.id,
                "incident_id": r.incident_id,
                "incident_version": r.incident_version,
                "recorded_at": r.recorded_at,
                "payload": r.payload,
            }
            for r in rows[:limit]
        ],
        next_cursor=rows[limit - 1].incident_version if len(rows) > limit else None,
    )


@router.get("/incidents/{incident_id}/events", response_model=EventPage)
def events(
    incident_id: UUID,
    db: Database,
    actor: Actor,
    cursor: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    incidents.get_incident(db, incident_id)
    rows = db.scalars(
        select(IncidentEvent)
        .where(
            IncidentEvent.incident_id == incident_id,
            IncidentEvent.incident_version > cursor,
        )
        .order_by(IncidentEvent.incident_version)
        .limit(limit + 1)
    ).all()
    return EventPage(
        items=rows[:limit],
        next_cursor=rows[limit - 1].incident_version if len(rows) > limit else None,
    )


@router.post(
    "/incidents/{incident_id}/acknowledgements",
    response_model=IncidentResponse,
    status_code=201,
    dependencies=[Depends(original_payload)],
)
def acknowledge(
    incident_id: UUID,
    payload: Acknowledgement,
    db: Database,
    response: Response,
    actor: Annotated[Operator, Depends(operator)],
):
    result, created = incidents.acknowledge(
        db, incident_id, payload, actor, db.scalar(select(func.clock_timestamp()))
    )
    response.status_code = 201 if created else 200
    return result


@router.post(
    "/assets/{asset_id}/detector-handovers",
    response_model=ControlResponse,
    status_code=201,
    dependencies=[Depends(original_payload)],
)
def handover(
    asset_id: str,
    payload: Handover,
    db: Database,
    response: Response,
    actor: Annotated[Operator, Depends(administrator)],
):
    result, created = incidents.handover(
        db, asset_id, payload, actor, db.scalar(select(func.clock_timestamp()))
    )
    response.status_code = 201 if created else 200
    return result
