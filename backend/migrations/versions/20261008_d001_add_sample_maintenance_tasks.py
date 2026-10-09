"""Add Person D's sample maintenance task milestone."""

from alembic import op
import sqlalchemy as sa

revision = "d001_maintenance"
down_revision = "84b8976a7d0d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "maintenance_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("asset_id", sa.String(100), sa.ForeignKey("assets.asset_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("alert_source", sa.String(20), nullable=False),
        sa.Column("alert_id", sa.String(100), nullable=False),
        sa.Column("alert_summary", sa.String(500), nullable=False),
        sa.Column("action", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("asset_id", "alert_source", "alert_id", name="uq_task_sample_alert"),
        sa.CheckConstraint("status = 'open'", name="ck_task_open"),
        sa.CheckConstraint("alert_source = 'sample'", name="ck_task_sample_source"),
    )
    op.create_index("ix_maintenance_tasks_asset_id", "maintenance_tasks", ["asset_id"])


def downgrade():
    op.drop_index("ix_maintenance_tasks_asset_id", table_name="maintenance_tasks")
    op.drop_table("maintenance_tasks")
