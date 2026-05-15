"""
schemas/check_line_item.py
Pydantic schemas for CheckLineItem — one verified line of a daily inventory check.

## Field routing by item check_type

    SUPPLY (default):
        quantity_needed, quantity_found, lot_id
        status → OK / SHORT / MISSING / EXPIRED

    MEASUREMENT (O2 PSI, glucose, temperature):
        measurement_value  (float reading)
        quantity_needed = quantity_found = 0 (unused)
        status → OK / LOW

    FUNCTIONAL (battery OK, runs & starts, lights & sirens):
        functional_pass  (True/False)
        status → OK / FAIL

    DATE_RECORD (AED last charge, LUCAS last charge):
        date_value  (date recorded)
        status → OK / OVERDUE

    DOCUMENT (PCR form, protocol book):
        quantity_needed = 1, quantity_found = 0 or 1
        status → OK / MISSING

## Real examples from Ambulance 712

    # O2 PSI reading — MEASUREMENT
    {"item_id": 42, "compartment_id": 8,
     "measurement_value": 1800.0,
     "quantity_needed": 0, "quantity_found": 0}
    → status: OK (1800 >= minimum 500)

    # AED battery check — FUNCTIONAL
    {"item_id": 43, "compartment_id": 8,
     "functional_pass": true,
     "quantity_needed": 0, "quantity_found": 0}
    → status: OK

    # AED last charge date — DATE_RECORD
    {"item_id": 44, "compartment_id": 8,
     "date_value": "2026-04-28",
     "quantity_needed": 0, "quantity_found": 0}
    → status: OK if within recurrence_days (e.g. 90)

    # AED pads adult — SUPPLY with expiry
    {"item_id": 45, "compartment_id": 8,
     "lot_id": 12,
     "quantity_needed": 1, "quantity_found": 1}
    → status: OK or EXPIRED depending on lot.expiration_date
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ems_readykit.models.check_line_item import LineItemStatus


class CheckLineItemBase(BaseModel):
    compartment_id: int = Field(..., gt=0, description="Compartment being checked")
    item_id: int = Field(..., gt=0, description="Item being verified")

    # ── SUPPLY fields ──────────────────────────────────────────────────────────
    lot_id: Optional[int] = Field(
        default=None,
        gt=0,
        description=(
            "SUPPLY items with expiration dates. "
            "Router validates lot belongs to item and checks expiration date."
        ),
    )
    quantity_needed: int = Field(
        default=0,
        ge=0,
        description="Par/Need quantity. 0 for MEASUREMENT, FUNCTIONAL, DATE_RECORD items.",
    )
    quantity_found: int = Field(
        default=0,
        ge=0,
        description="Actual count found. 0 for MEASUREMENT, FUNCTIONAL, DATE_RECORD items.",
    )

    # ── MEASUREMENT fields ─────────────────────────────────────────────────────
    measurement_value: Optional[float] = Field(
        default=None,
        description=(
            "MEASUREMENT items only. Numeric reading recorded by crew. "
            "e.g. O2 PSI = 1800.0, temperature = 98.6"
        ),
    )

    # ── FUNCTIONAL fields ──────────────────────────────────────────────────────
    functional_pass: Optional[bool] = Field(
        default=None,
        description=(
            "FUNCTIONAL items only. "
            "True = passed (battery OK, siren works). "
            "False = failed → status FAIL → check overall FAIL."
        ),
    )

    # ── DATE_RECORD fields ─────────────────────────────────────────────────────
    date_value: Optional[date] = Field(
        default=None,
        description=(
            "DATE_RECORD items only. Date recorded by crew. "
            "e.g. AED last charge date = '2026-04-28'. "
            "Router compares against item.recurrence_days to determine OVERDUE."
        ),
    )

    # ── Common ─────────────────────────────────────────────────────────────────
    notes: Optional[str] = Field(
        default=None,
        max_length=300,
        description=(
            "Optional crew note. Required when status is FAIL, EXPIRED, or OVERDUE "
            "to document what action was taken. "
            "e.g. 'O2 PSI low — tank swapped from supply room, now at 1800 PSI'"
        ),
    )


class CheckLineItemCreate(CheckLineItemBase):
    """Submitted as part of DailyInventoryCheckCreate.line_items."""
    pass


class CheckLineItemRead(CheckLineItemBase):
    """
    Response model — includes computed status and all type-specific fields.
    lot_number and expiration_date are read from hybrid_property on the
    CheckLineItem ORM model via the selectin-loaded lot relationship.
    """
    model_config = ConfigDict(from_attributes=True)

    line_item_id: int
    check_id: int
    status: LineItemStatus

    # Populated via CheckLineItem.lot_number and .expiration_date hybrid properties
    lot_number: Optional[str] = Field(
        default=None,
        description="Lot number from the linked StockLot (SUPPLY items with lots)",
    )
    expiration_date: Optional[date] = Field(
        default=None,
        description="Expiration date from the linked StockLot (SUPPLY items with lots)",
    )

    created_at: datetime
    updated_at: datetime
