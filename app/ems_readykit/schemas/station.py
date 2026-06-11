"""
schemas/station.py
Pydantic schemas for Station request validation and response serialization.

Design decisions:
- StationBase holds all user-supplied fields shared between create and read.
- StationCreate is the POST body — no id or timestamps (DB-generated).
- StationRead is the response model — includes DB-generated fields.
- from_attributes=True enables direct ORM model → schema serialization
  without manual field mapping in router handlers.

Session F Block 1 (B-M11):
  - primary_color added — optional #rrggbb hex, null = brand default.

Session F Block 2 (ADMIN-B15):
  - call_sign added — optional short radio identifier (e.g. "STA-1").
  - Both new fields are nullable so existing stations are unaffected.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    call_sign: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Short radio/dispatch identifier (e.g. 'STA-1'). Optional.",
    )
    primary_color: Optional[str] = Field(
        default=None,
        max_length=7,
        description="#rrggbb station color. Null = use brand default (#1a3a5c).",
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

    @field_validator("primary_color", mode="before")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        return _validate_hex_color(v)


class StationCreate(StationBase):
    """Request body for POST /stations and POST /admin/stations."""

    pass


class StationRetire(BaseModel):
    """Request body for PATCH /stations/{id}/retire."""

    retirement_reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Why this station is being permanently retired",
    )


class StationRead(StationBase):
    """
    Response model for station endpoints.
    Includes DB-generated fields: station_id, created_at, updated_at.
    """

    model_config = ConfigDict(from_attributes=True)

    station_id: int
    retired_at: Optional[datetime] = None
    retired_by: Optional[str] = None
    retirement_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StationSettingsRead(BaseModel):
    """Response model for GET /stations/{id}/settings (CH-B8)."""

    model_config = ConfigDict(from_attributes=True)

    station_id: int
    allow_check_modification: bool


class StationSettingsPatch(BaseModel):
    """Request body for PATCH /stations/{id}/settings (CH-B7)."""

    allow_check_modification: bool
