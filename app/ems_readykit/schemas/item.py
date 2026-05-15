"""
schemas/item.py
Pydantic schemas for Item request validation and response serialization.

## check_type field

Drives which fields on CheckLineItem are used and which UI control the
frontend renders. Default is SUPPLY — all pre-existing items are unaffected.

    SUPPLY      counted/presence items (default)
    MEASUREMENT numeric reading items (O2 PSI, temperature)
    FUNCTIONAL  pass/fail checks (battery OK, runs & starts)
    DATE_RECORD date recorded (AED last charge, LUCAS last charge)
    DOCUMENT    presence-only paperwork

## measurement fields (MEASUREMENT items only)

    measurement_minimum  — reading below this → status LOW
                           e.g. O2 PSI minimum 500
    measurement_maximum  — optional ceiling (blood glucose critical high)

## recurrence_days (DATE_RECORD items only)

    recurrence_days — max days between recorded events before OVERDUE
                      e.g. AED charge required every 90 days → 90
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ems_readykit.models.item import ItemCategory, ItemCheckType


class ItemBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Unique item name matching the label on the inventory form",
        examples=["On-Board O2 PSI", "AED Battery", "Kerlix Large"],
    )
    category: ItemCategory = Field(
        ...,
        description="Medication | Consumable | Equipment | Document",
    )
    check_type: ItemCheckType = Field(
        default=ItemCheckType.SUPPLY,
        description=(
            "SUPPLY — counted/presence item (default)\n"
            "MEASUREMENT — numeric reading (O2 PSI, temperature)\n"
            "FUNCTIONAL — pass/fail check (battery OK, runs & starts)\n"
            "DATE_RECORD — date recorded (AED last charge)\n"
            "DOCUMENT — presence-only paperwork"
        ),
    )
    controlled_substance: bool = Field(
        default=False,
        description="True for medications under dual-signature CS tracking (ALS only)",
    )
    unit_of_measure: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description=(
            "Unit of measure for SUPPLY items (each, box, mL, mg...). "
            "For MEASUREMENT items: the reading unit (PSI, °F, mg/dL). "
            "For FUNCTIONAL and DATE_RECORD: use 'N/A'."
        ),
        examples=["each", "PSI", "mg/dL", "N/A"],
    )
    measurement_minimum: Optional[float] = Field(
        default=None,
        description=(
            "MEASUREMENT items only. Reading below this value → status LOW. "
            "e.g. O2 tank minimum 500 PSI."
        ),
    )
    measurement_maximum: Optional[float] = Field(
        default=None,
        description=(
            "MEASUREMENT items only. Reading above this value → status CRITICAL. "
            "Optional — use when an upper bound matters (e.g. blood glucose)."
        ),
    )
    recurrence_days: Optional[int] = Field(
        default=None,
        gt=0,
        description=(
            "DATE_RECORD items only. Maximum days between recorded events "
            "before status → OVERDUE. "
            "e.g. AED must be charged every 90 days → recurrence_days=90."
        ),
    )
    active: bool = Field(
        default=True,
        description="Inactive items hidden from operational views but retained for audit history",
    )

    @field_validator("name", "unit_of_measure", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("Field must not be blank or whitespace only.")
            return stripped
        return v


class ItemCreate(ItemBase):
    """Request body for POST /items."""
    pass


class ItemRead(ItemBase):
    """Response model for item endpoints."""
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    created_at: datetime
    updated_at: datetime
