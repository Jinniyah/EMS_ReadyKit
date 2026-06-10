"""
Drop the legacy uq_par_item_location unique constraint from par_levels.

Revision ID: 0004_drop_par_location_unique
Revises: 0003_item_check_types_and_equipment
Create Date: 2026-05-16

Rationale:
    Migration 0002 added compartment_id to par_levels and introduced
    uq_par_item_compartment (item_id, compartment_id) as the correct
    uniqueness constraint for compartment-scoped par levels.

    The original uq_par_item_location constraint (item_id, location_id)
    predates compartments. It was correct when par levels were vehicle-scoped
    only, but is now wrong: the same item (e.g. "Stethoscope") legitimately
    appears in multiple compartments on the same vehicle. Retaining this
    constraint prevents seeding or restocking any item that appears in more
    than one compartment on the same truck.

    uq_par_item_compartment is the sole correct uniqueness constraint going
    forward: one par level per item per compartment.

SQLite note:
    SQLite does not support DROP CONSTRAINT. Batch mode rebuilds the table
    without the constraint.

PostgreSQL note:
    Native ALTER TABLE DROP CONSTRAINT with IF EXISTS guard for idempotency.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0004_drop_par_location_unique"
down_revision: Union[str, None] = "0003_item_check_types_and_equipment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # Batch mode rebuilds the table — SQLAlchemy re-applies only the
        # constraints declared in __table_args__, so uq_par_item_location
        # is excluded by not being present in the batch_alter context.
        with op.batch_alter_table("par_levels", schema=None) as batch_op:
            batch_op.drop_constraint("uq_par_item_location", type_="unique")
    else:
        bind.execute(sa.text("""
            ALTER TABLE par_levels
            DROP CONSTRAINT IF EXISTS uq_par_item_location
        """))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("par_levels", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                "uq_par_item_location", ["item_id", "location_id"]
            )
    else:
        bind.execute(sa.text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_par_item_location'
                ) THEN
                    ALTER TABLE par_levels
                    ADD CONSTRAINT uq_par_item_location
                    UNIQUE (item_id, location_id);
                END IF;
            END$$
        """))
