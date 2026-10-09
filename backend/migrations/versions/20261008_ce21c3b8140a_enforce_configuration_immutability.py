"""Enforce the existing append-only configuration contract in PostgreSQL.

Revision ID: ce21c3b8140a
Revises: 84b8976a7d0d

Online operations use the connection's current schema, including isolated test
schemas. Offline SQL targets version_table_schema when configured, else public.
Downgrade removes only the row guard; it does not delete configurations/readings.
"""

import sqlalchemy as sa
from alembic import context, op

revision = "ce21c3b8140a"
down_revision = "84b8976a7d0d"
branch_labels = None
depends_on = None


def targets():
    if context.is_offline_mode():
        schema = context.get_context().opts.get("version_table_schema") or "public"
    else:
        schema = op.get_bind().scalar(sa.text("SELECT current_schema()"))
    if schema is None:
        raise RuntimeError("A current schema is required for configuration guards")
    quote = op.get_context().dialect.identifier_preparer.quote
    prefix = quote(schema)
    return (
        f"{prefix}.asset_configurations",
        f"{prefix}.reject_asset_configuration_mutation",
    )


def upgrade():
    table, function = targets()
    op.execute(f"""
        CREATE FUNCTION {function}() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Asset configurations are immutable; append a new version'
                USING ERRCODE = '23514';
        END;
        $$
    """)
    op.execute(f"""
        CREATE TRIGGER asset_configuration_immutable
        BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION {function}()
    """)


def downgrade():
    table, function = targets()
    op.execute(f"DROP TRIGGER asset_configuration_immutable ON {table}")
    op.execute(f"DROP FUNCTION {function}()")
