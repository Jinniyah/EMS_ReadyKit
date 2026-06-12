"""
models/usage_event.py
UsageEvent  -- one record per after-call usage submission.
UsageEventItem -- one row per item used within an event.

Usage events are an audit trail of what was consumed from a vehicle or
portable location during a call. They do NOT decrement station supply room
stock -- that happens during check wizard reconcile (SR-B4 in checks.py).

The logged quantities feed back into get_last_readings so the check wizard
pre-fills the correct (post-call) on-hand quantities, automatically flagging
items as short without requiring a full discovery check.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.inventory_location import InventoryLocation
    from ems_readykit.models.item import Item
    from ems_readykit.models.vehicle import Vehicle


class UsageEvent(TimestampMixin, Base):
    __tablename__ = "usage_events"

    event_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.station_id"), nullable=False
    )
    vehicle_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vehicles.vehicle_id"), nullable=True
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("inventory_locations.location_id"), nullable=True
    )
    performed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    vehicle: Mapped[Optional["Vehicle"]] = relationship("Vehicle", lazy="selectin")
    location: Mapped[Optional["InventoryLocation"]] = relationship(
        "InventoryLocation", lazy="selectin"
    )
    items: Mapped[List["UsageEventItem"]] = relationship(
        "UsageEventItem",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<UsageEvent id={self.event_id} station={self.station_id} "
            f"by={self.performed_by}>"
        )


class UsageEventItem(TimestampMixin, Base):
    __tablename__ = "usage_event_items"

    usage_item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("usage_events.event_id"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"), nullable=False)
    quantity_used: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    event: Mapped["UsageEvent"] = relationship("UsageEvent", back_populates="items")
    item: Mapped["Item"] = relationship("Item", lazy="selectin")
