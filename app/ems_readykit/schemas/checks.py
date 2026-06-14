"""
schemas/checks.py
Pydantic schemas for check-related read models that don't belong in
daily_inventory_check.py (which covers the full check create/read lifecycle).

LastReadingItem -- response shape for GET /checks/daily/last-readings.
  Returns the most recent recorded reading per item on a vehicle or location,
  adjusted for any post-check usage events (USAGE-B1).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class LastReadingItem(BaseModel):
    """Per-item reading from the most recent check, adjusted for post-check usage."""

    item_id: int
    quantity_found: Optional[int]
    measurement_value: Optional[float]
    functional_pass: Optional[bool]
    date_value: Optional[date]
    check_date: str
