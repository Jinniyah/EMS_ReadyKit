"""
models/stock_lot.py
StockLot — a quantity of a specific item in a specific location,
with optional lot number and expiration date.
This is the primary unit of expiration tracking and recall readiness.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.item import Item
    from ems_readykit.models.inventory_location import InventoryLocation
    from ems_readykit.models.check_line_item import CheckLineItem


class StockLot(TimestampMixin, Base):
    __tablename__ = "stock_lots"

    lot_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_locations.location_id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lot_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="stock_lots")
    location: Mapped["InventoryLocation"] = relationship(
        "InventoryLocation", back_populates="stock_lots"
    )
    check_line_items: Mapped[List["CheckLineItem"]] = relationship(
        "CheckLineItem", back_populates="lot"
    )

    @property
    def is_expired(self) -> bool:
        """True if the lot has an expiration date that has passed."""
        if self.expiration_date is None:
            return False
        return self.expiration_date < date.today()

    def __repr__(self) -> str:
        return (
            f"<StockLot id={self.lot_id} item_id={self.item_id} "
            f"qty={self.quantity} exp={self.expiration_date}>"
        )
