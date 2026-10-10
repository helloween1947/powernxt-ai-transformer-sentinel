"""Join reviewed branch migrations; preserve all applied revisions and records.

A002 creates delivery checkpoints, D005 links maintenance tasks, and W001 creates
immutable scenario snapshots. No overlapping DDL or data backfill in this join.
"""
revision = "d006_combined_integration"
down_revision = ("a002_incident_outbox", "d005_incident_tasks", "w001_what_if_snapshots")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
