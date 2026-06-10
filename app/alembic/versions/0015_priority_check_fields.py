"""Add priority_check/question to par_levels and requires_full_check to compartments.

Changes:
  1. par_levels: priority_check BOOLEAN nullable — supervisor marks item for priority confirmation
  2. par_levels: priority_question VARCHAR(150) nullable — custom question shown to responder
  3. compartments: requires_full_check BOOLEAN NOT NULL DEFAULT FALSE — blocks No Change

Revision ID: 0015
Revises:     0014
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision      = '0015'
down_revision = '0014'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        op.add_column('par_levels', sa.Column('priority_check', sa.Boolean, nullable=True))
        op.add_column('par_levels', sa.Column('priority_question', sa.String(150), nullable=True))
        op.add_column('compartments', sa.Column(
            'requires_full_check', sa.Boolean, nullable=False, server_default=sa.false()
        ))
    else:
        bind.execute(sa.text(
            "ALTER TABLE par_levels "
            "ADD COLUMN IF NOT EXISTS priority_check BOOLEAN"
        ))
        bind.execute(sa.text(
            "ALTER TABLE par_levels "
            "ADD COLUMN IF NOT EXISTS priority_question VARCHAR(150)"
        ))
        bind.execute(sa.text(
            "ALTER TABLE compartments "
            "ADD COLUMN IF NOT EXISTS requires_full_check BOOLEAN NOT NULL DEFAULT FALSE"
        ))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        with op.batch_alter_table('par_levels') as batch_op:
            batch_op.drop_column('priority_question')
            batch_op.drop_column('priority_check')
        with op.batch_alter_table('compartments') as batch_op:
            batch_op.drop_column('requires_full_check')
    else:
        bind.execute(sa.text("ALTER TABLE par_levels DROP COLUMN IF EXISTS priority_question"))
        bind.execute(sa.text("ALTER TABLE par_levels DROP COLUMN IF EXISTS priority_check"))
        bind.execute(sa.text("ALTER TABLE compartments DROP COLUMN IF EXISTS requires_full_check"))
