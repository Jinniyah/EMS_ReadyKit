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
- inactive_reason and inactive_since are set by PATCH /vehicles/{id} (Supervisor+)
  when flipping active to False. They are read-only on the response.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

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


class VehicleUpdate(BaseModel):
    """
    Request body for PATCH /vehicles/{id} (Supervisor+).
    Allows toggling active status with a mandatory reason when deactivating.
    """
    active:          bool = Field(..., description="True = in service; False = out of service")
    inactive_reason: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Required when active is False — explain why the vehicle is being taken out of service",
    )


class VehicleRead(VehicleBase):
    """
    Response model for vehicle endpoints.
    Includes DB-generated fields, the computed requires_controlled_substance_check
    property, and the inactive metadata fields.
    """

    model_config = ConfigDict(from_attributes=True)

    vehicle_id:      int
    inactive_reason: Optional[str]
    inactive_since:  Optional[datetime]
    created_at:      datetime
    updated_at:      datetime

    # Computed from vehicle_type — included here for client convenience.
    requires_controlled_substance_check: bool = Field(
        description="True for ALS vehicles only — computed from vehicle_type"
    )
