"""Join the now-merged analytics worker with D's audit/maintenance join.

No DDL: maintenance tables and worker job/state/result tables are disjoint.
Retain all applied revisions, including D003; do not rewrite its parents.
"""

revision = "d004_worker_maintenance"
down_revision = ("d730a91b4c22", "d003_audit_maintenance")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
