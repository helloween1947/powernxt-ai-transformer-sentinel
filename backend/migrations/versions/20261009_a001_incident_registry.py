"""Add canonical incident registry and trusted identity; preserve sample tasks.

Additive revision after D004, no edits to previous revisions or legacy rows.
"""

import sqlalchemy as sa
from alembic import op

revision = "a001_incident_registry"
down_revision = "d004_worker_maintenance"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "incident_operators",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('reader','operator','admin')", name="ck_operator_role"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_table(
        "incident_operations",
        sa.Column("scope", sa.String(length=250), nullable=False),
        sa.Column("key", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["incident_operators.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("scope", "key"),
    )
    op.create_table(
        "incident_detector_epochs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("run_key", sa.String(length=100), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("parameter_version", sa.String(length=100), nullable=False),
        sa.Column("detector_version", sa.String(length=100), nullable=False),
        sa.Column("policy", sa.JSON(), nullable=False),
        sa.Column("policy_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("previous_twin_state", sa.JSON(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("boundary_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(source='device' AND run_key='') OR (source IN ('simulator','file_replay') AND run_key<>'')",
            name="ck_epoch_stream",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["incident_operators.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["asset_id", "configuration_version"],
            ["asset_configurations.asset_id", "asset_configurations.version"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id", "asset_id", "source", "run_key", name="uq_epoch_stream"
        ),
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.String(length=100), nullable=False),
        sa.Column("measurement_source", sa.String(length=20), nullable=False),
        sa.Column("run_key", sa.String(length=100), nullable=False),
        sa.Column("detector_epoch", sa.Uuid(), nullable=False),
        sa.Column("detector_episode_key", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("condition_status", sa.String(length=20), nullable=False),
        sa.Column("monitoring_status", sa.String(length=20), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_evaluated_measurement_time",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("last_evidence_status", sa.String(length=20), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "(condition_status='active' AND recovered_at IS NULL) OR (condition_status='recovered' AND recovered_at IS NOT NULL)",
            name="ck_incident_condition",
        ),
        sa.CheckConstraint(
            "last_evidence_status IN ('available','unavailable')",
            name="ck_incident_evidence_status",
        ),
        sa.CheckConstraint(
            "monitoring_status IN ('monitoring','interrupted')",
            name="ck_incident_monitoring",
        ),
        sa.CheckConstraint(
            "severity IN ('info','warning','critical')", name="ck_incident_severity"
        ),
        sa.CheckConstraint(
            "(acknowledged_at IS NULL AND actor_id IS NULL) OR (acknowledged_at IS NOT NULL AND actor_id IS NOT NULL)",
            name="ck_incident_ack",
        ),
        sa.CheckConstraint("version>0", name="ck_incident_version"),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["incident_operators.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.asset_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["detector_epoch", "asset_id", "measurement_source", "run_key"],
            [
                "incident_detector_epochs.id",
                "incident_detector_epochs.asset_id",
                "incident_detector_epochs.source",
                "incident_detector_epochs.run_key",
            ],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id",
            "detector_epoch",
            "detector_episode_key",
            name="uq_incident_mapping",
        ),
        sa.UniqueConstraint("id", "asset_id", name="uq_incident_asset"),
    )
    op.create_table(
        "incident_evidence",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("incident_version", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.BigInteger(), nullable=False),
        sa.Column("reading_id", sa.BigInteger(), nullable=False),
        sa.Column("detector_version", sa.String(length=100), nullable=False),
        sa.Column("policy_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["reading_id"], ["telemetry_readings.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["result_id"], ["analytics_results.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "incident_id", "incident_version", name="uq_incident_evidence_version"
        ),
        sa.UniqueConstraint(
            "incident_id",
            "result_id",
            "detector_version",
            "policy_fingerprint",
            name="uq_incident_evidence",
        ),
    )
    op.create_table(
        "incident_detector_controls",
        sa.Column("asset_id", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("run_key", sa.String(length=100), nullable=False),
        sa.Column("epoch_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("continuity_break", sa.Boolean(), nullable=False),
        sa.CheckConstraint("version>0", name="ck_detector_control_version"),
        sa.ForeignKeyConstraint(
            ["asset_id", "source", "run_key"],
            [
                "analytics_streams.asset_id",
                "analytics_streams.source",
                "analytics_streams.run_key",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["epoch_id", "asset_id", "source", "run_key"],
            [
                "incident_detector_epochs.id",
                "incident_detector_epochs.asset_id",
                "incident_detector_epochs.source",
                "incident_detector_epochs.run_key",
            ],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("asset_id", "source", "run_key"),
    )
    op.create_table(
        "incident_events",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("incident_version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("evidence_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["incident_operators.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["incident_evidence.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint(
            "incident_id", "incident_version", name="uq_incident_event_version"
        ),
    )
    # Schema-qualified triggers protect snapshots even outside ORM writes.
    schema = (
        "public"
        if op.get_context().as_sql
        else op.get_bind().scalar(sa.text("SELECT current_schema()"))
    )
    quoted = '"' + schema.replace('"', '""') + '"'
    op.execute(f"""CREATE FUNCTION {quoted}.incident_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        RAISE EXCEPTION 'incident audit records are append only' USING ERRCODE='23514';
        END $$""")
    for table in ("incident_evidence", "incident_events", "incident_operations"):
        op.execute(
            f"CREATE TRIGGER incident_append_only BEFORE UPDATE OR DELETE ON {quoted}.{table} "
            f"FOR EACH ROW EXECUTE FUNCTION {quoted}.incident_append_only()"
        )
    op.execute(f"""CREATE FUNCTION {quoted}.incident_epoch_binding() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'detector epoch is immutable' USING ERRCODE='23514';
        END IF;
        IF (to_jsonb(NEW) - 'context') IS DISTINCT FROM (to_jsonb(OLD) - 'context') THEN
            RAISE EXCEPTION 'detector epoch binding is immutable' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
        END $$""")
    op.execute(
        f"CREATE TRIGGER incident_epoch_binding BEFORE UPDATE OR DELETE ON {quoted}.incident_detector_epochs "
        f"FOR EACH ROW EXECUTE FUNCTION {quoted}.incident_epoch_binding()"
    )
    op.execute(f"""CREATE FUNCTION {quoted}.incident_evidence_binding() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM {quoted}.incidents i
            JOIN {quoted}.incident_detector_epochs e ON e.id=i.detector_epoch
            JOIN {quoted}.telemetry_readings t ON t.id=NEW.reading_id
            JOIN {quoted}.analytics_results r ON r.id=NEW.result_id AND r.reading_id=t.id
            WHERE i.id=NEW.incident_id AND i.asset_id=t.asset_id
                AND i.measurement_source=t.source AND i.run_key=t.run_key
                AND e.configuration_version=t.configuration_version
                AND e.model_version=r.model_version AND e.parameter_version=r.parameter_version
                AND e.detector_version=NEW.detector_version
                AND e.policy_fingerprint=NEW.policy_fingerprint
        ) THEN
            RAISE EXCEPTION 'incident evidence binding mismatch' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
        END $$""")
    op.execute(
        f"CREATE TRIGGER incident_evidence_binding BEFORE INSERT ON {quoted}.incident_evidence "
        f"FOR EACH ROW EXECUTE FUNCTION {quoted}.incident_evidence_binding()"
    )


def downgrade():
    # Empty-only rollback. Never delete/relabel incident audit or trusted identity.
    for table in (
        "incident_operators",
        "incident_detector_epochs",
        "incidents",
        "incident_evidence",
        "incident_events",
        "incident_operations",
        "incident_detector_controls",
    ):
        if op.get_context().as_sql:
            op.execute(f"""DO $$ BEGIN IF EXISTS(SELECT 1 FROM {table}) THEN
                RAISE EXCEPTION 'incident registry downgrade requires empty tables'; END IF; END $$""")
        elif op.get_bind().scalar(sa.text(f"SELECT EXISTS(SELECT 1 FROM {table})")):
            raise RuntimeError(
                "Incident registry downgrade refused: preserve populated incident/identity tables"
            )
    schema = (
        "public"
        if op.get_context().as_sql
        else op.get_bind().scalar(sa.text("SELECT current_schema()"))
    )
    quoted = '"' + schema.replace('"', '""') + '"'
    op.drop_table("incident_events")
    op.drop_table("incident_detector_controls")
    op.drop_table("incident_evidence")
    op.drop_table("incidents")
    op.drop_table("incident_detector_epochs")
    op.drop_table("incident_operations")
    op.drop_table("incident_operators")
    for name in (
        "incident_append_only",
        "incident_epoch_binding",
        "incident_evidence_binding",
    ):
        op.execute(f"DROP FUNCTION {quoted}.{name}()")
