"""
schemas/vehicle.py
Pydantic schemas for Vehicle request validation and response serialization.

Design decisions:
- VehicleType enum is imported from the model to keep a single source of truth.
  Redefining it here would risk divergence.
- requires_controlled_substance_check is a computed property on the ORM model,
  not a DB column. It is included in VehicleRead so callers don't have to
  re-implement the ALS check logic client-side.
- station_id is required on create — vehicles always belong to a station.
  The router validates the station exists before persisting.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Import directly from the model — single source of truth for the enum
from ems_readykit.models.vehicle import VehicleType


class VehicleBase(BaseModel):
    """Fields supplied by the caller on create."""

    station_id: int = Field(
        ...,
        gt=0,
        description="ID of the station this vehicle is assigned to",
    )
    vehicle_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Unique vehicle identifier (e.g. 'AMB-401')",
        examples=["AMB-401"],
    )
    vehicle_type: VehicleType = Field(
        ...,
        description="ALS = Advanced Life Support; BLS = Basic Life Support; QRV = Quick Response Vehicle",
    )
    active: bool = Field(
        default=True,
        description="Whether the vehicle is currently in service",
    )


class VehicleCreate(VehicleBase):
    """Request body for POST /vehicles."""
    pass


class VehicleRead(VehicleBase):
    """
    Response model for vehicle endpoints.
    Includes DB-generated fields and the computed requires_controlled_substance_check
    property so callers don't need to replicate the ALS business rule.
    """

    model_config = ConfigDict(from_attributes=True)

    vehicle_id: int
    created_at: datetime
    updated_at: datetime

    # Computed from vehicle_type — included here for client convenience.
    # This is a read-only derived field; it cannot be set on create/update.
    requires_controlled_substance_check: bool = Field(
        description="True for ALS vehicles only — computed from vehicle_type"
    )
