"""
models/controlled_substance_check.py
ControlledSubstanceCheck — double-signature workflow for ALS vehicles.
Any discrepancy triggers a high-severity audit event.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.vehicle import Vehicle


class ControlledSubstanceCheck(TimestampMixin, Base):
    __tablename__ = "controlled_substance_checks"

    cs_check_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=False)

    primary_signer: Mapped[str] = mapped_column(String(100), nullable=False)
    secondary_signer: Mapped[str] = mapped_column(String(100), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # True if any count discrepancy was noted
    discrepancy_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="cs_checks")

    def __repr__(self) -> str:
        return (
            f"<ControlledSubstanceCheck id={self.cs_check_id} vehicle_id={self.vehicle_id} "
            f"discrepancy={self.discrepancy_flag}>"
        )
