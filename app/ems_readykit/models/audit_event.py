"""
models/audit_event.py
AuditEvent — immutable record of every material action in the system.
Written at the service layer and also emitted to the structured logger
so events flow through to Log Analytics / Security Onion.

metadata_json contract:
    This column uses SQLAlchemy's JSON type, which handles serialization
    automatically. Callers MUST pass a Python dict (or None) — never a
    pre-serialized JSON string. Passing a string will cause double-encoding:
        CORRECT:   metadata_json={"before": 5, "after": 3}
        INCORRECT: metadata_json=json.dumps({"before": 5, "after": 3})

    On SQLite the JSON type stores as TEXT internally; on Azure SQL it stores
    as NVARCHAR(MAX). The wire format is identical to the previous Text column,
    so no data migration is required.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String
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

    # Structured detail for the event (e.g. {"before": 5, "after": 3, "item_id": 12}).
    # Pass a dict or None — SQLAlchemy handles serialization. See module docstring.
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Severity: INFO | WARNING | HIGH
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="INFO")

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<AuditEvent id={self.event_id} action={self.action!r} "
            f"actor={self.actor!r} severity={self.severity}>"
        )
