"""
models/station.py
Station — the top-level organizational unit.
One station manages multiple vehicles and a supply room.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.inventory_location import InventoryLocation
    from ems_readykit.models.repair_request import RepairRequest
    from ems_readykit.models.station_member import StationMember
    from ems_readykit.models.vehicle import Vehicle


class Station(TimestampMixin, Base):
    __tablename__ = "stations"

    station_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ADMIN-B15: short radio/dispatch identifier. Optional.
    call_sign: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # B-M11: station color for header / buttons / station card bar.
    # Null = fall back to --color-brand (#1a3a5c) in the frontend.
    primary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)

    # B-M10: whether submitted checks may be modified. Default True.
    # Prerequisite for CH-F6 (acknowledgement / corrective note).
    allow_check_modification: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    vehicles: Mapped[List["Vehicle"]] = relationship(
        "Vehicle", back_populates="station", cascade="all, delete-orphan"
    )
    inventory_locations: Mapped[List["InventoryLocation"]] = relationship(
        "InventoryLocation", back_populates="station"
    )
    repair_requests: Mapped[List["RepairRequest"]] = relationship(
        "RepairRequest", back_populates="station"
    )
    members: Mapped[List["StationMember"]] = relationship(
        "StationMember", back_populates="station", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Station id={self.station_id} name={self.name!r}>"
