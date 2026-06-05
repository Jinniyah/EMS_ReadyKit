"""Add stock_transfers table and backfill supply room compartments.

Changes:
  1. Creates stock_transfers table (transfer history)
  2. For any existing STATION_SUPPLY_ROOM that has zero compartments,
     inserts 4 default shelf compartments so the supply room UI is usable
     without a full re-seed.

Revision ID: 0014
Revises:     0013
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision      = '0014'
down_revision = '0013'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── 1. stock_transfers table ───────────────────────────────────────────────
    op.create_table(
        "stock_transfers",
        sa.Column("transfer_id",          sa.Integer(),      primary_key=True, autoincrement=True),
        sa.Column("from_location_id",     sa.Integer(),      sa.ForeignKey("inventory_locations.location_id"), nullable=True),
        sa.Column("to_location_id",       sa.Integer(),      sa.ForeignKey("inventory_locations.location_id"), nullable=False),
        sa.Column("item_id",              sa.Integer(),      sa.ForeignKey("items.item_id"), nullable=False),
        sa.Column("quantity",             sa.Integer(),      nullable=False),
        sa.Column("transferred_by",       sa.String(255),    nullable=False),
        sa.Column("notes",                sa.String(500),    nullable=True),
        sa.Column("lot_number",           sa.String(50),     nullable=True),
        sa.Column("lot_expiration_date",  sa.Date(),         nullable=True),
        sa.Column("created_at",           sa.DateTime(),     nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at",           sa.DateTime(),     nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_stock_transfer_from_loc", "stock_transfers", ["from_location_id"])
    op.create_index("ix_stock_transfer_to_loc",   "stock_transfers", ["to_location_id"])
    op.create_index("ix_stock_transfer_item",     "stock_transfers", ["item_id"])

    # ── 2. Backfill default compartments for supply rooms that have none ───────
    conn = op.get_bind()

    supply_rooms = conn.execute(
        sa.text(
            "SELECT location_id FROM inventory_locations "
            "WHERE location_type = 'STATION_SUPPLY_ROOM'"
        )
    ).fetchall()

    default_compartments = [
        ("Cab 1 - Shelf 1", "Cabinet 1, top shelf — airway & PPE supplies",       1),
        ("Cab 1 - Shelf 2", "Cabinet 1, bottom shelf — dressings & bandages",      2),
        ("Cab 2 - Shelf 1", "Cabinet 2, top shelf — medications & controlled items", 3),
        ("Cab 2 - Shelf 2", "Cabinet 2, bottom shelf — equipment & restock items", 4),
    ]

    for row in supply_rooms:
        loc_id = row[0]

        existing_count = conn.execute(
            sa.text("SELECT COUNT(*) FROM compartments WHERE location_id = :lid"),
            {"lid": loc_id},
        ).scalar()

        if existing_count and existing_count > 0:
            continue

        for name, descriptor, sort_order in default_compartments:
            conn.execute(
                sa.text(
                    "INSERT INTO compartments "
                    "(location_id, name, location_descriptor, sort_order, als_only, active, "
                    " created_at, updated_at) "
                    "VALUES (:lid, :name, :desc, :sort, 0, 1, "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"lid": loc_id, "name": name, "desc": descriptor, "sort": sort_order},
            )


def downgrade() -> None:
    op.drop_index("ix_stock_transfer_item",     table_name="stock_transfers")
    op.drop_index("ix_stock_transfer_to_loc",   table_name="stock_transfers")
    op.drop_index("ix_stock_transfer_from_loc", table_name="stock_transfers")
    op.drop_table("stock_transfers")
