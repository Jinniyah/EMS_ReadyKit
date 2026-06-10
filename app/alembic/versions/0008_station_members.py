"""
Add station_members table.

Revision ID: 0008_station_members
Revises: 0007_check_acknowledgement_and_soft_delete
Create Date: 2026-05-25

Changes (B-ACCESS1 / ACC-M1, ACC-M2):
  New table: station_members
    member_id       SERIAL PRIMARY KEY
    station_id      INTEGER NOT NULL FK → stations.station_id
    user_id         VARCHAR(255) NOT NULL  — Azure AD preferred_username (email)
    preferred_name  VARCHAR(100) nullable  — display name set by admin
    role            VARCHAR(50)  NOT NULL  — Administrator / Supervisor / Responder
    assigned_by     VARCHAR(255) NOT NULL  — UPN of assigning user (audit trail)
    assigned_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
    active          BOOLEAN NOT NULL DEFAULT TRUE
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()

  Indexes:
    ix_station_members_station_id  — fast lookup of members for a station
    ix_station_members_user_id     — fast lookup of stations for a user
    uq_station_members_station_user — one row per user per station

  Note: soft-delete via active=False preserves history.
  The unique constraint applies to all rows (active or not) — attempting to
  re-add a removed user should UPSERT the existing row back to active=True
  rather than insert a new row (handled in the router, not the DB).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0008_station_members"
down_revision: Union[str, None] = "0007_check_acknowledgement_and_soft_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        op.create_table(
            "station_members",
            sa.Column("member_id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "station_id",
                sa.Integer,
                sa.ForeignKey("stations.station_id"),
                nullable=False,
            ),
            sa.Column("user_id", sa.String(255), nullable=False),
            sa.Column("preferred_name", sa.String(100), nullable=True),
            sa.Column("role", sa.String(50), nullable=False),
            sa.Column("assigned_by", sa.String(255), nullable=False),
            sa.Column(
                "assigned_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "station_id", "user_id", name="uq_station_members_station_user"
            ),
        )
        op.create_index(
            "ix_station_members_station_id", "station_members", ["station_id"]
        )
        op.create_index("ix_station_members_user_id", "station_members", ["user_id"])
    else:
        # PostgreSQL — idempotent with IF NOT EXISTS guards
        bind.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS station_members (
                member_id       SERIAL PRIMARY KEY,
                station_id      INTEGER NOT NULL REFERENCES stations(station_id),
                user_id         VARCHAR(255) NOT NULL,
                preferred_name  VARCHAR(100),
                role            VARCHAR(50) NOT NULL,
                assigned_by     VARCHAR(255) NOT NULL,
                assigned_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                active          BOOLEAN NOT NULL DEFAULT TRUE,
                created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                CONSTRAINT uq_station_members_station_user UNIQUE (station_id, user_id)
            )
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_station_members_station_id
            ON station_members (station_id)
        """))
        bind.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_station_members_user_id
            ON station_members (user_id)
        """))


def downgrade() -> None:
    op.drop_table("station_members")
