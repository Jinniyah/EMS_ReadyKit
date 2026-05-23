"""
models/vehicle.py
Vehicle — assigned to exactly one station.
Type determines controlled-substance applicability (ALS ambulances only).
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.station import Station
    from ems_readykit.models.inventory_location import InventoryLocation
    from ems_readykit.models.daily_inventory_check import DailyInventoryCheck
    from ems_readykit.models.controlled_substance_check import ControlledSubstanceCheck
    from ems_readykit.models.repair_request import RepairRequest


class VehicleType(str, enum.Enum):
    ALS = "ALS"   # Advanced Life Support ambulance — controlled substances apply
    BLS = "BLS"   # Basic Life Support ambulance
    QRV = "QRV"   # Quick Response Vehicle / fire truck


class Vehicle(TimestampMixin, Base):
    __tablename__ = "vehicles"

    vehicle_id:     Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    station_id:     Mapped[int] = mapped_column(ForeignKey("stations.station_id"), nullable=False)
    vehicle_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    vehicle_type:   Mapped[VehicleType] = mapped_column(
        SAEnum(VehicleType, native_enum=False), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Set when active is flipped to False — explains why and when.
    inactive_reason: Mapped[Optional[str]]      = mapped_column(String(200), nullable=True)
    inactive_since:  Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    station: Mapped["Station"] = relationship("Station", back_populates="vehicles")
    inventory_location: Mapped["InventoryLocation"] = relationship(
        "InventoryLocation",
        back_populates="vehicle",
        uselist=False,
    )
    daily_checks: Mapped[List["DailyInventoryCheck"]] = relationship(
        "DailyInventoryCheck", back_populates="vehicle"
    )
    cs_checks: Mapped[List["ControlledSubstanceCheck"]] = relationship(
        "ControlledSubstanceCheck", back_populates="vehicle"
    )
    repair_requests: Mapped[List["RepairRequest"]] = relationship(
        "RepairRequest", back_populates="vehicle", cascade="all, delete-orphan"
    )

    @property
    def requires_controlled_substance_check(self) -> bool:
        """Only ALS ambulances track controlled substances."""
        return self.vehicle_type == VehicleType.ALS

    def __repr__(self) -> str:
        return f"<Vehicle id={self.vehicle_id} number={self.vehicle_number!r} type={self.vehicle_type}>"
