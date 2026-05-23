"""
models/repair_request.py
RepairRequest — a maintenance issue filed against a vehicle.

Severity:
    ROUTINE — normal wear, schedule at next opportunity.
    URGENT  — safety-affecting; supervisor is notified immediately and the
               vehicle should be taken out of service until resolved.

Status lifecycle:
    OPEN → IN_PROGRESS → RESOLVED
    Only Supervisor+ can advance or close a request.
    Any authenticated role can file (create) a request.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.vehicle import Vehicle
    from ems_readykit.models.station import Station


class RepairSeverity(str, enum.Enum):
    ROUTINE = "ROUTINE"
    URGENT  = "URGENT"


class RepairStatus(str, enum.Enum):
    OPEN        = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED    = "RESOLVED"


class RepairRequest(TimestampMixin, Base):
    __tablename__ = "repair_requests"

    repair_id:   Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id:  Mapped[int] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=False)
    station_id:  Mapped[int] = mapped_column(ForeignKey("stations.station_id"), nullable=False)

    reported_by: Mapped[str]      = mapped_column(String(100), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    severity:    Mapped[RepairSeverity] = mapped_column(
        String(10), nullable=False, default=RepairSeverity.ROUTINE
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    status: Mapped[RepairStatus] = mapped_column(
        String(20), nullable=False, default=RepairStatus.OPEN
    )

    resolved_by:       Mapped[Optional[str]]      = mapped_column(String(100), nullable=True)
    resolved_at:       Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes:  Mapped[Optional[str]]      = mapped_column(String(500), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="repair_requests")
    station: Mapped["Station"] = relationship("Station", back_populates="repair_requests")

    def __repr__(self) -> str:
        return (
            f"<RepairRequest id={self.repair_id} vehicle={self.vehicle_id} "
            f"severity={self.severity} status={self.status}>"
        )
