"""
Add category_group to items (cabinet grouping for Item Catalog UI).

Revision ID: 0029
Revises: 0028
Create Date: 2026-06-20

Changes:
  - Adds items.category_group (String 100, nullable) for ITM-3 cabinet grouping.
    Values populated by seed.py in ITM-4.
"""

import sqlalchemy as sa

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("category_group", sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.drop_column("category_group")
