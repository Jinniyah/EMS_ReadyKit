"""
Widen alembic_version.version_num from VARCHAR(32) to VARCHAR(64).

Revision ID: 0003a_widen_alembic_version
Revises: 0002_compartments_and_line_items
Create Date: 2026-05-23

Background:
  Alembic historically created alembic_version.version_num as VARCHAR(32).
  Our revision IDs (e.g. '0003_item_check_types_and_equipment') are longer
  than 32 characters, causing a StringDataRightTruncation error on PostgreSQL
  when Alembic tries to stamp the version after running the migration.
  SQLite is unaffected (TEXT type has no length limit).

  This migration must run before 0003 so the version stamp succeeds.
  It is a no-op if the column is already wide enough.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003a_widen_alembic_version"
down_revision: Union[str, None] = "0002_compartments_and_line_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        # ALTER COLUMN TYPE is safe here — no data loss, only widening.
        # The IF EXISTS on the table guard prevents failure if somehow the
        # alembic_version table doesn't exist yet (fresh DB path).
        bind.execute(sa.text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'alembic_version'
                      AND column_name = 'version_num'
                      AND character_maximum_length < 64
                ) THEN
                    ALTER TABLE alembic_version
                    ALTER COLUMN version_num TYPE VARCHAR(64);
                END IF;
            END$$
        """))
    # SQLite: TEXT has no length limit — nothing to do.


def downgrade() -> None:
    # Narrowing back to VARCHAR(32) would break the existing revision IDs
    # already stamped in the table, so downgrade is intentionally a no-op.
    pass
