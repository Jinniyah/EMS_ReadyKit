"""
Add acknowledgement and soft-delete fields to daily_inventory_checks.

Revision ID: 0007_check_acknowledgement_and_soft_delete
Revises: 0006_repair_requests_and_vehicle_inactive
Create Date: 2026-05-23

Changes:
  B-M7: Alter daily_inventory_checks — add supervisor acknowledgement fields:
    reviewed_by       VARCHAR(100) nullable
    reviewed_at       TIMESTAMP nullable
    corrective_action VARCHAR(500) nullable

  B-M9: Alter daily_inventory_checks — add soft-delete fields:
    deleted_at        TIMESTAMP nullable
    deleted_by        VARCHAR(100) nullable
    deletion_reason   VARCHAR(300) nullable
    force_deleted     BOOLEAN default False

  Soft-delete policy:
    - Soft-deleted checks are hidden from all normal queries immediately.
    - They are preserved in the database and visible to Admin-only endpoints.
    - Hard-deleted automatically after 90 days (scheduled job — see Q-6).
    - Force hard-delete bypasses the 90-day window (PII spill response).

SQLite: batch mode for all ALTER TABLE operations.
PostgreSQL: ADD COLUMN IF NOT EXISTS guards for idempotency on retry.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0007_check_acknowledgement_and_soft_delete"
down_revision: Union[str, None] = "0006_repair_requests_and_vehicle_inactive"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("daily_inventory_checks", schema=None) as batch_op:
            # B-M7 — acknowledgement
            batch_op.add_column(sa.Column("reviewed_by", sa.String(100), nullable=True))
            batch_op.add_column(
                sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
            )
            batch_op.add_column(
                sa.Column("corrective_action", sa.String(500), nullable=True)
            )
            # B-M9 — soft delete
            batch_op.add_column(
                sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
            )
            batch_op.add_column(sa.Column("deleted_by", sa.String(100), nullable=True))
            batch_op.add_column(
                sa.Column("deletion_reason", sa.String(300), nullable=True)
            )
            batch_op.add_column(
                sa.Column(
                    "force_deleted",
                    sa.Boolean,
                    nullable=False,
                    server_default=sa.false(),
                )
            )
    else:
        # B-M7
        bind.execute(sa.text("""
            ALTER TABLE daily_inventory_checks
            ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(100)
        """))
        bind.execute(sa.text("""
            ALTER TABLE daily_inventory_checks
            ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE
        """))
        bind.execute(sa.text("""
            ALTER TABLE daily_inventory_checks
            ADD COLUMN IF NOT EXISTS corrective_action VARCHAR(500)
        """))
        # B-M9
        bind.execute(sa.text("""
            ALTER TABLE daily_inventory_checks
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE
        """))
        bind.execute(sa.text("""
            ALTER TABLE daily_inventory_checks
            ADD COLUMN IF NOT EXISTS deleted_by VARCHAR(100)
        """))
        bind.execute(sa.text("""
            ALTER TABLE daily_inventory_checks
            ADD COLUMN IF NOT EXISTS deletion_reason VARCHAR(300)
        """))
        bind.execute(sa.text("""
            ALTER TABLE daily_inventory_checks
            ADD COLUMN IF NOT EXISTS force_deleted BOOLEAN NOT NULL DEFAULT FALSE
        """))

        # Index for efficient soft-delete filtering
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_daily_checks_deleted_at
            ON daily_inventory_checks (deleted_at)
        """))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("daily_inventory_checks", schema=None) as batch_op:
            batch_op.drop_column("force_deleted")
            batch_op.drop_column("deletion_reason")
            batch_op.drop_column("deleted_by")
            batch_op.drop_column("deleted_at")
            batch_op.drop_column("corrective_action")
            batch_op.drop_column("reviewed_at")
            batch_op.drop_column("reviewed_by")
    else:
        bind.execute(sa.text("DROP INDEX IF EXISTS ix_daily_checks_deleted_at"))
        for col in (
            "force_deleted",
            "deletion_reason",
            "deleted_by",
            "deleted_at",
            "corrective_action",
            "reviewed_at",
            "reviewed_by",
        ):
            bind.execute(sa.text(f"""
                ALTER TABLE daily_inventory_checks
                DROP COLUMN IF EXISTS {col}
            """))
