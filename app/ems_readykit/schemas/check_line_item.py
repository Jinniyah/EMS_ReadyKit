"""
schemas/check_line_item.py
Pydantic schemas for CheckLineItem.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ems_readykit.models.check_line_item import LineItemStatus


class CheckLineItemBase(BaseModel):
    compartment_id:    int           = Field(..., gt=0)
    item_id:           int           = Field(..., gt=0)
    lot_id:            Optional[int] = Field(default=None, gt=0)
    quantity_needed:   int           = Field(default=0, ge=0)
    quantity_found:    int           = Field(default=0, ge=0)
    measurement_value: Optional[float] = Field(default=None)
    functional_pass:   Optional[bool]  = Field(default=None)
    date_value:        Optional[date]  = Field(default=None)
    notes:             Optional[str]   = Field(default=None, max_length=300)


class CheckLineItemCreate(CheckLineItemBase):
    pass


class CheckLineItemRead(CheckLineItemBase):
    model_config = ConfigDict(from_attributes=True)

    line_item_id:    int
    check_id:        int
    status:          LineItemStatus
    lot_number:      Optional[str]  = None
    expiration_date: Optional[date] = None

    # Derived from the Item relationship — tells the frontend how to display this row
    item_name:  Optional[str] = Field(default=None, description="Human-readable item name")
    check_type: Optional[str] = Field(
        default=None,
        description="SUPPLY | MEASUREMENT | FUNCTIONAL | DATE_RECORD | DOCUMENT"
    )

    created_at: datetime
    updated_at: datetime
