"""
schemas/supply_catalog.py
Request / response schemas for the station supply catalog (SR-B1, SR-B2).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from ems_readykit.schemas.stock_lot import StockLotRead


class SupplyCatalogItem(BaseModel):
    """One item's supply-room state: on-hand count, par target, lot detail."""
    item_id: int
    item_name: str
    unit_of_measure: str
    check_type: str
    on_hand: int
    par_min: Optional[int] = None
    lots: List[StockLotRead]


class SupplyCatalogCountPatch(BaseModel):
    """Request body for PATCH /inventory/supply-catalog/items/{id}/count."""
    location_id: int = Field(..., gt=0, description="Supply room location ID")
    quantity: int = Field(..., ge=0, description="New absolute on-hand count")
    comment: Optional[str] = Field(default=None, max_length=500)
