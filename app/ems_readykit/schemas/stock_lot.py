"""
schemas/stock_lot.py
Pydantic schemas for StockLot request validation and response serialization.

Design decisions:
- quantity must be >= 0. Zero is valid (empty lot awaiting disposal/return).
  Negative quantities are a data integrity error and rejected at the schema layer.
- expiration_date and lot_number are Optional — equipment and some consumables
  have no expiration date or lot tracking.
- StockLotRead includes a computed 'is_expired' field so clients don't need
  to implement date comparison logic. Computed at serialization time.
- No bulk update endpoint in Phase 2 — individual lot adjustment is the
  safe pattern for audit trail purposes. Bulk operations are Phase 3.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


class StockLotBase(BaseModel):
    """Fields supplied by the caller on create."""

    item_id: int = Field(..., gt=0, description="ID of the item this lot tracks")
    location_id: int = Field(..., gt=0, description="ID of the inventory location holding this lot")
    quantity: int = Field(
        ...,
        ge=0,
        description="Quantity on hand. Zero is valid for empty lots awaiting disposal.",
    )
    lot_number: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Manufacturer lot number for traceability and recall readiness",
        examples=["LOT-EPI-AMB-401"],
    )
    expiration_date: Optional[date] = Field(
        default=None,
        description="Expiration date for medications and dated consumables. Null for equipment.",
    )

    @model_validator(mode="after")
    def expiration_not_in_far_future(self) -> "StockLotBase":
        """
        Sanity check: reject expiration dates more than 10 years out.
        This catches obvious data entry errors (e.g. year 2099 typo)
        without being so strict it blocks legitimate long-shelf-life items.
        """
        if self.expiration_date:
            max_date = date.today().replace(year=date.today().year + 10)
            if self.expiration_date > max_date:
                raise ValueError("Expiration date cannot be more than 10 years in the future.")
        return self


class StockLotCreate(StockLotBase):
    """Request body for POST /inventory/lots."""
    pass


class StockLotRead(StockLotBase):
    """
    Response model for stock lot endpoints.
    Includes DB-generated fields and a computed is_expired convenience field.
    """

    model_config = ConfigDict(from_attributes=True)

    lot_id: int
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def is_expired(self) -> bool:
        """True if the lot has an expiration date that has passed."""
        if self.expiration_date is None:
            return False
        return self.expiration_date < date.today()
