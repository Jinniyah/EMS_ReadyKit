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
    # ── compartments ──────────────────────────────────────────────────────────
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

    # ── check_line_items ──────────────────────────────────────────────────────
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
        # Nullable FK to stock_lots — links the specific lot inspected.
        # When provided, the router checks expiration_date and sets status
        # to EXPIRED if the lot has passed its expiration date.
        sa.Column(
            "lot_id",
            sa.Integer,
            sa.ForeignKey("stock_lots.lot_id"),
            nullable=True,
        ),
        sa.Column("quantity_needed", sa.Integer, nullable=False),
        sa.Column("quantity_found", sa.Integer, nullable=False),
        sa.Column("status", sa.String(10), nullable=False),  # OK / SHORT / MISSING / EXPIRED
        sa.Column("notes", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_check_line_items_check_id", "check_line_items", ["check_id"])
    op.create_index("ix_check_line_items_compartment_id", "check_line_items", ["compartment_id"])
    op.create_index("ix_check_line_items_status", "check_line_items", ["status"])
    op.create_index("ix_check_line_items_lot_id", "check_line_items", ["lot_id"])

    # ── par_levels: add compartment_id ────────────────────────────────────────
    op.add_column(
        "par_levels",
        sa.Column(
            "compartment_id",
            sa.Integer,
            sa.ForeignKey("compartments.compartment_id"),
            nullable=True,
        ),
    )
    op.create_index("ix_par_levels_compartment_id", "par_levels", ["compartment_id"])
    op.create_unique_constraint(
        "uq_par_item_compartment", "par_levels", ["item_id", "compartment_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_par_item_compartment", "par_levels", type_="unique")
    op.drop_index("ix_par_levels_compartment_id", table_name="par_levels")
    op.drop_column("par_levels", "compartment_id")

    op.drop_index("ix_check_line_items_lot_id", table_name="check_line_items")
    op.drop_index("ix_check_line_items_status", table_name="check_line_items")
    op.drop_index("ix_check_line_items_compartment_id", table_name="check_line_items")
    op.drop_index("ix_check_line_items_check_id", table_name="check_line_items")
    op.drop_table("check_line_items")

    op.drop_index("ix_compartments_location_id", table_name="compartments")
    op.drop_table("compartments")
