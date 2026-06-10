"""
schemas/audit_event.py
Pydantic schema for AuditEvent response serialization.

Design decisions:
- AuditEventRead ONLY — there is no AuditEventCreate schema exposed via the API.
  Audit events are written exclusively by the service layer to guarantee
  integrity. Allowing API callers to create audit events directly would
  undermine the audit trail.
- metadata_json is typed as Optional[dict] matching the JSON column on the model.
  Callers receive a parsed dict, not a raw JSON string.
- severity is a string field matching the model ("INFO", "WARNING", "HIGH").
  An enum could be used here but a string is simpler and future-proof if
  new severity levels are added.
- AuditEvent has no TimestampMixin — it uses only 'timestamp' (the event time).
  There is no created_at/updated_at because audit records are write-once.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditEventRead(BaseModel):
    """
    Response model for audit log endpoints.
    Read-only — audit events are written by the service layer only.
    """

    model_config = ConfigDict(from_attributes=True)

    event_id: int
    actor: str = Field(description="Identity of who performed the action")
    action: str = Field(
        description="Action code (e.g. INVENTORY_CHANGE, CS_DISCREPANCY, CHECK_COMPLETED)"
    )
    entity_type: str = Field(
        description="Type of entity affected (e.g. StockLot, Vehicle)"
    )
    entity_id: Optional[str] = Field(
        default=None, description="ID of the affected entity"
    )
    station_id: Optional[int] = Field(
        default=None, description="Station context for SIEM correlation"
    )
    vehicle_id: Optional[int] = Field(
        default=None, description="Vehicle context for SIEM correlation"
    )
    metadata_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured event detail (e.g. before/after quantities, lot numbers)",
    )
    severity: str = Field(description="INFO | WARNING | HIGH")
    timestamp: datetime = Field(description="UTC timestamp of the event")
