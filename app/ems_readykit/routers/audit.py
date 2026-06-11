"""
routers/audit.py
Audit log query endpoints — read-only.

Refactor (Session B):
- Role constants imported from deps (REF-3)
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db
from ems_readykit.models.audit_event import AuditEvent
from ems_readykit.routers.deps import SUPERVISOR_PLUS, require_role
from ems_readykit.schemas.audit_event import AuditEventRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "",
    response_model=List[AuditEventRead],
    summary="Query audit events",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def list_audit_events(
    severity: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    vehicle_id: Optional[int] = Query(default=None),
    station_id: Optional[int] = Query(default=None),
    from_date: Optional[date] = Query(
        default=None,
        description="Include events on or after this date (YYYY-MM-DD, UTC)",
    ),
    to_date: Optional[date] = Query(
        default=None,
        description="Include events on or before this date (YYYY-MM-DD, UTC)",
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[AuditEvent]:
    """
    Returns audit events matching the supplied filters, ordered most-recent-first.
    Requires Supervisor or Administrator role.
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
    if from_date is not None:
        query = query.filter(
            AuditEvent.timestamp
            >= datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        )
    if to_date is not None:
        query = query.filter(
            AuditEvent.timestamp
            <= datetime.combine(to_date, time.max, tzinfo=timezone.utc)
        )

    return query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
