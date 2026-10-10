"""Link genuine tasks without rewriting sample records or registry history."""
from alembic import op
import sqlalchemy as sa

revision = "d005_incident_tasks"
down_revision = "a001_incident_registry"
branch_labels = None
depends_on = None

REFERENCE = "(alert_source = 'sample' AND incident_id IS NULL AND incident_evidence_id IS NULL AND creation_request IS NULL AND created_by_id IS NULL) OR (alert_source = 'analytics' AND incident_id IS NOT NULL AND incident_evidence_id IS NOT NULL AND creation_request IS NOT NULL AND created_by_id IS NOT NULL)"
ATTRIBUTION = "(identity_source = 'authenticated_operator' AND actor_id IS NOT NULL AND actor IS NOT NULL AND actor = actor_id::text) OR (identity_source IN ('demo_header','unattributed_creation','legacy_import') AND actor_id IS NULL)"


def upgrade():
    op.add_column("maintenance_tasks", sa.Column("incident_id", sa.Uuid(), nullable=True))
    op.add_column("maintenance_tasks", sa.Column("incident_evidence_id", sa.BigInteger(), nullable=True))
    op.add_column("maintenance_tasks", sa.Column("created_by_id", sa.Uuid(), nullable=True))
    op.add_column("maintenance_tasks", sa.Column("creation_request", sa.JSON(), nullable=True))
    op.create_foreign_key("fk_task_incident_asset", "maintenance_tasks", "incidents", ["incident_id", "asset_id"], ["id", "asset_id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_task_incident_evidence", "maintenance_tasks", "incident_evidence", ["incident_evidence_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_task_created_by", "maintenance_tasks", "incident_operators", ["created_by_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_task_incident", "maintenance_tasks", ["incident_id"])
    op.drop_constraint("ck_task_sample_source", "maintenance_tasks", type_="check")
    op.create_check_constraint("ck_task_reference", "maintenance_tasks", REFERENCE)
    op.add_column("maintenance_task_history", sa.Column("actor_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_task_history_actor", "maintenance_task_history", "incident_operators", ["actor_id"], ["id"], ondelete="RESTRICT")
    op.create_check_constraint("ck_task_history_attribution", "maintenance_task_history", ATTRIBUTION)


def downgrade():
    op.execute("DO $$ BEGIN IF EXISTS(SELECT 1 FROM maintenance_tasks WHERE incident_id IS NOT NULL) OR EXISTS(SELECT 1 FROM maintenance_task_history WHERE actor_id IS NOT NULL) THEN RAISE EXCEPTION 'D005 downgrade refused: preserve genuine tasks and trusted audit'; END IF; END $$")
    op.drop_constraint("ck_task_history_attribution", "maintenance_task_history", type_="check")
    op.drop_constraint("fk_task_history_actor", "maintenance_task_history", type_="foreignkey")
    op.drop_column("maintenance_task_history", "actor_id")
    op.drop_constraint("ck_task_reference", "maintenance_tasks", type_="check")
    op.create_check_constraint("ck_task_sample_source", "maintenance_tasks", "alert_source = 'sample'")
    for name in ("fk_task_incident_asset", "fk_task_incident_evidence", "fk_task_created_by"):
        op.drop_constraint(name, "maintenance_tasks", type_="foreignkey")
    op.drop_constraint("uq_task_incident", "maintenance_tasks", type_="unique")
    for name in ("creation_request", "created_by_id", "incident_evidence_id", "incident_id"):
        op.drop_column("maintenance_tasks", name)
