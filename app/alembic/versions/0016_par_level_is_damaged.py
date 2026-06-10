"""par_level is_damaged flag

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-05
"""

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("par_levels") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_damaged",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("par_levels") as batch_op:
        batch_op.drop_column("is_damaged")
