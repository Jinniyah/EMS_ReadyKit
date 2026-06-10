"""Add compartments, check_line_items, lot tracking; add compartment_id to par_levels

Revision ID: 0002_compartments_and_line_items
Revises: 0001_initial_schema
Create Date: 2026-05-13

Changes:
  - New table: compartments (physical storage areas within a vehicle/location)
  - New table: check_line_items (per-item Need/Have counts per compartment per check)
      includes lot_id FK for expiration tracking during daily checks
  - Modified: par_levels — adds nullable compartment_id FK
  - New unique constraint on par_levels: (item_id, compartment_id)
  - New indexes for common query patterns

SQLite note:
  SQLite does not support ALTER TABLE ADD CONSTRAINT or inline FK on ADD COLUMN.
  The par_levels modification uses Alembic batch mode (copy-and-move strategy)
  to add compartment_id and the unique constraint in a single table rebuild.

PostgreSQL note:
  PostgreSQL supports ALTER TABLE natively and must NOT use batch mode because
  it enforces FK constraints when dropping and recreating tables — the batch
  rebuild would fail if any rows in par_levels are referenced by other tables.
  Dialect is checked at runtime so the same migration file works for both.

  All PostgreSQL DDL uses IF NOT EXISTS / IF EXISTS guards so the migration
  is fully idempotent. A previous failed deploy may have partially applied
  some statements; the guards prevent "already exists" errors on retry.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002_compartments_and_line_items"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # ── compartments ──────────────────────────────────────────────────────────
    if dialect == "sqlite":
        op.create_table(
            "compartments",
            sa.Column("compartment_id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "location_id",
                sa.Integer,
                sa.ForeignKey("inventory_locations.location_id"),
                nullable=False,
            ),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
            sa.Column("als_only", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("location_id", "name", name="uq_compartment_location_name"),
        )
        op.create_index("ix_compartments_location_id", "compartments", ["location_id"])
    else:
        bind.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS compartments (
                compartment_id  SERIAL PRIMARY KEY,
                location_id     INTEGER NOT NULL
                                REFERENCES inventory_locations(location_id),
                name            VARCHAR(100) NOT NULL,
                sort_order      INTEGER NOT NULL DEFAULT 0,
                als_only        BOOLEAN NOT NULL DEFAULT FALSE,
                active          BOOLEAN NOT NULL DEFAULT TRUE,
                created_at      TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at      TIMESTAMP WITH TIME ZONE NOT NULL,
                CONSTRAINT uq_compartment_location_name UNIQUE (location_id, name)
            )
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_compartments_location_id
            ON compartments (location_id)
        """))

    # ── check_line_items ──────────────────────────────────────────────────────
    if dialect == "sqlite":
        op.create_table(
            "check_line_items",
            sa.Column("line_item_id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "check_id",
                sa.Integer,
                sa.ForeignKey("daily_inventory_checks.check_id"),
                nullable=False,
            ),
            sa.Column(
                "compartment_id",
                sa.Integer,
                sa.ForeignKey("compartments.compartment_id"),
                nullable=False,
            ),
            sa.Column(
                "item_id",
                sa.Integer,
                sa.ForeignKey("items.item_id"),
                nullable=False,
            ),
            sa.Column(
                "lot_id",
                sa.Integer,
                sa.ForeignKey("stock_lots.lot_id"),
                nullable=True,
            ),
            sa.Column("quantity_needed", sa.Integer, nullable=False, server_default="0"),
            sa.Column("quantity_found", sa.Integer, nullable=False, server_default="0"),
            sa.Column("status", sa.String(10), nullable=False),
            sa.Column("notes", sa.String(300), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_check_line_items_check_id", "check_line_items", ["check_id"])
        op.create_index("ix_check_line_items_compartment_id", "check_line_items", ["compartment_id"])
        op.create_index("ix_check_line_items_status", "check_line_items", ["status"])
        op.create_index("ix_check_line_items_lot_id", "check_line_items", ["lot_id"])
    else:
        bind.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS check_line_items (
                line_item_id    SERIAL PRIMARY KEY,
                check_id        INTEGER NOT NULL
                                REFERENCES daily_inventory_checks(check_id),
                compartment_id  INTEGER NOT NULL
                                REFERENCES compartments(compartment_id),
                item_id         INTEGER NOT NULL
                                REFERENCES items(item_id),
                lot_id          INTEGER
                                REFERENCES stock_lots(lot_id),
                quantity_needed INTEGER NOT NULL DEFAULT 0,
                quantity_found  INTEGER NOT NULL DEFAULT 0,
                status          VARCHAR(10) NOT NULL,
                notes           VARCHAR(300),
                created_at      TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at      TIMESTAMP WITH TIME ZONE NOT NULL
            )
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_check_line_items_check_id
            ON check_line_items (check_id)
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_check_line_items_compartment_id
            ON check_line_items (compartment_id)
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_check_line_items_status
            ON check_line_items (status)
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_check_line_items_lot_id
            ON check_line_items (lot_id)
        """))

    # ── par_levels: add compartment_id + unique constraint ────────────────────
    # SQLite requires batch mode.
    # PostgreSQL uses raw DDL with IF NOT EXISTS guards so a partial previous
    # run (failed deploy) doesn't cause "column already exists" errors.
    if dialect == "sqlite":
        with op.batch_alter_table("par_levels", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("compartment_id", sa.Integer, nullable=True)
            )
            batch_op.create_index("ix_par_levels_compartment_id", ["compartment_id"])
            batch_op.create_unique_constraint(
                "uq_par_item_compartment", ["item_id", "compartment_id"]
            )
    else:
        # Add column only if it doesn't already exist
        bind.execute(sa.text("""
            ALTER TABLE par_levels
            ADD COLUMN IF NOT EXISTS compartment_id INTEGER
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_par_levels_compartment_id
            ON par_levels (compartment_id)
        """))
        # Unique constraint: no IF NOT EXISTS in PostgreSQL; use catalog check
        bind.execute(sa.text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_par_item_compartment'
                ) THEN
                    ALTER TABLE par_levels
                    ADD CONSTRAINT uq_par_item_compartment
                    UNIQUE (item_id, compartment_id);
                END IF;
            END$$
        """))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("par_levels", schema=None) as batch_op:
            batch_op.drop_constraint("uq_par_item_compartment", type_="unique")
            batch_op.drop_index("ix_par_levels_compartment_id")
            batch_op.drop_column("compartment_id")
    else:
        bind.execute(sa.text("""
            ALTER TABLE par_levels
            DROP CONSTRAINT IF EXISTS uq_par_item_compartment
        """))
        bind.execute(sa.text("""
            DROP INDEX IF EXISTS ix_par_levels_compartment_id
        """))
        bind.execute(sa.text("""
            ALTER TABLE par_levels
            DROP COLUMN IF EXISTS compartment_id
        """))

    if dialect == "sqlite":
        op.drop_index("ix_check_line_items_lot_id", table_name="check_line_items")
        op.drop_index("ix_check_line_items_status", table_name="check_line_items")
        op.drop_index("ix_check_line_items_compartment_id", table_name="check_line_items")
        op.drop_index("ix_check_line_items_check_id", table_name="check_line_items")
        op.drop_table("check_line_items")
        op.drop_index("ix_compartments_location_id", table_name="compartments")
        op.drop_table("compartments")
    else:
        bind.execute(sa.text("DROP TABLE IF EXISTS check_line_items"))
        bind.execute(sa.text("DROP TABLE IF EXISTS compartments"))
