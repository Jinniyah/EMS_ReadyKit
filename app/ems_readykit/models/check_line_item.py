"""
models/check_line_item.py
CheckLineItem — one verified line of a daily inventory check.
(docstring unchanged for brevity)
"""

from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.compartment import Compartment
    from ems_readykit.models.daily_inventory_check import DailyInventoryCheck
    from ems_readykit.models.item import Item
    from ems_readykit.models.stock_lot import StockLot


class LineItemStatus(str, enum.Enum):
    OK = "OK"
    SHORT = "SHORT"
    MISSING = "MISSING"
    EXPIRED = "EXPIRED"
    LOW = "LOW"
    CRITICAL = "CRITICAL"
    FAIL = "FAIL"
    OVERDUE = "OVERDUE"


class CheckLineItem(TimestampMixin, Base):
    __tablename__ = "check_line_items"

    line_item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    check_id: Mapped[int] = mapped_column(
        ForeignKey("daily_inventory_checks.check_id"), nullable=False
    )
    compartment_id: Mapped[int] = mapped_column(
        ForeignKey("compartments.compartment_id"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"), nullable=False)

    quantity_needed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("stock_lots.lot_id"), nullable=True
    )
    measurement_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    functional_pass: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    date_value: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    status: Mapped[LineItemStatus] = mapped_column(
        SAEnum(LineItemStatus, native_enum=False), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    check: Mapped["DailyInventoryCheck"] = relationship(
        "DailyInventoryCheck", back_populates="line_items"
    )
    compartment: Mapped["Compartment"] = relationship(
        "Compartment", back_populates="check_line_items"
    )
    item: Mapped["Item"] = relationship(
        "Item", back_populates="check_line_items", lazy="selectin"
    )
    lot: Mapped[Optional["StockLot"]] = relationship(
        "StockLot", back_populates="check_line_items", lazy="selectin"
    )

    # ── Hybrid properties ─────────────────────────────────────────────────────

    @hybrid_property
    def lot_number(self) -> Optional[str]:
        return self.lot.lot_number if self.lot is not None else None

    @hybrid_property
    def expiration_date(self) -> Optional[date]:
        return self.lot.expiration_date if self.lot is not None else None

    @hybrid_property
    def item_name(self) -> Optional[str]:
        """Human-readable item name from the related Item record."""
        return self.item.name if self.item is not None else None

    @hybrid_property
    def check_type(self) -> Optional[str]:
        """Item check type (SUPPLY/MEASUREMENT/FUNCTIONAL/DATE_RECORD/DOCUMENT)."""
        if self.item is None:
            return None
        ct = self.item.check_type
        return ct.value if hasattr(ct, "value") else str(ct)

    def __repr__(self) -> str:
        return (
            f"<CheckLineItem id={self.line_item_id} check_id={self.check_id} "
            f"item_id={self.item_id} status={self.status}>"
        )
