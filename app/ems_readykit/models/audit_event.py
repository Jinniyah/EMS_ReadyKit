"""
models/audit_event.py
AuditEvent — immutable record of every material action in the system.
Written at the service layer and also emitted to the structured logger
so events flow through to Log Analytics / Security Onion.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ems_readykit.core.database import Base


class AuditEvent(Base):
    """
    Intentionally has no updated_at — audit records are write-once.
    The created_at column is the authoritative event timestamp.
    """

    __tablename__ = "audit_events"

    event_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Who performed the action
    actor: Mapped[str] = mapped_column(String(100), nullable=False)

    # What they did (e.g. "INVENTORY_CHANGE", "CS_DISCREPANCY", "CHECK_COMPLETED")
    action: Mapped[str] = mapped_column(String(100), nullable=False)

    # What kind of entity was affected
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # The ID of the affected entity (stored as string for flexibility)
    entity_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Optional station/vehicle context for SIEM correlation
    station_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("stations.station_id"), nullable=True
    )
    vehicle_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vehicles.vehicle_id"), nullable=True
    )

    # JSON blob for action-specific detail (e.g. before/after quantities)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Severity: INFO | WARNING | HIGH
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="INFO")

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<AuditEvent id={self.event_id} action={self.action!r} "
            f"actor={self.actor!r} severity={self.severity}>"
        )
