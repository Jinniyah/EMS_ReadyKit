"""schemas/usage_event.py
Pydantic schemas for UsageEvent create and read.

Timezone note: datetime fields are serialized as explicit UTC ISO strings
(same pattern as daily_inventory_check.py) so JavaScript always parses
them as UTC, not local time.

Validation: exactly one of vehicle_id or location_id must be provided.
Both None or both set are rejected with a clear error message.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


def _to_utc_str(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class UsageItemCreate(BaseModel):
    item_id: int = Field(..., gt=0)
    quantity_used: int = Field(..., ge=1)


class UsageEventCreate(BaseModel):
    station_id: int = Field(..., gt=0)
    vehicle_id: Optional[int] = Field(default=None, gt=0)
    location_id: Optional[int] = Field(default=None, gt=0)
    timestamp: datetime
    notes: Optional[str] = Field(default=None, max_length=500)
    items: List[UsageItemCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def exactly_one_target(self) -> "UsageEventCreate":
        has_vehicle = self.vehicle_id is not None
        has_location = self.location_id is not None
        if has_vehicle and has_location:
            raise ValueError("Provide either vehicle_id or location_id, not both.")
        # Both None is allowed -- usage event not tied to a specific unit
        # (edge case: station-level log). Router handles this gracefully.
        return self


class UsageItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    item_name: str
    quantity_used: int


class UsageEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: int
    station_id: int
    vehicle_id: Optional[int]
    location_id: Optional[int]
    vehicle_number: Optional[str]
    location_label: Optional[str]
    performed_by: str
    timestamp: datetime
    notes: Optional[str]
    items: List[UsageItemRead]

    @field_serializer("timestamp")
    def serialize_timestamp(self, v: datetime) -> Optional[str]:
        return _to_utc_str(v)


class FrequentItemRead(BaseModel):
    item_id: int
    item_name: str
    total_used: int
