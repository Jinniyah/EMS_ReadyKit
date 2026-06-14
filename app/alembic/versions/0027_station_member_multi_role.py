"""
Drop station_member single-user constraint; allow multiple roles per person (ACC-B7 Option A).

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-14

Changes:
  - Drops uq_station_members_station_user (station_id, user_id)
  - Adds uq_station_members_station_user_role (station_id, user_id, role)

This allows one person to hold multiple roles at the same station by having
multiple active StationMember rows (one per role). Role resolution uses
highest-privilege wins: Administrator > Supervisor > Responder.

No data migration needed — existing rows have one role each and will continue
to satisfy the new constraint without modification.
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("station_members") as batch_op:
        batch_op.drop_constraint("uq_station_members_station_user", type_="unique")
        batch_op.create_unique_constraint(
            "uq_station_members_station_user_role",
            ["station_id", "user_id", "role"],
        )


def downgrade() -> None:
    with op.batch_alter_table("station_members") as batch_op:
        batch_op.drop_constraint("uq_station_members_station_user_role", type_="unique")
        batch_op.create_unique_constraint(
            "uq_station_members_station_user",
            ["station_id", "user_id"],
        )
