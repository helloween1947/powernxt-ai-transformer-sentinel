"""One persisted task per asset and sample-alert identity."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    __table_args__ = (
        UniqueConstraint("asset_id", "alert_source", "alert_id", name="uq_task_sample_alert"),
        CheckConstraint("status IN ('open', 'in_progress', 'completed', 'cancelled')", name="ck_task_status"),
        CheckConstraint("alert_source = 'sample'", name="ck_task_sample_source"),
        CheckConstraint("version > 0", name="ck_task_version"),
        CheckConstraint("status NOT IN ('in_progress', 'completed') OR (owner IS NOT NULL AND length(trim(owner)) > 0)", name="ck_task_owner_required"),
        CheckConstraint("status NOT IN ('completed', 'cancelled') OR length(trim(notes)) > 0", name="ck_task_terminal_notes"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.asset_id", ondelete="RESTRICT"), index=True)
    alert_source: Mapped[str] = mapped_column(String(20))
    alert_id: Mapped[str] = mapped_column(String(100))
    alert_summary: Mapped[str] = mapped_column(String(500))
    action: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20))
    owner: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str] = mapped_column(String(2000), server_default="")
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaintenanceTaskHistory(Base):
    __tablename__ = "maintenance_task_history"
    __table_args__ = (
        UniqueConstraint("task_id", "version", name="uq_task_history_version"),
        CheckConstraint("version > 0", name="ck_task_history_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("maintenance_tasks.id", ondelete="RESTRICT"))
    version: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(20))
    previous_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20))
    previous_owner: Mapped[str | None] = mapped_column(String(100))
    new_owner: Mapped[str | None] = mapped_column(String(100))
    previous_notes: Mapped[str | None] = mapped_column(String(2000))
    notes: Mapped[str] = mapped_column(String(2000))
    actor: Mapped[str | None] = mapped_column(String(100))
    identity_source: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
