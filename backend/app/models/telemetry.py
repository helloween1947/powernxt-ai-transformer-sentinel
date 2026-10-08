"""Durable raw/normalized readings and a transactional processing-job outbox."""

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
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["asset_id", "configuration_version"],
            ["asset_configurations.asset_id", "asset_configurations.version"],
            name="fk_telemetry_configuration",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "asset_id", "source", "run_key", "message_id", name="uq_telemetry_delivery"
        ),
        CheckConstraint("schema_version = '1.0.0'", name="ck_telemetry_schema"),
        CheckConstraint(
            "(source = 'device' AND run_key = '') OR (source IN ('simulator', 'file_replay') AND run_key <> '')",
            name="ck_telemetry_stream",
        ),
        Index(
            "ix_telemetry_stream_time",
            "asset_id",
            "source",
            "run_key",
            "measurement_time",
            "id",
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(100))
    configuration_version: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[str] = mapped_column(String(20))
    message_id: Mapped[UUID] = mapped_column(Uuid)
    source: Mapped[str] = mapped_column(String(20))
    # Non-null sentinel gives device streams reliable PostgreSQL uniqueness.
    run_key: Mapped[str] = mapped_column(String(100))
    measurement_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    arrival_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    original_payload: Mapped[dict] = mapped_column(JSON)
    payload_fingerprint: Mapped[str] = mapped_column(String(64))
    normalized_telemetry: Mapped[dict] = mapped_column(JSON)
    quality_flags: Mapped[dict] = mapped_column(JSON)
    out_of_order: Mapped[bool] = mapped_column(Boolean)


class ProcessingJob(Base):
    __tablename__ = "telemetry_processing_jobs"
    __table_args__ = (
        CheckConstraint("status = 'pending'", name="ck_telemetry_job_pending"),
        CheckConstraint(
            "state_policy IN ('forward_only', 'historical_only')",
            name="ck_telemetry_job_policy",
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reading_id: Mapped[int] = mapped_column(
        ForeignKey("telemetry_readings.id", ondelete="RESTRICT"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    state_policy: Mapped[str] = mapped_column(String(20))
