"""ensure supply rooms exist for all active stations

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-06

Stations created through the admin UI (after Session G) never had a
STATION_SUPPLY_ROOM inventory location or compartments created for them.
This migration backfills both so all stations have a usable supply room.
"""

from alembic import op
import sqlalchemy as sa


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Create STATION_SUPPLY_ROOM location for every active station that lacks one
    conn.execute(sa.text("""
        INSERT INTO inventory_locations (station_id, vehicle_id, location_type, label, created_at, updated_at)
        SELECT s.station_id, NULL, 'STATION_SUPPLY_ROOM', 'Station Supply Room',
               CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM stations s
        WHERE s.active = :active
          AND NOT EXISTS (
              SELECT 1 FROM inventory_locations il
              WHERE il.station_id = s.station_id
                AND il.location_type = 'STATION_SUPPLY_ROOM'
          )
    """), {"active": True})

    # Find supply rooms that have no compartments (newly created + any pre-existing gaps)
    result = conn.execute(sa.text("""
        SELECT il.location_id
        FROM inventory_locations il
        WHERE il.location_type = 'STATION_SUPPLY_ROOM'
          AND NOT EXISTS (
              SELECT 1 FROM compartments c WHERE c.location_id = il.location_id
          )
    """))
    empty_supply_rooms = [row[0] for row in result]

    # Create 4 default shelf compartments for each supply room without compartments
    for location_id in empty_supply_rooms:
        for sort_order, name in enumerate(["Shelf 1", "Shelf 2", "Shelf 3", "Shelf 4"], start=1):
            conn.execute(sa.text("""
                INSERT INTO compartments (location_id, name, sort_order, created_at, updated_at)
                VALUES (:location_id, :name, :sort_order, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """), {"location_id": location_id, "name": name, "sort_order": sort_order})


def downgrade():
    pass
