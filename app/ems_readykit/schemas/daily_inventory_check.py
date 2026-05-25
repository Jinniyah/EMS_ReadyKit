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

Timezone note:
  All datetime columns use DateTime(timezone=True) and store UTC in the DB.
  SQLite returns naive datetime objects (no tzinfo), which Pydantic would
  serialize without a 'Z' suffix, causing browsers to parse them as local time.
  The model_serializer below ensures every datetime in API responses is
  emitted as an explicit UTC ISO string (e.g. '2026-05-25T13:01:00Z') so
  JavaScript new Date(...) always interprets it as UTC, not local time.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from ems_readykit.models.daily_inventory_check import CheckStatus
from ems_readykit.schemas.check_line_item import CheckLineItemCreate, CheckLineItemRead

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _to_utc_str(dt: Optional[datetime]) -> Optional[str]:
    """Ensure a datetime is serialized as an explicit UTC ISO string with 'Z' suffix."""
    if dt is None:
        return None
    # If the datetime is naive (no tzinfo), assume it is UTC (as stored by SQLite).
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


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

    # Ensure all datetime fields are serialized as explicit UTC strings so
    # JavaScript new Date(...) always parses them as UTC, not local time.
    @field_serializer('timestamp', 'reviewed_at', 'deleted_at', 'created_at', 'updated_at')
    def serialize_utc(self, dt: Optional[datetime]) -> Optional[str]:
        return _to_utc_str(dt)
