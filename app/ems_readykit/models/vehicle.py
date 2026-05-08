"""
models/vehicle.py
Vehicle — assigned to exactly one station.
Type determines controlled-substance applicability (ALS ambulances only).
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.station import Station
    from ems_readykit.models.inventory_location import InventoryLocation
    from ems_readykit.models.daily_inventory_check import DailyInventoryCheck
    from ems_readykit.models.controlled_substance_check import ControlledSubstanceCheck


class VehicleType(str, enum.Enum):
    ALS = "ALS"   # Advanced Life Support ambulance — controlled substances apply
    BLS = "BLS"   # Basic Life Support ambulance
    QRV = "QRV"   # Quick Response Vehicle / fire truck


class Vehicle(TimestampMixin, Base):
    __tablename__ = "vehicles"

    vehicle_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.station_id"), nullable=False)
    vehicle_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    vehicle_type: Mapped[VehicleType] = mapped_column(
        SAEnum(VehicleType, native_enum=False), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
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

    @property
    def requires_controlled_substance_check(self) -> bool:
        """Only ALS ambulances track controlled substances."""
        return self.vehicle_type == VehicleType.ALS

    def __repr__(self) -> str:
        return f"<Vehicle id={self.vehicle_id} number={self.vehicle_number!r} type={self.vehicle_type}>"
