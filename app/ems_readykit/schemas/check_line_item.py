"""
schemas/check_line_item.py
Pydantic schemas for CheckLineItem request validation and response serialization.

The line item captures one row of the paper inventory form:
  Need | Have | Item Name                        | Lot       | Exp
  -----+------+----------------------------------+-----------+----------
    2  |  2   | Epi 1:1000 1mg                   | LOT-A123  | 2027-03-15
    2  |  2   | Epi 1:10,000 1mg                 | LOT-B456  | 2026-06-01  ← EXPIRED

status is computed by the router:
  OK      — quantity_found >= quantity_needed and lot not expired
  SHORT   — 0 < quantity_found < quantity_needed and not expired
  MISSING — quantity_found == 0 and quantity_needed > 0
  EXPIRED — lot_id provided and lot.expiration_date <= today

lot_number and expiration_date are populated via hybrid_property on the
CheckLineItem ORM model, which reads from the selectin-loaded lot relationship.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ems_readykit.models.check_line_item import LineItemStatus


class CheckLineItemBase(BaseModel):
    compartment_id: int = Field(..., gt=0, description="Compartment being checked")
    item_id: int = Field(..., gt=0, description="Item being counted")
    lot_id: Optional[int] = Field(
        default=None,
        gt=0,
        description=(
            "Stock lot being inspected. When provided, the router checks the "
            "expiration date and sets status to EXPIRED if past expiry. "
            "Required for medications and any item with a tracked expiration date."
        ),
    )
    quantity_needed: int = Field(
        ..., ge=0,
        description="Expected quantity (par / Need column on the form)",
    )
    quantity_found: int = Field(
        ..., ge=0,
        description="Actual count found (Have column on the form)",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Optional note (e.g. 'lot expires this week', 'used on run 2026-05-12')",
    )


class CheckLineItemCreate(CheckLineItemBase):
    """Submitted as part of DailyInventoryCheckCreate.line_items."""
    pass


class CheckLineItemRead(CheckLineItemBase):
    """
    Response model — includes computed status and expiration info.

    lot_number and expiration_date are read from hybrid_property on
    CheckLineItem which traverses the selectin-loaded lot relationship.
    """

    model_config = ConfigDict(from_attributes=True)

    line_item_id: int
    check_id: int
    status: LineItemStatus

    # Populated via CheckLineItem.lot_number and .expiration_date hybrid properties
    lot_number: Optional[str] = Field(
        default=None,
        description="Lot number from the linked StockLot, if any",
    )
    expiration_date: Optional[date] = Field(
        default=None,
        description="Expiration date from the linked StockLot, if any",
    )

    created_at: datetime
    updated_at: datetime
