"""Transformer identities and append-only, versioned nameplate configurations."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Asset(Base):
    __tablename__ = "assets"

    asset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(500))
    timezone: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AssetConfiguration(Base):
    __tablename__ = "asset_configurations"
    __table_args__ = (
        UniqueConstraint("asset_id", "version", name="uq_asset_configuration_version"),
        CheckConstraint("version > 0", name="ck_configuration_version_positive"),
        *[
            CheckConstraint(
                f"{field} > 0 AND {field} < 'Infinity'::float8",
                name=f"ck_{field}_positive_finite",
            )
            for field in ("rated_kva", "rated_voltage_v", "rated_current_a")
        ],
        CheckConstraint(
            "voltage_convention IN ('phase_to_neutral', 'line_to_line')",
            name="ck_voltage_convention",
        ),
        CheckConstraint(
            "measurement_side IN ('primary', 'secondary')", name="ck_measurement_side"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    rated_kva: Mapped[float] = mapped_column(Float)
    rated_voltage_v: Mapped[float] = mapped_column(Float)
    rated_current_a: Mapped[float] = mapped_column(Float)
    voltage_convention: Mapped[str] = mapped_column(String(30))
    measurement_side: Mapped[str] = mapped_column(String(20))
    cooling_type: Mapped[str] = mapped_column(String(50))
    operational_limits: Mapped[dict] = mapped_column(JSON)
    thermal_parameters: Mapped[dict] = mapped_column(JSON)
    parameter_provenance: Mapped[dict] = mapped_column(JSON)
