"""
models/par_level.py
ParLevel — minimum and maximum stock quantities per item per location.
When quantity on hand falls below min_quantity, a low-stock condition is flagged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.item import Item
    from ems_readykit.models.inventory_location import InventoryLocation


class ParLevel(TimestampMixin, Base):
    __tablename__ = "par_levels"
    __table_args__ = (
        # Each item/location pair has exactly one par level definition
        UniqueConstraint("item_id", "location_id", name="uq_par_item_location"),
    )

    par_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_locations.location_id"), nullable=False
    )
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    max_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="par_levels")
    location: Mapped["InventoryLocation"] = relationship(
        "InventoryLocation", back_populates="par_levels"
    )

    def __repr__(self) -> str:
        return (
            f"<ParLevel id={self.par_id} item_id={self.item_id} "
            f"location_id={self.location_id} min={self.min_quantity} max={self.max_quantity}>"
        )
