"""add allow_check_modification to stations (B-M10)

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-10

Controls whether submitted checks can be modified by crew. Default True.
Prerequisite for CH-F6 (acknowledgement / corrective note).
"""

import sqlalchemy as sa

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("stations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "allow_check_modification",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("stations") as batch_op:
        batch_op.drop_column("allow_check_modification")
