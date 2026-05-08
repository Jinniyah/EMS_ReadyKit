"""
models/inventory_location.py
InventoryLocation — abstract container for stock.
Either a VEHICLE location or a STATION_SUPPLY_ROOM.
Every vehicle gets exactly one location; each station has one supply room.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.station import Station
    from ems_readykit.models.vehicle import Vehicle
    from ems_readykit.models.stock_lot import StockLot
    from ems_readykit.models.par_level import ParLevel


class LocationType(str, enum.Enum):
    VEHICLE = "VEHICLE"
    STATION_SUPPLY_ROOM = "STATION_SUPPLY_ROOM"


class InventoryLocation(TimestampMixin, Base):
    __tablename__ = "inventory_locations"

    location_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    location_type: Mapped[LocationType] = mapped_column(
        SAEnum(LocationType, native_enum=False), nullable=False
    )
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.station_id"), nullable=False)

    # Nullable — only set when location_type = VEHICLE
    vehicle_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vehicles.vehicle_id"), nullable=True
    )

    # Human-readable label (e.g. "Unit 401 — ALS", "Station 1 Supply Room")
    label: Mapped[str] = mapped_column(String(150), nullable=False)

    # Relationships
    station: Mapped["Station"] = relationship("Station", back_populates="inventory_locations")
    vehicle: Mapped[Optional["Vehicle"]] = relationship(
        "Vehicle", back_populates="inventory_location"
    )
    stock_lots: Mapped[List["StockLot"]] = relationship(
        "StockLot", back_populates="location", cascade="all, delete-orphan"
    )
    par_levels: Mapped[List["ParLevel"]] = relationship(
        "ParLevel", back_populates="location", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<InventoryLocation id={self.location_id} type={self.location_type} label={self.label!r}>"
