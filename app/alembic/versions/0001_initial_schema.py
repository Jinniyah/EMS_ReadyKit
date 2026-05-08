"""Initial schema — all domain tables

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-05-06

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── stations ──────────────────────────────────────────────────────────────
    op.create_table(
        "stations",
        sa.Column("station_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── vehicles ──────────────────────────────────────────────────────────────
    op.create_table(
        "vehicles",
        sa.Column("vehicle_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("station_id", sa.Integer, sa.ForeignKey("stations.station_id"), nullable=False),
        sa.Column("vehicle_number", sa.String(20), nullable=False, unique=True),
        sa.Column("vehicle_type", sa.String(10), nullable=False),   # ALS / BLS / QRV
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── inventory_locations ───────────────────────────────────────────────────
    op.create_table(
        "inventory_locations",
        sa.Column("location_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("location_type", sa.String(30), nullable=False),  # VEHICLE / STATION_SUPPLY_ROOM
        sa.Column("station_id", sa.Integer, sa.ForeignKey("stations.station_id"), nullable=False),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.vehicle_id"), nullable=True),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── items ─────────────────────────────────────────────────────────────────
    op.create_table(
        "items",
        sa.Column("item_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("category", sa.String(20), nullable=False),       # Medication / Consumable / Equipment
        sa.Column("controlled_substance", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("unit_of_measure", sa.String(30), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── stock_lots ────────────────────────────────────────────────────────────
    op.create_table(
        "stock_lots",
        sa.Column("lot_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("items.item_id"), nullable=False),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("inventory_locations.location_id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lot_number", sa.String(50), nullable=True),
        sa.Column("expiration_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── par_levels ────────────────────────────────────────────────────────────
    op.create_table(
        "par_levels",
        sa.Column("par_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("items.item_id"), nullable=False),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("inventory_locations.location_id"), nullable=False),
        sa.Column("min_quantity", sa.Integer, nullable=False),
        sa.Column("max_quantity", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("item_id", "location_id", name="uq_par_item_location"),
    )

    # ── daily_inventory_checks ────────────────────────────────────────────────
    op.create_table(
        "daily_inventory_checks",
        sa.Column("check_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.vehicle_id"), nullable=False),
        sa.Column("station_id", sa.Integer, sa.ForeignKey("stations.station_id"), nullable=False),
        sa.Column("check_date", sa.String(10), nullable=False),     # YYYY-MM-DD
        sa.Column("performed_by", sa.String(100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),         # PASS / NEEDS_RESTOCK / FAIL
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("vehicle_id", "check_date", name="uq_check_vehicle_date"),
    )

    # ── controlled_substance_checks ───────────────────────────────────────────
    op.create_table(
        "controlled_substance_checks",
        sa.Column("cs_check_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.vehicle_id"), nullable=False),
        sa.Column("primary_signer", sa.String(100), nullable=False),
        sa.Column("secondary_signer", sa.String(100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("discrepancy_flag", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── audit_events ──────────────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(50), nullable=True),
        sa.Column("station_id", sa.Integer, sa.ForeignKey("stations.station_id"), nullable=True),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.vehicle_id"), nullable=True),
        sa.Column("metadata_json", sa.Text, nullable=True),
        sa.Column("severity", sa.String(10), nullable=False, server_default="INFO"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )

    # ── indexes for common query patterns ─────────────────────────────────────
    op.create_index("ix_vehicles_station_id", "vehicles", ["station_id"])
    op.create_index("ix_stock_lots_location_id", "stock_lots", ["location_id"])
    op.create_index("ix_stock_lots_expiration_date", "stock_lots", ["expiration_date"])
    op.create_index("ix_daily_checks_check_date", "daily_inventory_checks", ["check_date"])
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_severity", "audit_events", ["severity"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("controlled_substance_checks")
    op.drop_table("daily_inventory_checks")
    op.drop_table("par_levels")
    op.drop_table("stock_lots")
    op.drop_table("items")
    op.drop_table("inventory_locations")
    op.drop_table("vehicles")
    op.drop_table("stations")
