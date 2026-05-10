"""
routers/audit.py
Audit log query endpoints — read-only.

Endpoints:
  GET /audit          — list audit events (filterable by severity/action/vehicle/station)

Design decisions:
- The audit log is read-only via the API. No POST/PUT/DELETE endpoints exist
  or will ever exist. Writes happen exclusively through the service layer.
- Filtering is provided for the most operationally useful dimensions:
  severity (HIGH events for SIEM review), action (specific event types),
  vehicle_id and station_id (for scoped investigations).
- Results are ordered most-recent-first with a default limit of 100.
  The limit is capped at 1000 to prevent runaway queries on large logs.
  Pagination (offset/cursor) is a Phase 3 enhancement.
- No actor filter is exposed in Phase 2 to avoid inadvertently building a
  surveillance tool before RBAC is implemented. Phase 3 will add this
  with appropriate role restrictions.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db
from ems_readykit.models.audit_event import AuditEvent
from ems_readykit.schemas.audit_event import AuditEventRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=List[AuditEventRead], summary="Query audit events")
def list_audit_events(
    severity: Optional[str] = Query(
        default=None,
        description="Filter by severity level: INFO, WARNING, or HIGH",
    ),
    action: Optional[str] = Query(
        default=None,
        description="Filter by action code (e.g. CS_DISCREPANCY, CHECK_COMPLETED)",
    ),
    vehicle_id: Optional[int] = Query(
        default=None,
        description="Filter events related to a specific vehicle",
    ),
    station_id: Optional[int] = Query(
        default=None,
        description="Filter events related to a specific station",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of events to return (1-1000)",
    ),
    db: Session = Depends(get_db),
) -> List[AuditEvent]:
    """
    Returns audit events matching the supplied filters, ordered most-recent-first.

    Use severity=HIGH to surface controlled substance discrepancies and other
    critical events for SIEM review. All filters are ANDed together.
    """
    query = db.query(AuditEvent)

    if severity is not None:
        query = query.filter(AuditEvent.severity == severity.upper())
    if action is not None:
        query = query.filter(AuditEvent.action == action.upper())
    if vehicle_id is not None:
        query = query.filter(AuditEvent.vehicle_id == vehicle_id)
    if station_id is not None:
        query = query.filter(AuditEvent.station_id == station_id)

    return (
        query.order_by(AuditEvent.timestamp.desc())
        .limit(limit)
        .all()
    )
