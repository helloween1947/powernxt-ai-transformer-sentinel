"""Add transactional telemetry ingestion

Revision ID: 84b8976a7d0d
Revises: f272b723f71b
Create Date: 2026-10-08 07:17:08.052545+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "84b8976a7d0d"
down_revision: str | None = "f272b723f71b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telemetry_readings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("asset_id", sa.String(length=100), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("run_key", sa.String(length=100), nullable=False),
        sa.Column("measurement_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "arrival_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("original_payload", sa.JSON(), nullable=False),
        sa.Column("payload_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("normalized_telemetry", sa.JSON(), nullable=False),
        sa.Column("quality_flags", sa.JSON(), nullable=False),
        sa.Column("out_of_order", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "(source = 'device' AND run_key = '') OR (source IN ('simulator', 'file_replay') AND run_key <> '')",
            name="ck_telemetry_stream",
        ),
        sa.CheckConstraint("schema_version = '1.0.0'", name="ck_telemetry_schema"),
        sa.ForeignKeyConstraint(
            ["asset_id", "configuration_version"],
            ["asset_configurations.asset_id", "asset_configurations.version"],
            name="fk_telemetry_configuration",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id", "source", "run_key", "message_id", name="uq_telemetry_delivery"
        ),
    )
    op.create_index(
        "ix_telemetry_stream_time",
        "telemetry_readings",
        ["asset_id", "source", "run_key", "measurement_time", "id"],
        unique=False,
    )
    op.create_table(
        "telemetry_processing_jobs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("reading_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("state_policy", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "state_policy IN ('forward_only', 'historical_only')",
            name="ck_telemetry_job_policy",
        ),
        sa.CheckConstraint("status = 'pending'", name="ck_telemetry_job_pending"),
        sa.ForeignKeyConstraint(
            ["reading_id"], ["telemetry_readings.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reading_id"),
    )


def downgrade() -> None:
    op.drop_table("telemetry_processing_jobs")
    op.drop_index("ix_telemetry_stream_time", table_name="telemetry_readings")
    op.drop_table("telemetry_readings")
