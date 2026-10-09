"""Extend D001 tasks without replacing existing task identities or alert snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "d002_task_workflow"
down_revision = "d001_maintenance"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("maintenance_tasks", sa.Column("owner", sa.String(100), nullable=True))
    op.add_column("maintenance_tasks", sa.Column("notes", sa.String(2000), nullable=False, server_default=""))
    op.add_column("maintenance_tasks", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("maintenance_tasks", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.execute("UPDATE maintenance_tasks SET updated_at = created_at")
    op.drop_constraint("ck_task_open", "maintenance_tasks", type_="check")
    op.create_check_constraint("ck_task_status", "maintenance_tasks", "status IN ('open', 'in_progress', 'completed', 'cancelled')")
    op.create_check_constraint("ck_task_version", "maintenance_tasks", "version > 0")
    op.create_check_constraint("ck_task_owner_required", "maintenance_tasks", "status NOT IN ('in_progress', 'completed') OR (owner IS NOT NULL AND length(trim(owner)) > 0)")
    op.create_check_constraint("ck_task_terminal_notes", "maintenance_tasks", "status NOT IN ('completed', 'cancelled') OR length(trim(notes)) > 0")
    op.create_table(
        "maintenance_task_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("maintenance_tasks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("previous_status", sa.String(20)),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("previous_owner", sa.String(100)),
        sa.Column("new_owner", sa.String(100)),
        sa.Column("previous_notes", sa.String(2000)),
        sa.Column("notes", sa.String(2000), nullable=False),
        sa.Column("actor", sa.String(100)),
        sa.Column("identity_source", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("task_id", "version", name="uq_task_history_version"),
        sa.CheckConstraint("version > 0", name="ck_task_history_version"),
    )
    # Existing tasks have no recorded creator. Record a truthful migration
    # snapshot with migration time, rather than inventing an operator/event.
    op.execute("""
        INSERT INTO maintenance_task_history
        (task_id, version, event_type, new_status, new_owner, notes, identity_source)
        SELECT id, version, 'legacy_import', status, owner, notes, 'legacy_import'
        FROM maintenance_tasks
    """)


def downgrade():
    # Refuse to erase workflow/history data or manufacture an open state.
    connection = op.get_bind()
    used = connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM maintenance_tasks WHERE version > 1 OR status <> 'open' OR owner IS NOT NULL OR notes <> '')"))
    if used:
        raise RuntimeError("Workflow data exists; preserve/export it before planning a downgrade")
    op.drop_table("maintenance_task_history")
    for name in ("ck_task_terminal_notes", "ck_task_owner_required", "ck_task_version", "ck_task_status"):
        op.drop_constraint(name, "maintenance_tasks", type_="check")
    op.create_check_constraint("ck_task_open", "maintenance_tasks", "status = 'open'")
    for name in ("updated_at", "version", "notes", "owner"):
        op.drop_column("maintenance_tasks", name)
