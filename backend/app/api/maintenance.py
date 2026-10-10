"""Sample/genuine task workflows; incident acknowledgement stays independent."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from backend.app.api.incidents import bearer, trusted_actor, operator
from backend.app.services.incidents import IncidentError
from backend.app.schemas.incidents import ErrorResponse
from backend.app.api.validation import original_payload
from backend.app.db.session import get_db
from backend.app.schemas.maintenance import TaskCreate, TaskPage, TaskResponse, TaskUpdate, TaskHistoryPage
from backend.app.services import maintenance
from backend.app.services.assets import AssetNotFound

class MaintenanceRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def wrapped(request):
            try:
                return await handler(request)
            except IncidentError as exc:
                return JSONResponse(status_code=exc.status,
                    content=ErrorResponse(code=exc.code, message=exc.message, current_version=exc.current_version).model_dump(mode="json"),
                    headers={"WWW-Authenticate": "Bearer"} if exc.status == 401 else None)
        return wrapped

Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]

def genuine_actor(db, credentials, *, mutation=False):
    actor = trusted_actor(db, credentials)
    return operator(actor) if mutation else actor


router = APIRouter(route_class=MaintenanceRoute, prefix="/api/v1/maintenance/tasks", tags=["Maintenance"])


def maintenance_db(db: Annotated[Session, Depends(get_db)]):
    try:
        yield db
    except AssetNotFound:
        db.rollback()
        raise HTTPException(404, "Asset not found") from None
    except maintenance.TaskNotFound:
        db.rollback()
        raise HTTPException(404, "Maintenance task not found") from None
    except maintenance.TaskUpdateConflict as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from None
    except maintenance.InvalidTaskUpdate as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from None
    except (maintenance.TaskConflict, IntegrityError):
        db.rollback()
        raise HTTPException(409, "Alert already has a task with different creation content") from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, "Maintenance database operation unavailable") from None


Database = Annotated[Session, Depends(maintenance_db)]


def demo_actor(value: Annotated[str, Header(alias="X-Demo-Actor", max_length=100)]) -> str:
    """Prototype display label only; no authenticated session/operator model exists."""
    value = value.strip()
    if not value or any(ord(character) < 32 for character in value):
        raise HTTPException(422, "X-Demo-Actor must be a nonblank demo display name")
    return value


@router.post("", response_model=TaskResponse, status_code=201, dependencies=[Depends(original_payload)])
def create_task(payload: TaskCreate, response: Response, db: Database, credentials: Credentials):
    if payload.alert.source == "analytics":
        actor = genuine_actor(db, credentials, mutation=True)
        task, created = maintenance.create_incident_task(db, payload, actor)
    else:
        task, created = maintenance.create_task(db, payload)
    response.status_code = 201 if created else 200
    response.headers["Location"] = f"/api/v1/maintenance/tasks/{task.id}"
    return task


@router.get("", response_model=TaskPage)
def list_tasks(db: Database, credentials: Credentials, asset_id: str | None = None,
               source: Literal["sample", "analytics"] = "sample",
               limit: Annotated[int, Query(ge=1, le=100)] = 20,
               offset: Annotated[int, Query(ge=0)] = 0):
    if source == "analytics":
        genuine_actor(db, credentials)
    return TaskPage(items=maintenance.list_tasks(db, asset_id, limit, offset, source),
                    limit=limit, offset=offset)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID, db: Database, credentials: Credentials):
    task = maintenance.require_task(db, str(task_id))
    if task.incident_id is not None:
        genuine_actor(db, credentials)
    return maintenance.get_task(db, str(task_id))


@router.patch("/{task_id}", response_model=TaskResponse, dependencies=[Depends(original_payload)])
def update_task(task_id: UUID, payload: TaskUpdate, db: Database, credentials: Credentials,
                demo: Annotated[str | None, Header(alias="X-Demo-Actor", max_length=100)] = None):
    task = maintenance.require_task(db, str(task_id))
    if task.incident_id is not None:
        actor = genuine_actor(db, credentials, mutation=True)
        return maintenance.update_task(db, str(task_id), payload, str(actor.id), actor.id)
    if demo is None:
        raise HTTPException(422, "X-Demo-Actor required for sample task")
    return maintenance.update_task(db, str(task_id), payload, demo_actor(demo))


@router.get("/{task_id}/history", response_model=TaskHistoryPage)
def task_history(task_id: UUID, db: Database, credentials: Credentials,
                 limit: Annotated[int, Query(ge=1, le=100)] = 20,
                 offset: Annotated[int, Query(ge=0)] = 0):
    task = maintenance.require_task(db, str(task_id))
    if task.incident_id is not None:
        genuine_actor(db, credentials)
    return TaskHistoryPage(items=maintenance.task_history(db, str(task_id), limit, offset),
                           limit=limit, offset=offset)
