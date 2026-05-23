"""
routers/check_history.py
Check history, acknowledgement, and soft-delete endpoints.

Endpoints:
  GET    /checks/daily/my-history          — responder's own submitted checks (all roles)
  GET    /checks/daily/{id}/detail         — full check detail with RBAC scoping
  PATCH  /checks/daily/{id}/acknowledge    — supervisor adds corrective action (Supervisor+)
  DELETE /checks/daily/{id}                — soft-delete a check (Supervisor+)

Soft-delete behaviour:
  - deleted_at is set immediately; check is hidden from all normal queries.
  - Hard-deleted after 90 days by a scheduled job (Q-6).
  - Responders cannot see soft-deleted checks in their history.
  - Supervisors cannot see soft-deleted checks in normal list views.
  - Admin restore/force-delete endpoints are in scope for the next cluster (CH-B4/5/6).

Acknowledgement behaviour:
  - Any Supervisor+ can acknowledge a FAIL check by recording corrective action.
  - reviewed_by and reviewed_at are set automatically.
  - Re-acknowledging overwrites the previous note (supervisor correction).

RBAC:
  CH-B1 (my-history): all roles — scoped to current user's own checks
  CH-B2 (detail):     Responders see own checks only; Supervisor+ see any at their station
  B-E2  (acknowledge): Supervisor+ only
  CH-B3 (soft-delete): Supervisor+ only
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    ROLE_RESPONDER,
    ROLE_SUPERVISOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.audit_event import AuditEvent
from ems_readykit.models.daily_inventory_check import DailyInventoryCheck, CheckStatus
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.daily_inventory_check import (
    AcknowledgeRequest,
    DailyInventoryCheckRead,
    SoftDeleteRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["check-history"])

_ALL_ROLES       = (ROLE_RESPONDER, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)


def _get_check_or_404(check_id: int, db: Session, *, include_deleted: bool = False) -> DailyInventoryCheck:
    query = db.query(DailyInventoryCheck).filter(DailyInventoryCheck.check_id == check_id)
    if not include_deleted:
        query = query.filter(DailyInventoryCheck.deleted_at.is_(None))
    check = query.first()
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Check {check_id} not found.",
        )
    return check


# ── CH-B1: Responder's own check history ─────────────────────────────────────

@router.get(
    "/checks/daily/my-history",
    response_model=List[DailyInventoryCheckRead],
    summary="My submitted checks",
)
def my_check_history(
    from_date: Optional[str] = Query(
        default=None,
        alias="from",
        description="Start date filter YYYY-MM-DD (inclusive)",
    ),
    to_date: Optional[str] = Query(
        default=None,
        alias="to",
        description="End date filter YYYY-MM-DD (inclusive)",
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*_ALL_ROLES)),
) -> List[DailyInventoryCheck]:
    """
    Returns the current user's submitted checks, most recent first.
    Excludes soft-deleted records. All authenticated roles.
    """
    query = (
        db.query(DailyInventoryCheck)
        .filter(
            DailyInventoryCheck.performed_by == current_user.name,
            DailyInventoryCheck.deleted_at.is_(None),
        )
    )
    if from_date:
        query = query.filter(DailyInventoryCheck.check_date >= from_date)
    if to_date:
        query = query.filter(DailyInventoryCheck.check_date <= to_date)

    return query.order_by(DailyInventoryCheck.timestamp.desc()).all()


# ── CH-B2: Full check detail with RBAC scoping ───────────────────────────────

@router.get(
    "/checks/daily/{check_id}/detail",
    response_model=DailyInventoryCheckRead,
    summary="Get full check detail",
)
def get_check_detail(
    check_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*_ALL_ROLES)),
) -> DailyInventoryCheck:
    """
    Returns full check detail including all line items.
    Responders can only access their own checks.
    Supervisor+ can access any non-deleted check.
    Soft-deleted checks are not accessible via this endpoint.
    """
    check = _get_check_or_404(check_id, db)

    # Responders are scoped to their own checks only
    if not current_user.has_role(ROLE_SUPERVISOR, ROLE_ADMINISTRATOR):
        if check.performed_by != current_user.name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own checks.",
            )

    return check


# ── B-E2: Acknowledge a FAIL check ───────────────────────────────────────────

@router.patch(
    "/checks/daily/{check_id}/acknowledge",
    response_model=DailyInventoryCheckRead,
    summary="Acknowledge a check with corrective action",
)
def acknowledge_check(
    check_id: int,
    payload: AcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*_SUPERVISOR_PLUS)),
) -> DailyInventoryCheck:
    """
    Supervisor records corrective action on a submitted check.
    Typically used on FAIL or NEEDS_RESTOCK checks.
    Re-acknowledging overwrites the previous note.
    Soft-deleted checks cannot be acknowledged.
    """
    check = _get_check_or_404(check_id, db)

    now = datetime.now(timezone.utc)
    check.reviewed_by       = current_user.user_id
    check.reviewed_at       = now
    check.corrective_action = payload.corrective_action

    db.add(
        AuditEvent(
            actor=current_user.user_id,
            action="CHECK_ACKNOWLEDGED",
            entity_type="daily_inventory_check",
            entity_id=str(check_id),
            station_id=check.station_id,
            vehicle_id=check.vehicle_id,
            severity="INFO",
            timestamp=now,
            metadata_json={
                "check_status":      check.status.value,
                "corrective_action": payload.corrective_action,
            },
        )
    )

    db.commit()
    db.refresh(check)
    logger.info(
        "Check %s acknowledged by %s",
        check_id, current_user.user_id,
        extra={"check_id": check_id, "actor": current_user.user_id},
    )
    return check


# ── CH-B3: Soft-delete a check ────────────────────────────────────────────────

@router.delete(
    "/checks/daily/{check_id}",
    response_model=DailyInventoryCheckRead,
    summary="Soft-delete a check",
)
def soft_delete_check(
    check_id: int,
    payload: SoftDeleteRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*_SUPERVISOR_PLUS)),
) -> DailyInventoryCheck:
    """
    Supervisor+ soft-deletes a check record. The check is hidden from all
    normal queries immediately and will be hard-deleted after 90 days.
    A mandatory deletion_reason must be provided.
    Already-deleted checks return 409.
    """
    check = _get_check_or_404(check_id, db, include_deleted=True)

    if check.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This check has already been deleted.",
        )

    now = datetime.now(timezone.utc)
    check.deleted_at      = now
    check.deleted_by      = current_user.user_id
    check.deletion_reason = payload.deletion_reason

    db.add(
        AuditEvent(
            actor=current_user.user_id,
            action="CHECK_SOFT_DELETED",
            entity_type="daily_inventory_check",
            entity_id=str(check_id),
            station_id=check.station_id,
            vehicle_id=check.vehicle_id,
            severity="WARNING",
            timestamp=now,
            metadata_json={
                "deletion_reason": payload.deletion_reason,
                "check_date":      check.check_date,
                "check_status":    check.status.value,
            },
        )
    )

    db.commit()
    db.refresh(check)
    logger.warning(
        "Check %s soft-deleted by %s — reason: %s",
        check_id, current_user.user_id, payload.deletion_reason,
        extra={"check_id": check_id, "actor": current_user.user_id},
    )
    return check
