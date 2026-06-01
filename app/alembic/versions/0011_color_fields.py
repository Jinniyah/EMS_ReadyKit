"""
Add color fields to stations and vehicles.

Revision ID: 0011_color_fields
Revises: 0010_par_level_active
Create Date: 2026-05-30

Changes (B-M11 + NEW-M1):
  Alter table: stations
    primary_color  VARCHAR(7) NULL
      CSS hex color (e.g. "#1a3a5c"). Nullable — stations without an
      explicit color fall back to the brand default in the frontend.

  Alter table: vehicles
    vehicle_color  VARCHAR(7) NULL
      Per-vehicle override. Null = inherit station's primary_color.
      Set on creation or via PATCH /admin/vehicles/{id}/color.

Design notes:
  - Seven-character hex (#rrggbb) is the canonical format throughout.
    The ColorPickerWidget writes and validates this format.
  - station.primary_color drives the header, buttons, and station card
    color bar in the picker.
  - vehicle.vehicle_color overrides per vehicle in the compliance calendar
    (F-5F2) so supervisors can distinguish vehicles at a glance.
  - Both default NULL — existing data is unaffected; the frontend already
    falls back to --color-brand when no color is set.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_color_fields"
down_revision: Union[str, None] = "0010_par_level_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        op.add_column(
            "stations",
            sa.Column("primary_color", sa.String(7), nullable=True),
        )
        op.add_column(
            "vehicles",
            sa.Column("vehicle_color", sa.String(7), nullable=True),
        )
    else:
        bind.execute(sa.text(
            "ALTER TABLE stations ADD COLUMN IF NOT EXISTS primary_color VARCHAR(7)"
        ))
        bind.execute(sa.text(
            "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS vehicle_color VARCHAR(7)"
        ))


def downgrade() -> None:
    op.drop_column("stations", "primary_color")
    op.drop_column("vehicles", "vehicle_color")
