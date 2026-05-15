"""
schemas/inventory_location.py
Pydantic schemas for InventoryLocation.

## Location types

    VEHICLE             — attached to one vehicle; auto-created when vehicle is created
    STATION_SUPPLY_ROOM — station restocking inventory; auto-created with station
    JUMP_BAG            — portable bag shared across vehicles (e.g. Units 710/712)
    EQUIPMENT           — standalone equipment with its own inventory (future use)

## Create schema

VEHICLE and STATION_SUPPLY_ROOM locations are system-managed and created
automatically. JUMP_BAG and EQUIPMENT locations can be created via the API
by Supervisors and Administrators using InventoryLocationCreate.

The seed script uses InventoryLocationCreate to create the Jump Bag location
for Ambulance 712 (shared between trucks 710 and 712).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ems_readykit.models.inventory_location import LocationType


class InventoryLocationCreate(BaseModel):
    """
    Request body for POST /inventory/locations.
    Only valid for JUMP_BAG and EQUIPMENT location types.
    VEHICLE and STATION_SUPPLY_ROOM are system-managed.
    """
    location_type: LocationType = Field(
        ...,
        description="JUMP_BAG or EQUIPMENT only — VEHICLE and SUPPLY_ROOM are auto-created",
    )
    station_id: int = Field(..., gt=0, description="Owning station")
    vehicle_id: Optional[int] = Field(
        default=None,
        description="Only set for VEHICLE locations (auto-created). Leave null for JUMP_BAG.",
    )
    label: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Human-readable label shown in UI",
        examples=["Jump Bag (Units 710/712)", "LifePak Monitor — Unit 712"],
    )


class InventoryLocationRead(BaseModel):
    """Response model for inventory location endpoints."""
    model_config = ConfigDict(from_attributes=True)

    location_id: int
    location_type: LocationType = Field(
        description=(
            "VEHICLE | STATION_SUPPLY_ROOM | JUMP_BAG | EQUIPMENT"
        )
    )
    station_id: int
    vehicle_id: Optional[int] = Field(
        default=None,
        description="Set for VEHICLE locations; null for all other types",
    )
    label: str
    created_at: datetime
    updated_at: datetime
