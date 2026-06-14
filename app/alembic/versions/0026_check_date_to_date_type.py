"""convert check_date from String(10) to Date type (CQ-B6)

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-14

Changes daily_inventory_checks.check_date from String(10) to Date type.
ISO-format string comparisons (>=, <=) used in range queries continue to
work correctly after this change -- SQLAlchemy Date type accepts Python
date objects and ISO strings in filters, and the DB stores native dates.

SQLite: batch mode required for column type change.
PostgreSQL: ALTER TABLE ... ALTER COLUMN ... TYPE DATE USING check_date::DATE.
"""

import sqlalchemy as sa

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("daily_inventory_checks") as batch_op:
        batch_op.alter_column(
            "check_date",
            existing_type=sa.String(10),
            type_=sa.Date(),
            existing_nullable=False,
            # PostgreSQL needs an explicit USING cast; SQLite ignores it.
            postgresql_using="check_date::DATE",
        )


def downgrade() -> None:
    with op.batch_alter_table("daily_inventory_checks") as batch_op:
        batch_op.alter_column(
            "check_date",
            existing_type=sa.Date(),
            type_=sa.String(10),
            existing_nullable=False,
            postgresql_using="check_date::TEXT",
        )
