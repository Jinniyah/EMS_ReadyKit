"""add deactivated_at and deactivation_reason to par_levels (B-M6)

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-11

Records when and why a par level assignment was removed (soft-deactivated).
"""

import sqlalchemy as sa

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("par_levels") as batch_op:
        batch_op.add_column(
            sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("deactivation_reason", sa.String(500), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("par_levels") as batch_op:
        batch_op.drop_column("deactivation_reason")
        batch_op.drop_column("deactivated_at")
