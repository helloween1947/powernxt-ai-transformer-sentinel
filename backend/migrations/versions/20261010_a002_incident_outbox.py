"""Add incident delivery checkpoints without rewriting existing event history."""

import sqlalchemy as sa
from alembic import op

revision = "a002_incident_outbox"
down_revision = "a001_incident_registry"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "incident_deliveries",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("claim_token", sa.Uuid(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("event_id"),
        sa.ForeignKeyConstraint(
            ["event_id"], ["incident_events.event_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_incident_delivery_attempts"),
        sa.CheckConstraint(
            "(claim_token IS NULL) = (lease_until IS NULL)",
            name="ck_incident_delivery_lease",
        ),
    )
    # Existing immutable journal entries remain intact and become pending deliveries.
    op.execute(
        "INSERT INTO incident_deliveries(event_id) SELECT event_id FROM incident_events"
    )


def downgrade():
    # Delivery receipts are evidence too. Refuse to destroy a populated checkpoint.
    if op.get_context().as_sql:
        op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM incident_deliveries) THEN
            RAISE EXCEPTION 'incident outbox downgrade requires empty table'; END IF; END $$""")
    elif op.get_bind().scalar(
        sa.text("SELECT EXISTS(SELECT 1 FROM incident_deliveries)")
    ):
        raise RuntimeError(
            "Incident outbox downgrade refused: preserve delivery records"
        )
    op.drop_table("incident_deliveries")
