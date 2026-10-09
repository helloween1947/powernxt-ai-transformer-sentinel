"""Sample task persistence using A's asset lock and transaction conventions."""

from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.maintenance import MaintenanceTask, MaintenanceTaskHistory
from backend.app.schemas.maintenance import SampleAlert, TaskCreate, TaskResponse, TaskUpdate, TaskHistoryResponse
from backend.app.services.assets import require_asset


class TaskConflict(Exception):
    pass


class TaskNotFound(Exception):
    pass


class TaskUpdateConflict(Exception):
    pass


class InvalidTaskUpdate(Exception):
    pass


ALLOWED_TRANSITIONS = {
    "open": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def response_for(task: MaintenanceTask) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        asset_id=task.asset_id,
        alert=SampleAlert(source=task.alert_source, alert_id=task.alert_id,
                          asset_id=task.asset_id, summary=task.alert_summary),
        action=task.action, status=task.status, created_at=task.created_at,
        owner=task.owner, notes=task.notes, version=task.version, updated_at=task.updated_at,
    )


def create_task(db: Session, payload: TaskCreate) -> tuple[TaskResponse, bool]:
    # Serialize same-asset retries before checking the unique alert identity.
    require_asset(db, payload.alert.asset_id, lock=True)
    task = db.scalar(select(MaintenanceTask).where(
        MaintenanceTask.asset_id == payload.alert.asset_id,
        MaintenanceTask.alert_source == payload.alert.source,
        MaintenanceTask.alert_id == payload.alert.alert_id,
    ))
    if task is not None:
        if task.alert_summary != payload.alert.summary or task.action != payload.action:
            raise TaskConflict
        # An explicitly supplied owner must match on retry. Omitting owner keeps
        # original D001 requests valid after assignment or subsequent updates.
        if "owner" in payload.model_fields_set and task.owner != payload.owner:
            raise TaskConflict
        result = response_for(task)
        db.commit()
        return result, False
    task = MaintenanceTask(
        id=str(uuid4()), asset_id=payload.alert.asset_id, alert_source=payload.alert.source,
        alert_id=payload.alert.alert_id, alert_summary=payload.alert.summary,
        action=payload.action, status="open", owner=payload.owner, notes="", version=1,
    )
    db.add(task)
    db.flush()
    db.add(MaintenanceTaskHistory(
        task_id=task.id, version=1, event_type="created", previous_status=None,
        new_status="open", previous_owner=None, new_owner=task.owner,
        previous_notes=None, notes="", actor=None, identity_source="unattributed_creation",
        created_at=task.created_at,
    ))
    db.flush()
    result = response_for(task)
    db.commit()
    return result, True


def get_task(db: Session, task_id: str) -> TaskResponse:
    task = db.get(MaintenanceTask, task_id)
    if task is None:
        raise TaskNotFound
    return response_for(task)


def list_tasks(db: Session, asset_id: str | None, limit: int, offset: int):
    statement = select(MaintenanceTask)
    if asset_id is not None:
        require_asset(db, asset_id)
        statement = statement.where(MaintenanceTask.asset_id == asset_id)
    rows = db.scalars(statement.order_by(MaintenanceTask.created_at, MaintenanceTask.id)
                      .limit(limit).offset(offset))
    return [response_for(row) for row in rows]


def require_task(db: Session, task_id: str, *, lock=False) -> MaintenanceTask:
    statement = select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    if lock:
        statement = statement.with_for_update()
    task = db.scalar(statement)
    if task is None:
        raise TaskNotFound
    return task


def update_task(db: Session, task_id: str, payload: TaskUpdate, actor: str) -> TaskResponse:
    task = require_task(db, task_id, lock=True)
    if task.version != payload.expected_version:
        raise TaskUpdateConflict("Task changed; retrieve its latest version before updating")
    if task.status in ("completed", "cancelled"):
        raise TaskUpdateConflict("Completed and cancelled tasks are read-only")
    changes = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    status = changes.get("status", task.status)
    if status != task.status and status not in ALLOWED_TRANSITIONS[task.status]:
        raise TaskUpdateConflict("Status transition is not allowed")
    owner = changes.get("owner", task.owner)
    notes = changes.get("notes", task.notes)
    if status in ("in_progress", "completed") and owner is None:
        raise InvalidTaskUpdate("Assign an owner before starting or completing a task")
    if (status, owner, notes) == (task.status, task.owner, task.notes):
        raise InvalidTaskUpdate("Update does not change the task")
    now = datetime.now(timezone.utc)
    history = MaintenanceTaskHistory(
        task_id=task.id, version=task.version + 1, event_type="updated",
        previous_status=task.status, new_status=status, previous_owner=task.owner,
        new_owner=owner, previous_notes=task.notes, notes=notes,
        actor=actor, identity_source="demo_header", created_at=now,
    )
    task.status, task.owner, task.notes = status, owner, notes
    task.version += 1
    task.updated_at = now
    db.add(history)
    db.flush()
    result = response_for(task)
    # Task and history are committed together. A failed insert rolls back both.
    db.commit()
    return result


def task_history(db: Session, task_id: str, limit: int, offset: int):
    require_task(db, task_id)
    rows = db.scalars(select(MaintenanceTaskHistory)
        .where(MaintenanceTaskHistory.task_id == task_id)
        .order_by(MaintenanceTaskHistory.version).limit(limit).offset(offset))
    return [TaskHistoryResponse.model_validate(row) for row in rows]
