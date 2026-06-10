"""add usage_events and usage_event_items tables

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-10

usage_events     — one row per after-call usage log submission
usage_event_items — one row per item used within an event

Stock lot FIFO decrement happens at submission time; these tables
record what was logged for history and frequency queries.
"""

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usage_events",
        sa.Column("event_id",     sa.Integer(),             primary_key=True, autoincrement=True),
        sa.Column("station_id",   sa.Integer(),             sa.ForeignKey("stations.station_id"),  nullable=False),
        sa.Column("vehicle_id",   sa.Integer(),             sa.ForeignKey("vehicles.vehicle_id"),  nullable=True),
        sa.Column("performed_by", sa.String(100),           nullable=False),
        sa.Column("timestamp",    sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes",        sa.String(500),           nullable=True),
        sa.Column("created_at",   sa.DateTime(),            nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at",   sa.DateTime(),            nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "usage_event_items",
        sa.Column("usage_item_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id",      sa.Integer(), sa.ForeignKey("usage_events.event_id"), nullable=False),
        sa.Column("item_id",       sa.Integer(), sa.ForeignKey("items.item_id"),         nullable=False),
        sa.Column("quantity_used", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at",    sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at",    sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_usage_events_station_id", "usage_events", ["station_id"])
    op.create_index("ix_usage_events_timestamp",  "usage_events", ["timestamp"])


def downgrade():
    op.drop_index("ix_usage_events_timestamp",  table_name="usage_events")
    op.drop_index("ix_usage_events_station_id", table_name="usage_events")
    op.drop_table("usage_event_items")
    op.drop_table("usage_events")
