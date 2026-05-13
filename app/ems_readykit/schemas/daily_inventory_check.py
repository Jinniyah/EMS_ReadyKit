"""
schemas/daily_inventory_check.py
Pydantic schemas for DailyInventoryCheck request validation and response serialization.

Phase 4 change: line_items added to both Create and Read schemas.
- On create, line_items is optional (empty list = header-only check, backward compatible)
- overall status is auto-computed from line items in the router:
    PASS          = all line items OK (or no line items)
    NEEDS_RESTOCK = any line item SHORT
    FAIL          = any line item MISSING
- performed_by is set from JWT identity, not from the request body
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ems_readykit.models.daily_inventory_check import CheckStatus
from ems_readykit.schemas.check_line_item import CheckLineItemCreate, CheckLineItemRead

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
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional free-text notes about the overall check",
    )

    @field_validator("check_date")
    @classmethod
    def validate_check_date_format(cls, v: str) -> str:
        if not _DATE_PATTERN.match(v):
            raise ValueError("check_date must be in YYYY-MM-DD format.")
        return v


class DailyInventoryCheckCreate(DailyInventoryCheckBase):
    """
    Request body for POST /checks/daily.

    line_items is optional — submitting without line items creates a
    header-only check (status defaults to PASS). Submitting line items
    causes the router to compute the overall status automatically.
    """
    line_items: List[CheckLineItemCreate] = Field(
        default_factory=list,
        description=(
            "Line-by-line item counts per compartment. "
            "Each entry maps to one row on the paper form (Need / Have). "
            "Leave empty for a header-only check."
        ),
    )


class DailyInventoryCheckRead(DailyInventoryCheckBase):
    """Response model for daily inventory check endpoints."""

    model_config = ConfigDict(from_attributes=True)

    check_id: int
    status: CheckStatus = Field(
        description="PASS = all OK; NEEDS_RESTOCK = any SHORT; FAIL = any MISSING"
    )
    line_items: List[CheckLineItemRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
