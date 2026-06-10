"""
Add repair_requests table and inactive columns to vehicles.

Revision ID: 0006_repair_requests_and_vehicle_inactive
Revises: 0005_allow_multiple_checks_per_day
Create Date: 2026-05-23

Changes:
  - New table: repair_requests
    Tracks maintenance issues filed against a vehicle. Severity can be
    ROUTINE or URGENT. Status lifecycle: OPEN → IN_PROGRESS → RESOLVED.
  - Alter vehicles: add inactive_reason (VARCHAR 200, nullable) and
    inactive_since (TIMESTAMP, nullable).
    Note: the `active` column already exists from migration 0001.

SQLite note:
  New table uses op.create_table (compatible with SQLite).
  ALTER TABLE uses batch mode for SQLite.

PostgreSQL note:
  Uses raw DDL with IF NOT EXISTS / ADD COLUMN IF NOT EXISTS guards
  for full idempotency on retry after a partial failure.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0006_repair_requests_and_vehicle_inactive"
down_revision: Union[str, None] = "0005_allow_multiple_checks_per_day"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # ── repair_requests ───────────────────────────────────────────────────────
    if dialect == "sqlite":
        op.create_table(
            "repair_requests",
            sa.Column("repair_id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "vehicle_id",
                sa.Integer,
                sa.ForeignKey("vehicles.vehicle_id"),
                nullable=False,
            ),
            sa.Column(
                "station_id",
                sa.Integer,
                sa.ForeignKey("stations.station_id"),
                nullable=False,
            ),
            sa.Column("reported_by", sa.String(100), nullable=False),
            sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("severity", sa.String(10), nullable=False, server_default="ROUTINE"),
            sa.Column("description", sa.String(500), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
            sa.Column("resolved_by", sa.String(100), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolution_notes", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_repair_requests_vehicle_id", "repair_requests", ["vehicle_id"])
        op.create_index("ix_repair_requests_status", "repair_requests", ["status"])
        op.create_index("ix_repair_requests_severity", "repair_requests", ["severity"])
    else:
        bind.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS repair_requests (
                repair_id        SERIAL PRIMARY KEY,
                vehicle_id       INTEGER NOT NULL
                                 REFERENCES vehicles(vehicle_id),
                station_id       INTEGER NOT NULL
                                 REFERENCES stations(station_id),
                reported_by      VARCHAR(100) NOT NULL,
                reported_at      TIMESTAMP WITH TIME ZONE NOT NULL,
                severity         VARCHAR(10) NOT NULL DEFAULT 'ROUTINE',
                description      VARCHAR(500) NOT NULL,
                status           VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                resolved_by      VARCHAR(100),
                resolved_at      TIMESTAMP WITH TIME ZONE,
                resolution_notes VARCHAR(500),
                created_at       TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at       TIMESTAMP WITH TIME ZONE NOT NULL
            )
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_repair_requests_vehicle_id
            ON repair_requests (vehicle_id)
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_repair_requests_status
            ON repair_requests (status)
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_repair_requests_severity
            ON repair_requests (severity)
        """))

    # ── vehicles: add inactive_reason + inactive_since ────────────────────────
    # `active` already exists (migration 0001). We are only adding the two
    # companion columns that explain *why* and *when* a vehicle was deactivated.
    if dialect == "sqlite":
        with op.batch_alter_table("vehicles", schema=None) as batch_op:
            batch_op.add_column(sa.Column("inactive_reason", sa.String(200), nullable=True))
            batch_op.add_column(sa.Column("inactive_since", sa.DateTime(timezone=True), nullable=True))
    else:
        bind.execute(sa.text("""
            ALTER TABLE vehicles
            ADD COLUMN IF NOT EXISTS inactive_reason VARCHAR(200)
        """))
        bind.execute(sa.text("""
            ALTER TABLE vehicles
            ADD COLUMN IF NOT EXISTS inactive_since TIMESTAMP WITH TIME ZONE
        """))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("vehicles", schema=None) as batch_op:
            batch_op.drop_column("inactive_since")
            batch_op.drop_column("inactive_reason")

        op.drop_index("ix_repair_requests_severity", table_name="repair_requests")
        op.drop_index("ix_repair_requests_status", table_name="repair_requests")
        op.drop_index("ix_repair_requests_vehicle_id", table_name="repair_requests")
        op.drop_table("repair_requests")
    else:
        bind.execute(sa.text("""
            ALTER TABLE vehicles
            DROP COLUMN IF EXISTS inactive_since
        """))
        bind.execute(sa.text("""
            ALTER TABLE vehicles
            DROP COLUMN IF EXISTS inactive_reason
        """))
        bind.execute(sa.text("DROP TABLE IF EXISTS repair_requests"))
