"""add location_id to usage_events (USAGE-B2)

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-12

Adds nullable location_id FK to usage_events so items used from portable
locations (jump bags) can be logged against the location rather than a
vehicle. Exactly one of vehicle_id or location_id must be set; this
constraint is enforced at the application layer, not the DB, to keep
the migration simple and compatible with SQLite for testing.
"""

import sqlalchemy as sa

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("usage_events") as batch_op:
        batch_op.add_column(
            sa.Column(
                "location_id",
                sa.Integer(),
                sa.ForeignKey("inventory_locations.location_id"),
                nullable=True,
            )
        )
    op.create_index("ix_usage_events_location_id", "usage_events", ["location_id"])


def downgrade():
    op.drop_index("ix_usage_events_location_id", table_name="usage_events")
    with op.batch_alter_table("usage_events") as batch_op:
        batch_op.drop_column("location_id")
