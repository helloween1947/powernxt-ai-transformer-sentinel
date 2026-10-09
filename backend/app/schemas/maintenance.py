"""Provisional sample-alert contract; genuine detector alerts are not accepted yet."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from backend.app.schemas.assets import StrictSchema, UTCDateTime

TaskStatus = Literal["open", "in_progress", "completed", "cancelled"]
OperatorName = Annotated[str, Field(min_length=1, max_length=100)]


class SampleAlert(StrictSchema):
    source: Literal["sample"]
    alert_id: str = Field(min_length=1, max_length=100, pattern=r"^sample-[A-Za-z0-9._-]+$")
    asset_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    summary: str = Field(min_length=1, max_length=500)


class TaskCreate(StrictSchema):
    alert: SampleAlert
    action: str = Field(min_length=1, max_length=1000)
    owner: OperatorName | None = None


class TaskUpdate(StrictSchema):
    expected_version: int = Field(ge=1, strict=True)
    owner: OperatorName | None = None
    status: TaskStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def valid_update(self):
        changes = self.model_fields_set - {"expected_version"}
        if not changes:
            raise ValueError("Include owner, status or notes")
        if "status" in changes and self.status is None:
            raise ValueError("status cannot be null")
        if "notes" in changes and self.notes is None:
            raise ValueError("notes cannot be null; use an empty string to clear draft notes")
        if self.status in ("completed", "cancelled") and not self.notes:
            raise ValueError("Completion requires notes; cancellation requires a reason in notes")
        return self


class TaskResponse(StrictSchema):
    id: UUID
    asset_id: str
    alert: SampleAlert
    action: str
    status: TaskStatus
    created_at: UTCDateTime
    owner: str | None
    notes: str
    version: int
    updated_at: UTCDateTime


class TaskPage(StrictSchema):
    items: list[TaskResponse]
    limit: int
    offset: int


class TaskHistoryResponse(StrictSchema):
    id: int
    task_id: UUID
    version: int
    event_type: Literal["created", "legacy_import", "updated"]
    previous_status: TaskStatus | None
    new_status: TaskStatus
    previous_owner: str | None
    new_owner: str | None
    previous_notes: str | None
    notes: str
    actor: str | None
    identity_source: Literal["demo_header", "unattributed_creation", "legacy_import"]
    created_at: UTCDateTime


class TaskHistoryPage(StrictSchema):
    items: list[TaskHistoryResponse]
    limit: int
    offset: int
