"""
models/daily_inventory_check.py
DailyInventoryCheck — one record per inventory check event.

Phase 5 change: removed the UniqueConstraint("vehicle_id", "check_date")
that enforced one check per vehicle per calendar day. Multiple checks per
day are now supported to cover:
  - Post-call restocking checks (supplies used during a call)
  - Shift-start and shift-end checks (legal requirement at some stations)
  - Any other station-specific check cadence

The (vehicle_id, check_date) unique constraint is replaced with a plain
non-unique index on (vehicle_id, check_date) for query performance. The
timestamp column remains the natural unique discriminator for a check event.

Phase 4 change: added line_items relationship to CheckLineItem.
The overall status is auto-computed from line items in the router rather
than submitted manually. PASS = all OK, NEEDS_RESTOCK = any SHORT,
FAIL = any MISSING/EXPIRED.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.vehicle import Vehicle
    from ems_readykit.models.check_line_item import CheckLineItem


class CheckStatus(str, enum.Enum):
    PASS          = "PASS"
    NEEDS_RESTOCK = "NEEDS_RESTOCK"
    FAIL          = "FAIL"


class DailyInventoryCheck(TimestampMixin, Base):
    __tablename__ = "daily_inventory_checks"
    __table_args__ = (
        # Non-unique index on (vehicle_id, check_date) for query performance.
        # Uniqueness is no longer enforced — multiple checks per vehicle per
        # calendar day are intentionally allowed (post-call restocks, shift
        # start/end checks, etc.). The timestamp column is the natural
        # discriminator for a specific check event within a day.
        Index("ix_check_vehicle_date", "vehicle_id", "check_date"),
    )

    check_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=False)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.station_id"), nullable=False)

    # Calendar date (YYYY-MM-DD) — used for compliance reporting and grouping.
    # Multiple checks may share the same check_date; timestamp distinguishes them.
    check_date: Mapped[str] = mapped_column(String(10), nullable=False)

    performed_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timestamp of when the check was started (set at draft creation, not
    # at submission time). Natural unique discriminator within a day.
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Auto-computed from line items: PASS / NEEDS_RESTOCK / FAIL
    # If no line items submitted, defaults to PASS (header-only check)
    status: Mapped[CheckStatus] = mapped_column(
        SAEnum(CheckStatus, native_enum=False), nullable=False,
        default=CheckStatus.PASS,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="daily_checks")
    line_items: Mapped[List["CheckLineItem"]] = relationship(
        "CheckLineItem", back_populates="check", cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<DailyInventoryCheck id={self.check_id} vehicle_id={self.vehicle_id} "
            f"date={self.check_date} status={self.status}>"
        )
