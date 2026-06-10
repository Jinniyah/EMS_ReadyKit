"""
Add item check types, measurement/functional/date fields on check_line_items,
compartment location descriptor and parent, and JUMP_BAG/EQUIPMENT location types.

Revision ID: 0003_item_check_types_and_equipment
Revises: 0003a_widen_alembic_version
Create Date: 2026-05-15

SQLite note:
  All ALTER TABLE operations on existing tables use Alembic batch mode
  (copy-and-move strategy) because SQLite does not support ALTER TABLE
  ADD COLUMN with constraints, ADD CONSTRAINT, or DROP COLUMN natively.

PostgreSQL note:
  PostgreSQL supports these operations natively and must NOT use batch mode
  because it enforces FK constraints during table drop/recreate.
  All PostgreSQL DDL uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS guards so
  the migration is fully idempotent. A previous failed deploy may have
  partially applied some statements; the guards prevent "already exists"
  errors on retry.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003_item_check_types_and_equipment"
down_revision: Union[str, None] = "0003a_widen_alembic_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # ── items: add check_type and measurement/recurrence metadata ─────────────
    if dialect == "sqlite":
        with op.batch_alter_table("items", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "check_type",
                    sa.String(20),
                    nullable=False,
                    server_default="SUPPLY",
                )
            )
            batch_op.add_column(
                sa.Column("measurement_minimum", sa.Float, nullable=True)
            )
            batch_op.add_column(
                sa.Column("measurement_maximum", sa.Float, nullable=True)
            )
            batch_op.add_column(sa.Column("recurrence_days", sa.Integer, nullable=True))
            batch_op.create_index("ix_items_check_type", ["check_type"])
    else:
        bind.execute(sa.text("""
            ALTER TABLE items
            ADD COLUMN IF NOT EXISTS check_type VARCHAR(20) NOT NULL DEFAULT 'SUPPLY'
        """))
        bind.execute(sa.text("""
            ALTER TABLE items
            ADD COLUMN IF NOT EXISTS measurement_minimum FLOAT
        """))
        bind.execute(sa.text("""
            ALTER TABLE items
            ADD COLUMN IF NOT EXISTS measurement_maximum FLOAT
        """))
        bind.execute(sa.text("""
            ALTER TABLE items
            ADD COLUMN IF NOT EXISTS recurrence_days INTEGER
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_items_check_type
            ON items (check_type)
        """))

    # ── check_line_items: add measurement, functional, and date fields ────────
    if dialect == "sqlite":
        with op.batch_alter_table("check_line_items", schema=None) as batch_op:
            batch_op.add_column(sa.Column("measurement_value", sa.Float, nullable=True))
            batch_op.add_column(sa.Column("functional_pass", sa.Boolean, nullable=True))
            batch_op.add_column(sa.Column("date_value", sa.Date, nullable=True))
    else:
        bind.execute(sa.text("""
            ALTER TABLE check_line_items
            ADD COLUMN IF NOT EXISTS measurement_value FLOAT
        """))
        bind.execute(sa.text("""
            ALTER TABLE check_line_items
            ADD COLUMN IF NOT EXISTS functional_pass BOOLEAN
        """))
        bind.execute(sa.text("""
            ALTER TABLE check_line_items
            ADD COLUMN IF NOT EXISTS date_value DATE
        """))

    # ── compartments: add location descriptor, parent, restriction note ───────
    if dialect == "sqlite":
        with op.batch_alter_table("compartments", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("location_descriptor", sa.String(150), nullable=True)
            )
            batch_op.add_column(
                sa.Column("parent_compartment_id", sa.Integer, nullable=True)
            )
            batch_op.add_column(
                sa.Column("restriction_note", sa.String(100), nullable=True)
            )
            batch_op.create_index(
                "ix_compartments_parent_compartment_id",
                ["parent_compartment_id"],
            )
    else:
        bind.execute(sa.text("""
            ALTER TABLE compartments
            ADD COLUMN IF NOT EXISTS location_descriptor VARCHAR(150)
        """))
        bind.execute(sa.text("""
            ALTER TABLE compartments
            ADD COLUMN IF NOT EXISTS parent_compartment_id INTEGER
        """))
        bind.execute(sa.text("""
            ALTER TABLE compartments
            ADD COLUMN IF NOT EXISTS restriction_note VARCHAR(100)
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_compartments_parent_compartment_id
            ON compartments (parent_compartment_id)
        """))

    # ── inventory_locations: JUMP_BAG and EQUIPMENT are VARCHAR values ────────
    # location_type is stored as VARCHAR (native_enum=False).
    # New enum values require no DDL change — accepted automatically.


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("compartments", schema=None) as batch_op:
            batch_op.drop_index("ix_compartments_parent_compartment_id")
            batch_op.drop_column("restriction_note")
            batch_op.drop_column("parent_compartment_id")
            batch_op.drop_column("location_descriptor")

        with op.batch_alter_table("check_line_items", schema=None) as batch_op:
            batch_op.drop_column("date_value")
            batch_op.drop_column("functional_pass")
            batch_op.drop_column("measurement_value")

        with op.batch_alter_table("items", schema=None) as batch_op:
            batch_op.drop_index("ix_items_check_type")
            batch_op.drop_column("recurrence_days")
            batch_op.drop_column("measurement_maximum")
            batch_op.drop_column("measurement_minimum")
            batch_op.drop_column("check_type")
    else:
        bind.execute(sa.text("""
            DROP INDEX IF EXISTS ix_compartments_parent_compartment_id
        """))
        bind.execute(sa.text("""
            ALTER TABLE compartments
            DROP COLUMN IF EXISTS restriction_note
        """))
        bind.execute(sa.text("""
            ALTER TABLE compartments
            DROP COLUMN IF EXISTS parent_compartment_id
        """))
        bind.execute(sa.text("""
            ALTER TABLE compartments
            DROP COLUMN IF EXISTS location_descriptor
        """))

        bind.execute(sa.text("""
            ALTER TABLE check_line_items
            DROP COLUMN IF EXISTS date_value
        """))
        bind.execute(sa.text("""
            ALTER TABLE check_line_items
            DROP COLUMN IF EXISTS functional_pass
        """))
        bind.execute(sa.text("""
            ALTER TABLE check_line_items
            DROP COLUMN IF EXISTS measurement_value
        """))

        bind.execute(sa.text("""
            DROP INDEX IF EXISTS ix_items_check_type
        """))
        bind.execute(sa.text("""
            ALTER TABLE items
            DROP COLUMN IF EXISTS recurrence_days
        """))
        bind.execute(sa.text("""
            ALTER TABLE items
            DROP COLUMN IF EXISTS measurement_maximum
        """))
        bind.execute(sa.text("""
            ALTER TABLE items
            DROP COLUMN IF EXISTS measurement_minimum
        """))
        bind.execute(sa.text("""
            ALTER TABLE items
            DROP COLUMN IF EXISTS check_type
        """))
