"""Join immutable configurations and maintenance without rewriting either branch.

The audit parent is already on main. Apply this revision with both parent
migration files present; it deliberately performs no schema/data operations.
"""

revision = "d003_audit_maintenance"
down_revision = ("ce21c3b8140a", "d002_task_workflow")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
