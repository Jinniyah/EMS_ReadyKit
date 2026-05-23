"""
schemas/daily_inventory_check.py
Pydantic schemas for DailyInventoryCheck request validation and response serialization.

Phase 7 additions:
  AcknowledgeRequest   — body for PATCH /checks/daily/{id}/acknowledge
  SoftDeleteRequest    — body for DELETE /checks/daily/{id}
  DailyInventoryCheckRead now exposes acknowledgement and soft-delete fields.

Phase 4 change: line_items added to both Create and Read schemas.
- On create, line_items is optional (empty = header-only check, backward compatible)
- Overall status is auto-computed from line items in the router.
- performed_by is set from JWT identity, not from the request body.
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
    vehicle_id:   int = Field(..., gt=0)
    station_id:   int = Field(..., gt=0)
    check_date:   str = Field(..., examples=["2026-05-23"])
    performed_by: Optional[str] = Field(default=None, max_length=100)
    timestamp:    datetime
    notes:        Optional[str] = Field(default=None, max_length=500)

    @field_validator("check_date")
    @classmethod
    def validate_check_date_format(cls, v: str) -> str:
        if not _DATE_PATTERN.match(v):
            raise ValueError("check_date must be in YYYY-MM-DD format.")
        return v


class DailyInventoryCheckCreate(DailyInventoryCheckBase):
    """Request body for POST /checks/daily."""
    line_items: List[CheckLineItemCreate] = Field(default_factory=list)


class AcknowledgeRequest(BaseModel):
    """Body for PATCH /checks/daily/{id}/acknowledge (Supervisor+)."""
    corrective_action: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Required description of corrective action taken",
    )


class SoftDeleteRequest(BaseModel):
    """Body for DELETE /checks/daily/{id} (Supervisor+)."""
    deletion_reason: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Required reason for deleting this check record",
    )


class DailyInventoryCheckRead(DailyInventoryCheckBase):
    """Response model — includes all fields including acknowledgement and soft-delete metadata."""

    model_config = ConfigDict(from_attributes=True)

    check_id:   int
    status:     CheckStatus
    line_items: List[CheckLineItemRead] = Field(default_factory=list)

    # Acknowledgement (B-M7)
    reviewed_by:       Optional[str]
    reviewed_at:       Optional[datetime]
    corrective_action: Optional[str]

    # Soft delete (B-M9)
    deleted_at:      Optional[datetime]
    deleted_by:      Optional[str]
    deletion_reason: Optional[str]
    force_deleted:   bool

    created_at: datetime
    updated_at: datetime
