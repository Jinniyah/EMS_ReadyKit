"""
core/audit.py
Shared audit event writer used across all routers.

Previously _write_audit_event() was defined locally in checks.py and called
inconsistently in check_history.py and repair_requests.py without the
accompanying logger.info() call. Centralising here (REF-1) ensures every
audit write also emits a structured log line to Log Analytics.

Usage:
    from ems_readykit.core.audit import write_audit_event

    write_audit_event(
        db,
        actor=current_user.user_id,
        action="CHECK_COMPLETED",
        entity_type="DailyInventoryCheck",
        entity_id=str(check.check_id),
        station_id=check.station_id,
        vehicle_id=check.vehicle_id,
        metadata={"status": "FAIL", ...},
        severity="HIGH",
    )

Note on commit behaviour:
    write_audit_event() calls db.commit() internally. Do not call db.commit()
    again in the calling handler after write_audit_event() — this would be a
    harmless no-op but is confusing. For handlers that need to write both a
    model update AND an audit event in one atomic operation, do the model
    update first (db.add / db.flush), then call write_audit_event() which
    commits both together.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ems_readykit.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)


def write_audit_event(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    station_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
    metadata: Optional[dict] = None,
    severity: str = "INFO",
) -> None:
    """
    Write a structured audit event to the database and emit a log line.

    All parameters are keyword-only to prevent positional argument confusion.
    The db session is committed after writing the event.
    """
    event = AuditEvent(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        station_id=station_id,
        vehicle_id=vehicle_id,
        metadata_json=metadata,
        severity=severity,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    logger.info(
        "Audit event written: action=%s entity_type=%s entity_id=%s severity=%s",
        action, entity_type, entity_id, severity,
        extra={
            "action":      action,
            "entity_type": entity_type,
            "entity_id":   entity_id,
            "severity":    severity,
            "actor":       actor,
        },
    )
