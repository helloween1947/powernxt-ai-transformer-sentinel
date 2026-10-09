"""Lease-fenced jobs share a stream watermark and versioned model namespaces."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
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


class AnalyticsStream(Base):
    __tablename__ = "analytics_streams"
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_id", ondelete="RESTRICT"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(20), primary_key=True)
    run_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    watermark_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    watermark_reading_id: Mapped[int | None] = mapped_column(
        ForeignKey("telemetry_readings.id", ondelete="RESTRICT")
    )
    last_identity: Mapped[str | None] = mapped_column(String(400))
    active_token: Mapped[object | None] = mapped_column(Uuid)
    active_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("telemetry_processing_jobs.id", ondelete="RESTRICT")
    )
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    advances: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class AnalyticsState(Base):
    __tablename__ = "analytics_states"
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
            ["asset_id", "configuration_version"],
            ["asset_configurations.asset_id", "asset_configurations.version"],
            ondelete="RESTRICT",
        ),
    )
    asset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(String(20), primary_key=True)
    run_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    model_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    configuration_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    parameter_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON)
    advances: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AnalyticsResult(Base):
    __tablename__ = "analytics_results"
    __table_args__ = (
        UniqueConstraint(
            "reading_id",
            "model_id",
            "model_version",
            "parameter_version",
            name="uq_analytics_result_identity",
        ),
        CheckConstraint(
            "status IN ('completed', 'unavailable')", name="ck_analytics_result_status"
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reading_id: Mapped[int] = mapped_column(
        ForeignKey("telemetry_readings.id", ondelete="RESTRICT")
    )
    model_id: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(100))
    parameter_version: Mapped[str] = mapped_column(String(100))
    schema_version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
