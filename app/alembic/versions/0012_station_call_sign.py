"""
Add call_sign to stations table.

Revision ID: 0012_station_call_sign
Revises: 0011_color_fields
Create Date: 2026-05-30

Changes (ADMIN-B15):
  Alter table: stations
    call_sign  VARCHAR(20) NULL
      Optional short radio/dispatch identifier (e.g. "STA-1").
      Displayed alongside the station name in admin and compliance views.

Design notes:
  - Nullable — existing stations are unaffected; the field defaults to null.
  - No uniqueness constraint at the DB layer (call signs are informal labels
    that may overlap across regions; the frontend validates non-blank only).
  - The primary_color column was added in 0011_color_fields.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_station_call_sign"
down_revision: Union[str, None] = "0011_color_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        op.add_column(
            "stations",
            sa.Column("call_sign", sa.String(20), nullable=True),
        )
    else:
        bind.execute(sa.text(
            "ALTER TABLE stations ADD COLUMN IF NOT EXISTS call_sign VARCHAR(20)"
        ))


def downgrade() -> None:
    op.drop_column("stations", "call_sign")
