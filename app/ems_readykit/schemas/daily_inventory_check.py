"""
schemas/daily_inventory_check.py
Pydantic schemas for DailyInventoryCheck request validation and response serialization.

Phase 3 change: performed_by is now Optional in the Create schema.
The router overwrites it with current_user.name from the JWT, so callers
do not need to supply it. Existing seeded data and migration records
that have a value are still serialized correctly by DailyInventoryCheckRead.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ems_readykit.models.daily_inventory_check import CheckStatus

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DailyInventoryCheckBase(BaseModel):
    """Fields common to create and read schemas."""

    vehicle_id: int = Field(..., gt=0, description="Vehicle being checked")
    station_id: int = Field(..., gt=0, description="Station the vehicle belongs to")
    check_date: str = Field(
        ...,
        description="Calendar date of the check in YYYY-MM-DD format",
        examples=["2026-05-09"],
    )
    performed_by: Optional[str] = Field(
        default=None,
        max_length=100,
        description=(
            "Name of the person performing the check. "
            "Set automatically from the authenticated user's identity on create."
        ),
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
        if not _DATE_PATTERN.match(v):
            raise ValueError("check_date must be in YYYY-MM-DD format.")
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
