"""
schemas/station.py
Pydantic schemas for Station request validation and response serialization.

Design decisions:
- StationBase holds all user-supplied fields shared between create and read.
- StationCreate is the POST body — no id or timestamps (DB-generated).
- StationRead is the response model — includes DB-generated fields.
- No StationUpdate in Phase 2; partial updates are Phase 3 (RBAC-gated).
- from_attributes=True enables direct ORM model → schema serialization
  without manual field mapping in router handlers.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StationBase(BaseModel):
    """Fields that are supplied by the caller on create."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable station name",
        examples=["Newberg Township Station 1"],
    )
    address: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Physical street address",
        examples=["100 Fire Station Dr, Newberg Township, MI 48183"],
    )
    region: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Geographic region label used for grouping",
        examples=["Downriver"],
    )
    active: bool = Field(
        default=True,
        description="Whether the station is currently operational",
    )

    @field_validator("name", "address", "region", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Reject blank strings that are all whitespace."""
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("Field must not be blank or whitespace only.")
            return stripped
        return v


class StationCreate(StationBase):
    """Request body for POST /stations."""
    pass


class StationRead(StationBase):
    """
    Response model for station endpoints.
    Includes DB-generated fields: station_id, created_at, updated_at.
    """

    model_config = ConfigDict(from_attributes=True)

    station_id: int
    created_at: datetime
    updated_at: datetime
