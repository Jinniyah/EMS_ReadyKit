"""
models/par_level.py
ParLevel — minimum and maximum stock quantities per item per location/compartment.

When quantity on hand falls below min_quantity, a low-stock condition is flagged.

Phase 4 change: par levels can now be scoped to a specific compartment within
a location, matching the paper form where each compartment has its own Need qty.
compartment_id is nullable for backward compatibility — existing par levels
without a compartment remain valid (vehicle-level par).

Uniqueness: one par level per item per compartment (if compartment set),
or one per item per location (if no compartment).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.item import Item
    from ems_readykit.models.inventory_location import InventoryLocation
    from ems_readykit.models.compartment import Compartment


class ParLevel(TimestampMixin, Base):
    __tablename__ = "par_levels"
    __table_args__ = (
        # Compartment-scoped: one par per item per compartment
        UniqueConstraint(
            "item_id", "compartment_id",
            name="uq_par_item_compartment",
        ),
        # Location-scoped (legacy): one par per item per location when no compartment
        UniqueConstraint(
            "item_id", "location_id",
            name="uq_par_item_location",
        ),
    )

    par_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_locations.location_id"), nullable=False
    )
    # Nullable — set when par is compartment-specific; null for vehicle-level par
    compartment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("compartments.compartment_id"), nullable=True
    )
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    max_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="par_levels")
    location: Mapped["InventoryLocation"] = relationship(
        "InventoryLocation", back_populates="par_levels"
    )
    compartment: Mapped[Optional["Compartment"]] = relationship(
        "Compartment", back_populates="par_levels"
    )

    def __repr__(self) -> str:
        return (
            f"<ParLevel id={self.par_id} item_id={self.item_id} "
            f"location_id={self.location_id} compartment_id={self.compartment_id} "
            f"min={self.min_quantity} max={self.max_quantity}>"
        )
