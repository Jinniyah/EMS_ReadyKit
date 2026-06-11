"""
models/par_level.py
ParLevel — minimum and maximum stock quantities per item per compartment.

Uniqueness: one par level per item per compartment (uq_par_item_compartment).
The legacy uq_par_item_location constraint was dropped in migration 0004 —
it incorrectly prevented the same item from appearing in multiple compartments
on the same vehicle, which is valid and expected (e.g. Stethoscope in PC3
and PC18 on the same truck).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.compartment import Compartment
    from ems_readykit.models.inventory_location import InventoryLocation
    from ems_readykit.models.item import Item


class ParLevel(TimestampMixin, Base):
    __tablename__ = "par_levels"
    __table_args__ = (
        # One par level per item per compartment — the correct constraint.
        # uq_par_item_location (item_id, location_id) was dropped in 0004.
        UniqueConstraint(
            "item_id",
            "compartment_id",
            name="uq_par_item_compartment",
        ),
    )

    par_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_locations.location_id"), nullable=False
    )
    compartment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("compartments.compartment_id"), nullable=True
    )
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    max_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True, server_default=sa.true()
    )

    # Priority items — supervisor marks per vehicle. Pulled above compartment list in check wizard.
    priority_check: Mapped[Optional[bool]] = mapped_column(
        sa.Boolean, nullable=True, default=False
    )
    # Plain-English question shown to responder in place of item name (max 150 chars).
    priority_question: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    # Damaged flag — responder marks item as damaged/unavailable at this compartment.
    is_damaged: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )

    # Soft-deactivation tracking — recorded when a par level is removed.
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deactivation_reason: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

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
