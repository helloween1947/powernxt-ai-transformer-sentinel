"""Add immutable what-if snapshots; leave worker/results/configuration data intact."""

import sqlalchemy as sa
from alembic import op

revision = "w001_what_if_snapshots"
down_revision = "d004_worker_maintenance"
branch_labels = None
depends_on = None


def schema():
    name = (
        "public"
        if op.get_context().as_sql
        else op.get_bind().scalar(sa.text("SELECT current_schema()"))
    )
    return '"' + name.replace('"', '""') + '"'


def upgrade():
    op.create_table(
        "what_if_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "result_id",
            sa.BigInteger(),
            sa.ForeignKey("analytics_results.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("asset_id", sa.String(100), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("run_key", sa.String(100), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("parameter_version", sa.String(100), nullable=False),
        sa.Column("measurement_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("result_id", name="uq_what_if_snapshot_result"),
        sa.ForeignKeyConstraint(
            ["asset_id", "configuration_version"],
            ["asset_configurations.asset_id", "asset_configurations.version"],
            ondelete="RESTRICT",
        ),
    )
    qualified = schema()
    op.execute(f"""CREATE FUNCTION {qualified}.what_if_snapshot_guard() RETURNS trigger AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'what-if snapshots are immutable' USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM {qualified}.analytics_results a
        JOIN {qualified}.telemetry_readings r ON r.id=a.reading_id
        WHERE a.id=NEW.result_id AND a.status='completed'
        AND r.asset_id=NEW.asset_id AND r.source=NEW.source AND r.run_key=NEW.run_key
        AND r.configuration_version=NEW.configuration_version
        AND r.measurement_time=NEW.measurement_time
        AND a.model_id=NEW.model_id AND a.model_version=NEW.model_version
        AND a.parameter_version=NEW.parameter_version
        AND a.payload::jsonb->'execution_status'->>'state_advanced'='true'
        AND a.payload::jsonb->'updated_state'=NEW.state::jsonb
      ) THEN
        RAISE EXCEPTION 'what-if snapshot binding mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql""")
    op.execute(f"""CREATE TRIGGER what_if_snapshot_guard BEFORE INSERT OR UPDATE OR DELETE
        ON {qualified}.what_if_snapshots FOR EACH ROW EXECUTE FUNCTION {qualified}.what_if_snapshot_guard()""")


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM what_if_snapshots) THEN
        RAISE EXCEPTION 'what-if downgrade requires empty snapshot table'; END IF; END $$""")
    op.drop_table("what_if_snapshots")
    op.execute(f"DROP FUNCTION {schema()}.what_if_snapshot_guard()")
