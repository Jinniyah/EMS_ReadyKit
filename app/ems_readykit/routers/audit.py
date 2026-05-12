"""
routers/audit.py
Audit log query endpoints — read-only.

Endpoints:
  GET /audit          — list audit events (Supervisor, Administrator)
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ems_readykit.core.auth import ROLE_ADMINISTRATOR, ROLE_SUPERVISOR
from ems_readykit.core.database import get_db
from ems_readykit.models.audit_event import AuditEvent
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.audit_event import AuditEventRead

router = APIRouter(prefix="/audit", tags=["audit"])

_SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)


@router.get(
    "",
    response_model=List[AuditEventRead],
    summary="Query audit events",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
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
    Requires Supervisor or Administrator role.
    Use severity=HIGH to surface controlled substance discrepancies for SIEM review.
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
