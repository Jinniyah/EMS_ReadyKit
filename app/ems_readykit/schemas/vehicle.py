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
- vehicle_color (NEW-M1): optional #rrggbb hex, nullable.
  Null = inherit station.primary_color in the frontend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ems_readykit.models.vehicle import VehicleType

# ── Hex color validator (shared with station schema) ─────────────────────────


def _validate_hex_color(v: Optional[str]) -> Optional[str]:
    """Accept None or a valid 7-char CSS hex color (#rrggbb)."""
    if v is None:
        return v
    if (
        len(v) != 7
        or v[0] != "#"
        or not all(c in "0123456789abcdefABCDEF" for c in v[1:])
    ):
        raise ValueError("color must be a 7-character hex string, e.g. '#1a3a5c'")
    return v.lower()


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

    vehicle_color: Optional[str] = Field(
        default=None,
        max_length=7,
        description="Optional #rrggbb color. Null = inherit station color.",
    )

    @field_validator("vehicle_color", mode="before")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        return _validate_hex_color(v)


class VehicleUpdate(BaseModel):
    """
    Request body for PATCH /vehicles/{id} (Supervisor+).
    Allows toggling active status with a mandatory reason when deactivating.
    """

    active: bool = Field(..., description="True = in service; False = out of service")
    inactive_reason: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Required when active is False — explain why the vehicle is being taken out of service",
    )


class VehicleDetailsUpdate(BaseModel):
    """Request body for PATCH /admin/vehicles/{id}/details (Admin only)."""

    vehicle_number: str = Field(..., min_length=1, max_length=20)
    vehicle_type: VehicleType


class VehicleColorUpdate(BaseModel):
    """Request body for PATCH /admin/vehicles/{id}/color (ADMIN-UX1-V)."""

    vehicle_color: Optional[str] = Field(
        default=None,
        max_length=7,
        description="#rrggbb color, or null to clear (inherit station color).",
    )

    @field_validator("vehicle_color", mode="before")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        return _validate_hex_color(v)


class VehicleRead(VehicleBase):
    """
    Response model for vehicle endpoints.
    Includes DB-generated fields, the computed requires_controlled_substance_check
    property, and the inactive / color metadata fields.
    """

    model_config = ConfigDict(from_attributes=True)

    vehicle_id: int
    inactive_reason: Optional[str]
    inactive_since: Optional[datetime]
    vehicle_color: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Computed from vehicle_type — included here for client convenience.
    requires_controlled_substance_check: bool = Field(
        description="True for ALS vehicles only — computed from vehicle_type"
    )
