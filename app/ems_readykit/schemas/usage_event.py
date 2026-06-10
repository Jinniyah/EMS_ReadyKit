"""schemas/usage_event.py
Pydantic schemas for UsageEvent create and read.

Timezone note: datetime fields are serialized as explicit UTC ISO strings
(same pattern as daily_inventory_check.py) so JavaScript always parses
them as UTC, not local time.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


def _to_utc_str(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class UsageItemCreate(BaseModel):
    item_id:       int = Field(..., gt=0)
    quantity_used: int = Field(..., ge=1)


class UsageEventCreate(BaseModel):
    station_id: int  = Field(..., gt=0)
    vehicle_id: Optional[int] = Field(default=None, gt=0)
    timestamp:  datetime
    notes:      Optional[str] = Field(default=None, max_length=500)
    items:      List[UsageItemCreate] = Field(..., min_length=1)


class UsageItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id:       int
    item_name:     str
    quantity_used: int


class UsageEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id:       int
    station_id:     int
    vehicle_id:     Optional[int]
    vehicle_number: Optional[str]
    performed_by:   str
    timestamp:      datetime
    notes:          Optional[str]
    items:          List[UsageItemRead]

    @field_serializer("timestamp")
    def serialize_timestamp(self, v: datetime) -> Optional[str]:
        return _to_utc_str(v)


class FrequentItemRead(BaseModel):
    item_id:    int
    item_name:  str
    total_used: int
