"""
schemas/inventory_location.py
Pydantic schemas for InventoryLocation response serialization.

Design decisions:
- InventoryLocation is NOT user-created via the API in Phase 2.
  Locations are created automatically when a vehicle is added (VEHICLE type)
  or when a station is initialized (STATION_SUPPLY_ROOM type).
  Exposing a create endpoint would allow orphaned locations — deferred to Phase 3.
- Only a Read schema is provided here.
- vehicle_id is Optional because STATION_SUPPLY_ROOM locations have no vehicle.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ems_readykit.models.inventory_location import LocationType


class InventoryLocationRead(BaseModel):
    """
    Response model for inventory location endpoints.
    Read-only in Phase 2 — locations are system-managed.
    """

    model_config = ConfigDict(from_attributes=True)

    location_id: int
    location_type: LocationType = Field(
        description="VEHICLE = attached to a vehicle; STATION_SUPPLY_ROOM = station-level buffer"
    )
    station_id: int
    vehicle_id: Optional[int] = Field(
        default=None,
        description="Set for VEHICLE locations; null for STATION_SUPPLY_ROOM",
    )
    label: str = Field(description="Human-readable location label")
    created_at: datetime
    updated_at: datetime
