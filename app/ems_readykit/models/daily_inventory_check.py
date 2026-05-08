"""
models/daily_inventory_check.py
DailyInventoryCheck — first-class entity requiring one completion
per active vehicle per calendar day.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.vehicle import Vehicle


class CheckStatus(str, enum.Enum):
    PASS = "PASS"
    NEEDS_RESTOCK = "NEEDS_RESTOCK"
    FAIL = "FAIL"


class DailyInventoryCheck(TimestampMixin, Base):
    __tablename__ = "daily_inventory_checks"
    __table_args__ = (
        # Enforce one check per vehicle per calendar day at the DB level
        UniqueConstraint("vehicle_id", "check_date", name="uq_check_vehicle_date"),
    )

    check_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=False)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.station_id"), nullable=False)

    # Date string (YYYY-MM-DD) stored separately to simplify daily uniqueness enforcement
    check_date: Mapped[str] = mapped_column(String(10), nullable=False)

    performed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[CheckStatus] = mapped_column(
        SAEnum(CheckStatus, native_enum=False), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="daily_checks")

    def __repr__(self) -> str:
        return (
            f"<DailyInventoryCheck id={self.check_id} vehicle_id={self.vehicle_id} "
            f"date={self.check_date} status={self.status}>"
        )
