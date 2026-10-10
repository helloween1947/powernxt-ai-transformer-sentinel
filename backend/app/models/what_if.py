"""Server-owned immutable captures, never a mutable worker cache reference."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class WhatIfSnapshot(Base):
    __tablename__ = "what_if_snapshots"
    __table_args__ = (
        UniqueConstraint("result_id", name="uq_what_if_snapshot_result"),
        ForeignKeyConstraint(
            ["asset_id", "configuration_version"],
            ["asset_configurations.asset_id", "asset_configurations.version"],
            ondelete="RESTRICT",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    result_id: Mapped[int] = mapped_column(
        ForeignKey("analytics_results.id", ondelete="RESTRICT")
    )
    asset_id: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(20))
    run_key: Mapped[str] = mapped_column(String(100))
    configuration_version: Mapped[int]
    model_id: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(100))
    parameter_version: Mapped[str] = mapped_column(String(100))
    measurement_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[dict] = mapped_column(JSON)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
