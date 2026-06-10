"""Make vehicle_id nullable on daily_inventory_checks; add location_id for portable checks.

Jump bags and other portable locations need their own check records.
Previously vehicle_id was NOT NULL which made it impossible to submit a
portable location check. This migration:
  1. Makes vehicle_id nullable (existing vehicle checks are unaffected)
  2. Adds location_id column (FK to inventory_locations) for portable checks
  3. Adds an index on (location_id, check_date) to support compliance queries

Revision ID: 0013
Revises:     0012_station_call_sign
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision   = '0013'
down_revision = '0012_station_call_sign'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    with op.batch_alter_table("daily_inventory_checks", schema=None) as batch_op:
        batch_op.alter_column(
            "vehicle_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column("location_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index(
            "ix_check_location_date", ["location_id", "check_date"]
        )


def downgrade() -> None:
    with op.batch_alter_table("daily_inventory_checks", schema=None) as batch_op:
        batch_op.drop_index("ix_check_location_date")
        batch_op.drop_column("location_id")
        batch_op.alter_column(
            "vehicle_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
