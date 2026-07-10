"""add retirement fields to vehicles, locations, stations, stock_lots (RET-M1/M2/M3)

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-11

retired_at / retired_by / retirement_reason on:
  vehicles, inventory_locations, stations, stock_lots

Retirement is permanent decommissioning; distinct from temporary OOS (active=False on vehicles).
"""

import sqlalchemy as sa

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

_RETIREMENT_COLUMNS = [
    sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("retired_by", sa.String(255), nullable=True),
    sa.Column("retirement_reason", sa.String(500), nullable=True),
]


def upgrade() -> None:
    for table in ("vehicles", "inventory_locations", "stations", "stock_lots"):
        with op.batch_alter_table(table) as batch_op:
            for col in _RETIREMENT_COLUMNS:
                batch_op.add_column(col.copy())


def downgrade() -> None:
    for table in ("vehicles", "inventory_locations", "stations", "stock_lots"):
        with op.batch_alter_table(table) as batch_op:
            for col in _RETIREMENT_COLUMNS:
                batch_op.drop_column(col.name)
