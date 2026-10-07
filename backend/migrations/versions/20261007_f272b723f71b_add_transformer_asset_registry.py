"""Add transformer asset registry

Revision ID: f272b723f71b
Revises:
Create Date: 2026-10-07 17:22:53.382244+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f272b723f71b"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("asset_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("asset_id"),
    )
    op.create_table(
        "asset_configurations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("rated_kva", sa.Float(), nullable=False),
        sa.Column("rated_voltage_v", sa.Float(), nullable=False),
        sa.Column("rated_current_a", sa.Float(), nullable=False),
        sa.Column("voltage_convention", sa.String(length=30), nullable=False),
        sa.Column("measurement_side", sa.String(length=20), nullable=False),
        sa.Column("cooling_type", sa.String(length=50), nullable=False),
        sa.Column("operational_limits", sa.JSON(), nullable=False),
        sa.Column("thermal_parameters", sa.JSON(), nullable=False),
        sa.Column("parameter_provenance", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "measurement_side IN ('primary', 'secondary')", name="ck_measurement_side"
        ),
        sa.CheckConstraint(
            "rated_current_a > 0 AND rated_current_a < 'Infinity'::float8",
            name="ck_rated_current_a_positive_finite",
        ),
        sa.CheckConstraint(
            "rated_kva > 0 AND rated_kva < 'Infinity'::float8",
            name="ck_rated_kva_positive_finite",
        ),
        sa.CheckConstraint(
            "rated_voltage_v > 0 AND rated_voltage_v < 'Infinity'::float8",
            name="ck_rated_voltage_v_positive_finite",
        ),
        sa.CheckConstraint(
            "voltage_convention IN ('phase_to_neutral', 'line_to_line')",
            name="ck_voltage_convention",
        ),
        sa.CheckConstraint("version > 0", name="ck_configuration_version_positive"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.asset_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id", "version", name="uq_asset_configuration_version"
        ),
    )


def downgrade() -> None:
    op.drop_table("asset_configurations")
    op.drop_table("assets")
