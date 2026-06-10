"""add (station_id, check_date) composite index on daily_inventory_checks

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-09

The compliance calendar queries filter by station_id + check_date.
This index eliminates full-table scans as check volume grows.
Index name: ix_check_station_date (mirrors ix_check_vehicle_date pattern).
"""

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_check_station_date",
        "daily_inventory_checks",
        ["station_id", "check_date"],
    )


def downgrade():
    op.drop_index("ix_check_station_date", table_name="daily_inventory_checks")
