"""
models/check_line_item.py
CheckLineItem — one verified line of a daily inventory check.

## Check type routing

The item's check_type determines which fields are populated and which
are left NULL. The router validates this at write time.

    SUPPLY items:
        quantity_needed  — par/need (from ParLevel)
        quantity_found   — actual count found
        lot_id           — optional; triggers expiration check
        status           → OK / SHORT / MISSING / EXPIRED

    MEASUREMENT items (PSI readings, temperature, glucose):
        measurement_value  — the numeric reading (e.g. 1800.0 for PSI)
        status             → OK (>= minimum) or LOW (< minimum) or CRITICAL
        quantity_needed and quantity_found are 0 / not used

    FUNCTIONAL items (battery OK, runs and starts, lights & sirens):
        functional_pass  — True (pass) or False (fail)
        status           → OK (True) or FAIL (False)

    DATE_RECORD items (AED last charge, LUCAS last charge):
        date_value       — the date recorded by the crew member
        status           → OK (within recurrence_days) or OVERDUE

    DOCUMENT items (PCR form, billing form, protocol book):
        quantity_found   — 1 (present) or 0 (missing)
        quantity_needed  — always 1
        status           → OK or MISSING

## Status values (extended from Phase 4)

    OK       — item is present/passing/within spec
    SHORT    — SUPPLY: have > 0 but less than needed
    MISSING  — SUPPLY: have 0 / DOCUMENT: not present
    EXPIRED  — SUPPLY: lot expiration date has passed
    LOW      — MEASUREMENT: reading below minimum threshold (e.g. O2 PSI too low)
    FAIL     — FUNCTIONAL: check did not pass (battery not OK, siren not working)
    OVERDUE  — DATE_RECORD: last recorded date exceeds recurrence_days

## Real examples from Ambulance 712

    AED Battery:
        item.check_type = FUNCTIONAL
        functional_pass = True/False
        status = OK / FAIL

    AED Date of Last Charge:
        item.check_type = DATE_RECORD
        date_value = 2026-04-28
        status = OK (within 90 days) / OVERDUE

    AED Pads Adult:
        item.check_type = SUPPLY
        quantity_found = 1, lot_id → expiration date
        status = OK / EXPIRED

    On-Board O2 PSI:
        item.check_type = MEASUREMENT
        measurement_value = 1800.0
        item.measurement_minimum = 500.0
        status = OK / LOW

    On-Board O2 Tank (presence):
        item.check_type = SUPPLY
        quantity_needed = 1, quantity_found = 0 or 1
        status = OK / MISSING
"""

from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, Enum as SAEnum, Float, ForeignKey, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.daily_inventory_check import DailyInventoryCheck
    from ems_readykit.models.compartment import Compartment
    from ems_readykit.models.item import Item
    from ems_readykit.models.stock_lot import StockLot


class LineItemStatus(str, enum.Enum):
    # SUPPLY statuses
    OK      = "OK"       # quantity_found >= quantity_needed, not expired
    SHORT   = "SHORT"    # 0 < quantity_found < quantity_needed
    MISSING = "MISSING"  # quantity_found == 0 / document not present
    EXPIRED = "EXPIRED"  # lot expiration date has passed

    # MEASUREMENT statuses
    LOW      = "LOW"      # reading below item.measurement_minimum
    CRITICAL = "CRITICAL" # reading below critical floor (future use)

    # FUNCTIONAL status
    FAIL = "FAIL"         # functional check did not pass

    # DATE_RECORD status
    OVERDUE = "OVERDUE"   # last charge/service date exceeds recurrence_days


class CheckLineItem(TimestampMixin, Base):
    __tablename__ = "check_line_items"

    line_item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    check_id: Mapped[int] = mapped_column(
        ForeignKey("daily_inventory_checks.check_id"), nullable=False
    )
    compartment_id: Mapped[int] = mapped_column(
        ForeignKey("compartments.compartment_id"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.item_id"), nullable=False
    )

    # ── SUPPLY fields ─────────────────────────────────────────────────────────

    # "Need" column — expected quantity (par). 0 for non-SUPPLY items.
    quantity_needed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # "Have" column — actual count found. 0 for non-SUPPLY items.
    quantity_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Optional lot link — triggers expiration check when provided.
    # Required for medication items; optional for dated consumables.
    lot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("stock_lots.lot_id"), nullable=True
    )

    # ── MEASUREMENT fields ────────────────────────────────────────────────────

    # Numeric reading recorded by crew member.
    # Examples: O2 PSI = 1800.0, temperature = 98.6, glucose = 112.0
    # NULL for all non-MEASUREMENT items.
    measurement_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── FUNCTIONAL fields ─────────────────────────────────────────────────────

    # True = passed, False = failed, NULL = not applicable.
    # Examples: Battery OK = True, Lights & Sirens working = True,
    #           Runs and Starts = True, Communication Medcom Compliant = True
    functional_pass: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # ── DATE_RECORD fields ────────────────────────────────────────────────────

    # Date recorded by crew member for maintenance events.
    # Examples: AED last charge date, LUCAS device last charge date.
    # Status compared against item.recurrence_days to determine OVERDUE.
    date_value: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ── Common fields ─────────────────────────────────────────────────────────

    # Computed server-side from item.check_type + the type-specific fields.
    # Never supplied by the client.
    status: Mapped[LineItemStatus] = mapped_column(
        SAEnum(LineItemStatus, native_enum=False), nullable=False
    )

    # Optional crew notes — required when status is FAIL, EXPIRED, or OVERDUE
    # to document what action was taken or why.
    # e.g. "O2 PSI at 420 — tank swapped from supply room, now at 1800"
    # e.g. "AED battery replaced, date of last charge updated to today"
    notes: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    check: Mapped["DailyInventoryCheck"] = relationship(
        "DailyInventoryCheck", back_populates="line_items"
    )
    compartment: Mapped["Compartment"] = relationship(
        "Compartment", back_populates="check_line_items"
    )
    item: Mapped["Item"] = relationship(
        "Item", back_populates="check_line_items"
    )
    lot: Mapped[Optional["StockLot"]] = relationship(
        "StockLot", back_populates="check_line_items", lazy="selectin"
    )

    # ── Hybrid properties (SUPPLY items) ──────────────────────────────────────

    @hybrid_property
    def lot_number(self) -> Optional[str]:
        """Lot number from the linked StockLot. None for non-SUPPLY items."""
        return self.lot.lot_number if self.lot is not None else None

    @hybrid_property
    def expiration_date(self) -> Optional[date]:
        """Expiration date from the linked StockLot. None if no lot linked."""
        return self.lot.expiration_date if self.lot is not None else None

    def __repr__(self) -> str:
        return (
            f"<CheckLineItem id={self.line_item_id} check_id={self.check_id} "
            f"item_id={self.item_id} status={self.status}>"
        )
