"""
models/compartment.py
Compartment — a named physical storage area within a vehicle or station.

Each Compartment belongs to one InventoryLocation (the vehicle or supply room).
Items and par levels are tracked at the compartment level, matching how
EMS crews actually perform inventory: compartment by compartment.

Examples from Jan-Care inventory sheets:
  - Compartment #1, Compartment #2 ... Compartment #13
  - First Out Bag, Peds Bag, Drug Bag, Narcotic Lock Bag
  - BLS Only Epi Pens, Emergency Resp. Box, ALS Trucks Only

Design decision: Compartment is a separate model rather than a field on
InventoryLocation so that:
  1. Par levels and check line items can be scoped to a compartment.
  2. The same item can appear in multiple compartments with different par levels
     (e.g. KY Jelly in Compartment #2 AND First Out Bag).
  3. Compartment templates can be defined once and applied to multiple vehicles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.inventory_location import InventoryLocation
    from ems_readykit.models.check_line_item import CheckLineItem
    from ems_readykit.models.par_level import ParLevel


class Compartment(TimestampMixin, Base):
    __tablename__ = "compartments"
    __table_args__ = (
        # Each location can only have one compartment with a given name
        UniqueConstraint("location_id", "name", name="uq_compartment_location_name"),
    )

    compartment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    location_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_locations.location_id"), nullable=False
    )

    # Human-readable name matching the physical label on the truck
    # e.g. "Compartment #1", "Drug Bag", "Narcotic Lock Bag", "First Out Bag"
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Display order for UI — matches physical left-to-right / top-to-bottom layout
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ALS-only compartments (Drug Bag, Narcotic Lock Bag) are hidden on BLS trucks
    als_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    location: Mapped["InventoryLocation"] = relationship(
        "InventoryLocation", back_populates="compartments"
    )
    par_levels: Mapped[List["ParLevel"]] = relationship(
        "ParLevel", back_populates="compartment", cascade="all, delete-orphan"
    )
    check_line_items: Mapped[List["CheckLineItem"]] = relationship(
        "CheckLineItem", back_populates="compartment"
    )

    def __repr__(self) -> str:
        return (
            f"<Compartment id={self.compartment_id} "
            f"location_id={self.location_id} name={self.name!r}>"
        )
