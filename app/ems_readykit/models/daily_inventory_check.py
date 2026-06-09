"""
models/daily_inventory_check.py
DailyInventoryCheck — one record per inventory check event.

Phase 7 change: added supervisor acknowledgement (reviewed_by, reviewed_at,
corrective_action) and soft-delete fields (deleted_at, deleted_by,
deletion_reason, force_deleted).

  Acknowledgement:
    A Supervisor can acknowledge a FAIL check and record corrective action.
    Controlled by the station-level allow_check_modification setting (B-M10).

  Soft-delete:
    Supervisor+ can soft-delete a check. It is hidden from all normal queries
    immediately but preserved in the DB for 90 days before automatic hard
    deletion. Administrators can force hard-delete within the window (PII
    spill response) or restore a soft-deleted check.

Phase 5 change: removed UniqueConstraint("vehicle_id", "check_date").
Multiple checks per vehicle per calendar day are supported.

Phase 4 change: added line_items relationship to CheckLineItem.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.check_line_item import CheckLineItem
    from ems_readykit.models.vehicle import Vehicle


class CheckStatus(str, enum.Enum):
    PASS          = "PASS"
    NEEDS_RESTOCK = "NEEDS_RESTOCK"
    FAIL          = "FAIL"


class DailyInventoryCheck(TimestampMixin, Base):
    __tablename__ = "daily_inventory_checks"
    __table_args__ = (
        Index("ix_check_vehicle_date",   "vehicle_id",  "check_date"),
        Index("ix_check_location_date",  "location_id", "check_date"),
        Index("ix_check_station_date",   "station_id",  "check_date"),
    )

    check_id:    Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("vehicles.vehicle_id"),              nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("inventory_locations.location_id"),  nullable=True)
    station_id:  Mapped[int]           = mapped_column(ForeignKey("stations.station_id"),              nullable=False)
    check_date: Mapped[str] = mapped_column(String(10), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp:  Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status:     Mapped[CheckStatus] = mapped_column(
        SAEnum(CheckStatus, native_enum=False), nullable=False, default=CheckStatus.PASS,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Acknowledgement (B-M7) ────────────────────────────────────────────────
    reviewed_by:       Mapped[Optional[str]]      = mapped_column(String(100), nullable=True)
    reviewed_at:       Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    corrective_action: Mapped[Optional[str]]      = mapped_column(String(500), nullable=True)

    # ── Soft delete (B-M9) ────────────────────────────────────────────────────
    deleted_at:      Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by:      Mapped[Optional[str]]      = mapped_column(String(100), nullable=True)
    deletion_reason: Mapped[Optional[str]]      = mapped_column(String(300), nullable=True)
    force_deleted:   Mapped[bool]               = mapped_column(Boolean, nullable=False, default=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="daily_checks")
    line_items: Mapped[List["CheckLineItem"]] = relationship(
        "CheckLineItem", back_populates="check", cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return (
            f"<DailyInventoryCheck id={self.check_id} vehicle_id={self.vehicle_id} "
            f"date={self.check_date} status={self.status}>"
        )
