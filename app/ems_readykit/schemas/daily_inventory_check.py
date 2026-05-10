"""
schemas/daily_inventory_check.py
Pydantic schemas for DailyInventoryCheck request validation and response serialization.

Design decisions:
- check_date is validated as YYYY-MM-DD string to match the model's String(10)
  column. Using date type here would require conversion at every layer —
  keeping it as a validated string is simpler and consistent with the model.
- The UniqueConstraint (vehicle_id, check_date) means only one check per
  vehicle per day. The router catches IntegrityError and returns 409 Conflict
  with a clear message rather than a generic 500.
- performed_by is a free-form string in Phase 2. Phase 3 will bind this to
  the authenticated user identity from the JWT claim.
- station_id is required on create so the check is anchored to a station
  for supervisor-level compliance reporting.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ems_readykit.models.daily_inventory_check import CheckStatus

# YYYY-MM-DD pattern for check_date validation
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DailyInventoryCheckBase(BaseModel):
    """Fields supplied by the caller on create."""

    vehicle_id: int = Field(..., gt=0, description="Vehicle being checked")
    station_id: int = Field(..., gt=0, description="Station the vehicle belongs to")
    check_date: str = Field(
        ...,
        description="Calendar date of the check in YYYY-MM-DD format",
        examples=["2026-05-09"],
    )
    performed_by: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name or identifier of the person performing the check",
        examples=["J. Smith"],
    )
    timestamp: datetime = Field(
        ...,
        description="Exact UTC timestamp when the check was completed",
    )
    status: CheckStatus = Field(
        ...,
        description="PASS = all items at or above par; NEEDS_RESTOCK = below par; FAIL = critical issue",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional free-text notes about the check",
    )

    @field_validator("check_date")
    @classmethod
    def validate_check_date_format(cls, v: str) -> str:
        """
        Enforce YYYY-MM-DD format to match the model's String(10) column.
        This prevents the UniqueConstraint from silently failing due to
        different date string formats representing the same calendar day.
        """
        if not _DATE_PATTERN.match(v):
            raise ValueError("check_date must be in YYYY-MM-DD format.")
        return v

    @field_validator("performed_by", mode="before")
    @classmethod
    def strip_performed_by(cls, v: str) -> str:
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("performed_by must not be blank.")
            return stripped
        return v


class DailyInventoryCheckCreate(DailyInventoryCheckBase):
    """Request body for POST /checks/daily."""
    pass


class DailyInventoryCheckRead(DailyInventoryCheckBase):
    """Response model for daily inventory check endpoints."""

    model_config = ConfigDict(from_attributes=True)

    check_id: int
    created_at: datetime
    updated_at: datetime
