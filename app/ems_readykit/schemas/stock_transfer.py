"""
schemas/stock_transfer.py
Pydantic schemas for supply room stock transfer and stock summary.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ems_readykit.schemas.stock_lot import StockLotRead

# ── Transfer request / response ───────────────────────────────────────────────


class TransferRequest(BaseModel):
    from_location_id: int = Field(..., gt=0, description="Source inventory location")
    to_location_id: int = Field(..., gt=0, description="Destination inventory location")
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, description="Units to move; must be positive")
    notes: Optional[str] = Field(default=None, max_length=500)


class StockTransferRead(BaseModel):
    """Response shape for a completed transfer or history record."""

    transfer_id: int
    from_location_id: Optional[int] = None
    to_location_id: int
    from_location_label: Optional[str] = None
    to_location_label: str
    item_id: int
    item_name: str
    quantity: int
    transferred_by: str
    notes: Optional[str] = None
    lot_number: Optional[str] = None
    lot_expiration_date: Optional[date] = None
    transferred_at: datetime


# ── Stock summary (per-item view for a location) ──────────────────────────────


class StockItemSummary(BaseModel):
    """Aggregated stock state for one item at a location."""

    item_id: int
    item_name: str
    item_category: str
    total_quantity: int
    par_min: Optional[int] = None
    par_max: Optional[int] = None
    status: str  # "OK" | "LOW" | "OUT" | "NO_PAR"
    is_any_expiring: bool  # any lot expiring within 30 days (not yet expired)
    is_any_expired: bool  # any lot already past expiry
    lots: List[StockLotRead]


# ── CSV receive result ────────────────────────────────────────────────────────


class CsvReceiveResult(BaseModel):
    rows_imported: int
    rows_skipped: int
    errors: List[Dict[str, Any]]
    lots_created: List[StockLotRead]
