"""
Allow multiple inventory checks per vehicle per calendar day.

Revision ID: 0005_allow_multiple_checks_per_day
Revises: 0004_drop_par_location_unique
Create Date: 2026-05-22

Rationale:
    The original schema enforced one check per vehicle per calendar day via
    uq_check_vehicle_date (vehicle_id, check_date). This assumption breaks
    in two real-world scenarios:

    1. Post-call restock checks: after a significant call, supplies are
       consumed and the vehicle needs to be restocked and re-inventoried
       before going back in service. No one counts supplies during an
       emergency, so a second full check is the correct workflow.

    2. Shift-start / shift-end checks: some stations have legal requirements
       to check inventory at shift handoff in both directions.

    The unique constraint is dropped and replaced with a plain non-unique
    index on (vehicle_id, check_date) which preserves query performance for
    the common "give me all checks for vehicle X on date Y" pattern used by
    the compliance dashboard.

    The timestamp column is the natural discriminator for a specific check
    event within a day. It is set at draft creation time (not submission
    time) so it accurately reflects when the check was started.

SQLite note:
    SQLite does not support DROP CONSTRAINT. The batch_alter_table context
    rebuilds the table without the constraint. The replacement index is
    created separately after the batch operation.

PostgreSQL note:
    Native ALTER TABLE DROP CONSTRAINT with IF EXISTS guard for idempotency.
    The replacement index is created with CREATE INDEX IF NOT EXISTS.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_allow_multiple_checks_per_day"
down_revision: Union[str, None] = "0004_drop_par_location_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # SQLite can't DROP CONSTRAINT directly — batch mode rebuilds the
        # table from scratch using the current model definition, which no
        # longer includes the UniqueConstraint.
        with op.batch_alter_table("daily_inventory_checks", schema=None) as batch_op:
            batch_op.drop_constraint("uq_check_vehicle_date", type_="unique")
        # Add the non-unique replacement index
        op.create_index(
            "ix_check_vehicle_date",
            "daily_inventory_checks",
            ["vehicle_id", "check_date"],
        )
    else:
        # PostgreSQL — native DROP CONSTRAINT
        bind.execute(sa.text("""
            ALTER TABLE daily_inventory_checks
            DROP CONSTRAINT IF EXISTS uq_check_vehicle_date
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_check_vehicle_date
            ON daily_inventory_checks (vehicle_id, check_date)
        """))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # Drop the non-unique index first, then recreate the unique constraint
        op.drop_index("ix_check_vehicle_date", table_name="daily_inventory_checks")
        with op.batch_alter_table("daily_inventory_checks", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                "uq_check_vehicle_date", ["vehicle_id", "check_date"]
            )
    else:
        bind.execute(sa.text("DROP INDEX IF EXISTS ix_check_vehicle_date"))
        bind.execute(sa.text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_check_vehicle_date'
                ) THEN
                    ALTER TABLE daily_inventory_checks
                    ADD CONSTRAINT uq_check_vehicle_date
                    UNIQUE (vehicle_id, check_date);
                END IF;
            END$$
        """))
