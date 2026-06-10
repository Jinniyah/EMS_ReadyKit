"""
models/inventory_location.py
InventoryLocation — abstract container for stock and equipment.

## Location types — validated against Ambulance 712 inventory forms

    VEHICLE
        The interior/exterior of an ambulance or response unit.
        One per vehicle, created automatically when the vehicle is created.
        Examples: Unit 712 (ALS Ambulance), Unit 710 (ALS Ambulance)

    STATION_SUPPLY_ROOM
        The station's restocking inventory. When a vehicle item is SHORT
        or MISSING during a daily check, the crew restocks from here.
        One per station.

    JUMP_BAG
        A portable equipment bag that travels with the crew to patient scenes.
        May be shared across multiple vehicles (710/712 share the same Jump Bag
        checklist). Modeled as a standalone location not tied to one vehicle.
        Has its own compartment structure (Left Pocket, Back Pocket, etc.).

    EQUIPMENT
        A specific piece of equipment with its own inventory/maintenance record.
        Used when a device is complex enough to warrant its own location record.
        Future use: AED unit, LUCAS device, LifePak monitor.
        For now, AED and LUCAS items are modeled as CheckLineItems within
        the PC 8 compartment of their vehicle.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.compartment import Compartment
    from ems_readykit.models.par_level import ParLevel
    from ems_readykit.models.station import Station
    from ems_readykit.models.stock_lot import StockLot
    from ems_readykit.models.vehicle import Vehicle


class LocationType(str, enum.Enum):
    VEHICLE = "VEHICLE"
    STATION_SUPPLY_ROOM = "STATION_SUPPLY_ROOM"
    JUMP_BAG = "JUMP_BAG"
    EQUIPMENT = "EQUIPMENT"


class InventoryLocation(TimestampMixin, Base):
    __tablename__ = "inventory_locations"

    location_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    location_type: Mapped[LocationType] = mapped_column(
        SAEnum(LocationType, native_enum=False), nullable=False
    )

    station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.station_id"), nullable=False
    )

    # Nullable — set only for VEHICLE locations.
    # JUMP_BAG and EQUIPMENT locations are not tied to a single vehicle.
    vehicle_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vehicles.vehicle_id"), nullable=True
    )

    # Human-readable label shown in the UI.
    # Examples:
    #   "Unit 712 — ALS Ambulance"
    #   "Station 1 Supply Room"
    #   "Jump Bag (Units 710/712)"
    label: Mapped[str] = mapped_column(String(150), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────

    station: Mapped["Station"] = relationship(
        "Station", back_populates="inventory_locations"
    )
    vehicle: Mapped[Optional["Vehicle"]] = relationship(
        "Vehicle", back_populates="inventory_location"
    )
    stock_lots: Mapped[List["StockLot"]] = relationship(
        "StockLot", back_populates="location", cascade="all, delete-orphan"
    )
    par_levels: Mapped[List["ParLevel"]] = relationship(
        "ParLevel", back_populates="location", cascade="all, delete-orphan"
    )
    compartments: Mapped[List["Compartment"]] = relationship(
        "Compartment",
        back_populates="location",
        cascade="all, delete-orphan",
        order_by="Compartment.sort_order",
    )

    def __repr__(self) -> str:
        return (
            f"<InventoryLocation id={self.location_id} "
            f"type={self.location_type} label={self.label!r}>"
        )
