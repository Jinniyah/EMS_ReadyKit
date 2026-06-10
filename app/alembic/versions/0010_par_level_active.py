"""
Add active flag to par_levels table.

Revision ID: 0010_par_level_active
Revises: 0009_item_ai_fields
Create Date: 2026-05-29

Changes (ADMIN-F4):
  Alter table: par_levels
    active  BOOLEAN NOT NULL DEFAULT TRUE

  Index:
    ix_par_levels_active — fast lookup of active par levels for check wizard

Design notes:
  - Soft-deactivate: inactive par levels are excluded from the check wizard
    and compliance queries so crews never see removed items mid-check.
  - Hard-delete is never used — retains the assignment history for audit.
  - Defaults TRUE — all existing par levels remain active after migration.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0010_par_level_active"
down_revision: Union[str, None] = "0009_item_ai_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        op.add_column(
            "par_levels",
            sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        )
        op.create_index("ix_par_levels_active", "par_levels", ["active"])
    else:
        bind.execute(
            sa.text(
                "ALTER TABLE par_levels ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE"
            )
        )
        bind.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_par_levels_active ON par_levels (active)"
            )
        )


def downgrade() -> None:
    op.drop_index("ix_par_levels_active", table_name="par_levels")
    op.drop_column("par_levels", "active")
