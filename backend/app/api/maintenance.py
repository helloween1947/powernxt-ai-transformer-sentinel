"""Sample task creation, versioned updates and history; no alert acknowledgement."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.maintenance import TaskCreate, TaskPage, TaskResponse, TaskUpdate, TaskHistoryPage
from backend.app.services import maintenance
from backend.app.services.assets import AssetNotFound

router = APIRouter(prefix="/api/v1/maintenance/tasks", tags=["Maintenance (sample milestone)"])


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
        raise HTTPException(409, "Sample alert already has a task with different content") from None
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


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(payload: TaskCreate, response: Response, db: Database):
    task, created = maintenance.create_task(db, payload)
    response.status_code = 201 if created else 200
    response.headers["Location"] = f"/api/v1/maintenance/tasks/{task.id}"
    return task


@router.get("", response_model=TaskPage)
def list_tasks(db: Database, asset_id: str | None = None,
               limit: Annotated[int, Query(ge=1, le=100)] = 20,
               offset: Annotated[int, Query(ge=0)] = 0):
    return TaskPage(items=maintenance.list_tasks(db, asset_id, limit, offset),
                    limit=limit, offset=offset)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID, db: Database):
    return maintenance.get_task(db, str(task_id))


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: UUID, payload: TaskUpdate, db: Database,
                actor: Annotated[str, Depends(demo_actor)]):
    return maintenance.update_task(db, str(task_id), payload, actor)


@router.get("/{task_id}/history", response_model=TaskHistoryPage)
def task_history(task_id: UUID, db: Database,
                 limit: Annotated[int, Query(ge=1, le=100)] = 20,
                 offset: Annotated[int, Query(ge=0)] = 0):
    return TaskHistoryPage(items=maintenance.task_history(db, str(task_id), limit, offset),
                           limit=limit, offset=offset)
