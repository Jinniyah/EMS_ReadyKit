"""
models/stock_transfer.py
StockTransfer — records a stock movement between two inventory locations.

Quantity is always positive; direction is encoded by from/to location.
Common paths:
  STATION_SUPPLY_ROOM → VEHICLE  (supervisor restocks truck)
  External receipt    → STATION_SUPPLY_ROOM  (supervisor receives new shipment;
                        no from_location_id — null means external receipt)
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.inventory_location import InventoryLocation
    from ems_readykit.models.item import Item


class StockTransfer(TimestampMixin, Base):
    __tablename__ = "stock_transfers"
    __table_args__ = (
        Index("ix_stock_transfer_from_loc", "from_location_id"),
        Index("ix_stock_transfer_to_loc", "to_location_id"),
        Index("ix_stock_transfer_item", "item_id"),
    )

    transfer_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # NULL = external receipt (items came from outside the system)
    from_location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("inventory_locations.location_id"), nullable=True
    )
    to_location_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_locations.location_id"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # JWT-bound server-side — never trust a client-supplied identity
    transferred_by: Mapped[str] = mapped_column(String(255), nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Snapshot of lot metadata from the source lot at transfer time
    # Preserved for audit/history display even if the source lot is later modified
    lot_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    lot_expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    from_location: Mapped[Optional["InventoryLocation"]] = relationship(
        "InventoryLocation",
        foreign_keys=[from_location_id],
        primaryjoin="StockTransfer.from_location_id == InventoryLocation.location_id",
    )
    to_location: Mapped["InventoryLocation"] = relationship(
        "InventoryLocation",
        foreign_keys=[to_location_id],
        primaryjoin="StockTransfer.to_location_id == InventoryLocation.location_id",
    )
    item: Mapped["Item"] = relationship(
        "Item",
        foreign_keys=[item_id],
    )

    def __repr__(self) -> str:
        return (
            f"<StockTransfer id={self.transfer_id} item_id={self.item_id} "
            f"qty={self.quantity} {self.from_location_id}→{self.to_location_id}>"
        )
