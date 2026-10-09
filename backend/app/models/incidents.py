"""Canonical incidents; immutable evidence/events and independently trusted actors."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Operator(Base):
    __tablename__ = "incident_operators"
    __table_args__ = (
        CheckConstraint(
            "role IN ('reader','operator','admin')", name="ck_operator_role"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    role: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    active: Mapped[bool] = mapped_column(Boolean)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DetectorEpoch(Base):
    __tablename__ = "incident_detector_epochs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["asset_id", "configuration_version"],
            ["asset_configurations.asset_id", "asset_configurations.version"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "asset_id", "source", "run_key", name="uq_epoch_stream"),
        CheckConstraint(
            "(source='device' AND run_key='') OR (source IN ('simulator','file_replay') AND run_key<>'')",
            name="ck_epoch_stream",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(20))
    run_key: Mapped[str] = mapped_column(String(100))
    configuration_version: Mapped[int] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(100))
    parameter_version: Mapped[str] = mapped_column(String(100))
    detector_version: Mapped[str] = mapped_column(String(100))
    policy: Mapped[dict] = mapped_column(JSON)
    policy_fingerprint: Mapped[str] = mapped_column(String(64))
    context: Mapped[dict | None] = mapped_column(JSON)
    previous_twin_state: Mapped[dict | None] = mapped_column(JSON)
    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("incident_operators.id", ondelete="RESTRICT")
    )
    reason: Mapped[str] = mapped_column(String(1000))
    boundary_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DetectorControl(Base):
    __tablename__ = "incident_detector_controls"
    __table_args__ = (
        ForeignKeyConstraint(
            ["asset_id", "source", "run_key"],
            [
                "analytics_streams.asset_id",
                "analytics_streams.source",
                "analytics_streams.run_key",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["epoch_id", "asset_id", "source", "run_key"],
            [
                "incident_detector_epochs.id",
                "incident_detector_epochs.asset_id",
                "incident_detector_epochs.source",
                "incident_detector_epochs.run_key",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint("version>0", name="ck_detector_control_version"),
    )
    asset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(String(20), primary_key=True)
    run_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    epoch_id: Mapped[UUID] = mapped_column(Uuid)
    version: Mapped[int] = mapped_column(Integer)
    continuity_break: Mapped[bool] = mapped_column(Boolean)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        UniqueConstraint("id", "asset_id", name="uq_incident_asset"),
        UniqueConstraint(
            "asset_id",
            "detector_epoch",
            "detector_episode_key",
            name="uq_incident_mapping",
        ),
        ForeignKeyConstraint(
            ["detector_epoch", "asset_id", "measurement_source", "run_key"],
            [
                "incident_detector_epochs.id",
                "incident_detector_epochs.asset_id",
                "incident_detector_epochs.source",
                "incident_detector_epochs.run_key",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint("version>0", name="ck_incident_version"),
        CheckConstraint(
            "severity IN ('info','warning','critical')", name="ck_incident_severity"
        ),
        CheckConstraint(
            "(condition_status='active' AND recovered_at IS NULL) OR (condition_status='recovered' AND recovered_at IS NOT NULL)",
            name="ck_incident_condition",
        ),
        CheckConstraint(
            "monitoring_status IN ('monitoring','interrupted')",
            name="ck_incident_monitoring",
        ),
        CheckConstraint(
            "last_evidence_status IN ('available','unavailable')",
            name="ck_incident_evidence_status",
        ),
        CheckConstraint(
            "(acknowledged_at IS NULL AND actor_id IS NULL) OR (acknowledged_at IS NOT NULL AND actor_id IS NOT NULL)",
            name="ck_incident_ack",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_id", ondelete="RESTRICT")
    )
    measurement_source: Mapped[str] = mapped_column(String(20))
    run_key: Mapped[str] = mapped_column(String(100))
    detector_epoch: Mapped[UUID] = mapped_column(Uuid)
    detector_episode_key: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer)
    condition_status: Mapped[str] = mapped_column(String(20))
    monitoring_status: Mapped[str] = mapped_column(String(20))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_evaluated_measurement_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )
    last_evidence_status: Mapped[str] = mapped_column(String(20))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("incident_operators.id", ondelete="RESTRICT")
    )


class IncidentEvidence(Base):
    __tablename__ = "incident_evidence"
    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "result_id",
            "detector_version",
            "policy_fingerprint",
            name="uq_incident_evidence",
        ),
        UniqueConstraint(
            "incident_id", "incident_version", name="uq_incident_evidence_version"
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT")
    )
    incident_version: Mapped[int] = mapped_column(Integer)
    result_id: Mapped[int] = mapped_column(
        ForeignKey("analytics_results.id", ondelete="RESTRICT")
    )
    reading_id: Mapped[int] = mapped_column(
        ForeignKey("telemetry_readings.id", ondelete="RESTRICT")
    )
    detector_version: Mapped[str] = mapped_column(String(100))
    policy_fingerprint: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class IncidentEvent(Base):
    """Durable event/outbox records. No delivery transport is claimed."""

    __tablename__ = "incident_events"
    __table_args__ = (
        UniqueConstraint(
            "incident_id", "incident_version", name="uq_incident_event_version"
        ),
    )
    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT")
    )
    incident_version: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(50))
    evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("incident_evidence.id", ondelete="RESTRICT")
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("incident_operators.id", ondelete="RESTRICT")
    )
    payload: Mapped[dict] = mapped_column(JSON)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class IncidentOperation(Base):
    """Immutable receipts for acknowledgement and handover idempotency."""

    __tablename__ = "incident_operations"
    scope: Mapped[str] = mapped_column(String(250), primary_key=True)
    key: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("incident_operators.id", ondelete="RESTRICT")
    )
    fingerprint: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
