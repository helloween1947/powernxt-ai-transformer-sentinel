"""Separate sample identities and canonical incident linkages; retain task history."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, BigInteger, Uuid, ForeignKeyConstraint, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    __table_args__ = (
        UniqueConstraint("asset_id", "alert_source", "alert_id", name="uq_task_sample_alert"),
        CheckConstraint("status IN ('open', 'in_progress', 'completed', 'cancelled')", name="ck_task_status"),
        CheckConstraint("(alert_source = 'sample' AND incident_id IS NULL AND incident_evidence_id IS NULL AND creation_request IS NULL AND created_by_id IS NULL) OR (alert_source = 'analytics' AND incident_id IS NOT NULL AND incident_evidence_id IS NOT NULL AND creation_request IS NOT NULL AND created_by_id IS NOT NULL)", name="ck_task_reference"),
        ForeignKeyConstraint(["incident_id", "asset_id"], ["incidents.id", "incidents.asset_id"], ondelete="RESTRICT", name="fk_task_incident_asset"),
        UniqueConstraint("incident_id", name="uq_task_incident"),
        CheckConstraint("version > 0", name="ck_task_version"),
        CheckConstraint("status NOT IN ('in_progress', 'completed') OR (owner IS NOT NULL AND length(trim(owner)) > 0)", name="ck_task_owner_required"),
        CheckConstraint("status NOT IN ('completed', 'cancelled') OR length(trim(notes)) > 0", name="ck_task_terminal_notes"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.asset_id", ondelete="RESTRICT"), index=True)
    incident_id: Mapped[UUID | None] = mapped_column(Uuid)
    incident_evidence_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("incident_evidence.id", ondelete="RESTRICT"))
    created_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("incident_operators.id", ondelete="RESTRICT"))
    creation_request: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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
        CheckConstraint("(identity_source = 'authenticated_operator' AND actor_id IS NOT NULL AND actor IS NOT NULL AND actor = actor_id::text) OR (identity_source IN ('demo_header','unattributed_creation','legacy_import') AND actor_id IS NULL)", name="ck_task_history_attribution"),
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
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("incident_operators.id", ondelete="RESTRICT"))
    identity_source: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
