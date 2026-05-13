"""
models/check_line_item.py
CheckLineItem — one line of a daily inventory check.

Captures the "Need" (par) and "Have" (found) quantities for a single item
in a single compartment during a daily check, matching the paper form:

  Need | Have | Compartment #1
  -----+------+----------------------------
    2  |  2   | Personal Protection Kits
    1  |  0   | BioHaz Spill Clean-up Kit   ← SHORT
    2  |  2   | Epi 1:1000 1mg (LOT A, exp 2026-06-01)  ← EXPIRED

Each CheckLineItem belongs to one DailyInventoryCheck (the header) and
one Compartment, and references one Item.

lot_id is optional — links to the specific StockLot inspected during
the check. When provided, the router validates the lot belongs to the
correct item and checks its expiration date.

Status is computed automatically:
  OK      — quantity_found >= quantity_needed and lot not expired
  SHORT   — 0 < quantity_found < quantity_needed and lot not expired
  MISSING — quantity_found == 0 and quantity_needed > 0
  EXPIRED — lot_id provided and lot expiration_date <= today
             (expired items cannot be used regardless of quantity found)
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String
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
    OK      = "OK"       # quantity_found >= quantity_needed, not expired
    SHORT   = "SHORT"    # 0 < quantity_found < quantity_needed, not expired
    MISSING = "MISSING"  # quantity_found == 0 and quantity_needed > 0
    EXPIRED = "EXPIRED"  # lot is expired — unusable regardless of quantity


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

    # Optional — the specific stock lot inspected during this check.
    # When provided, the router validates expiration and sets status to
    # EXPIRED if the lot has passed its expiration date.
    lot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("stock_lots.lot_id"), nullable=True
    )

    # "Need" column on the paper form — expected quantity (par)
    quantity_needed: Mapped[int] = mapped_column(Integer, nullable=False)

    # "Have" column on the paper form — actual count found
    quantity_found: Mapped[int] = mapped_column(Integer, nullable=False)

    # Computed at write time
    status: Mapped[LineItemStatus] = mapped_column(
        SAEnum(LineItemStatus, native_enum=False), nullable=False
    )

    notes: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Relationships
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

    def __repr__(self) -> str:
        return (
            f"<CheckLineItem id={self.line_item_id} check_id={self.check_id} "
            f"item_id={self.item_id} lot_id={self.lot_id} "
            f"need={self.quantity_needed} have={self.quantity_found} status={self.status}>"
        )

    @hybrid_property
    def lot_number(self) -> Optional[str]:
        """Lot number from the linked StockLot, for serialization convenience."""
        return self.lot.lot_number if self.lot is not None else None

    @hybrid_property
    def expiration_date(self):
        """Expiration date from the linked StockLot, for serialization convenience."""
        return self.lot.expiration_date if self.lot is not None else None
