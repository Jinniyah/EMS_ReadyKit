"""
routers/check_history.py
Check history, acknowledgement, and soft-delete endpoints.

Refactor (Session B):
- Role constants imported from deps (REF-3)
- write_audit_event imported from core.audit (REF-1)
- HTTP_422_UNPROCESSABLE_CONTENT replaces deprecated constant (REF-7)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ems_readykit.core.audit import write_audit_event
from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    ROLE_SUPERVISOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.daily_inventory_check import DailyInventoryCheck
from ems_readykit.routers.deps import (
    ADMIN_ONLY,
    ALL_ROLES,
    SUPERVISOR_PLUS,
    require_role,
)
from ems_readykit.schemas.daily_inventory_check import (
    AcknowledgeRequest,
    DailyInventoryCheckRead,
    SoftDeleteRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["check-history"])


def _get_check_or_404(
    check_id: int, db: Session, *, include_deleted: bool = False
) -> DailyInventoryCheck:
    query = db.query(DailyInventoryCheck).filter(
        DailyInventoryCheck.check_id == check_id
    )
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
    station_id: Optional[int] = Query(
        default=None, gt=0, description="Scope to a specific station"
    ),
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
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[DailyInventoryCheck]:
    performed_by_identity = current_user.email or current_user.name
    query = db.query(DailyInventoryCheck).filter(
        DailyInventoryCheck.performed_by == performed_by_identity,
        DailyInventoryCheck.deleted_at.is_(None),
    )
    if station_id is not None:
        query = query.filter(DailyInventoryCheck.station_id == station_id)
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
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> DailyInventoryCheck:
    check = _get_check_or_404(check_id, db)

    if not current_user.has_role(ROLE_SUPERVISOR, ROLE_ADMINISTRATOR):
        if check.performed_by != (current_user.email or current_user.name):
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
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> DailyInventoryCheck:
    check = _get_check_or_404(check_id, db)

    # Responders can only add notes to their own checks
    if not current_user.has_role(ROLE_SUPERVISOR, ROLE_ADMINISTRATOR):
        if check.performed_by != (current_user.email or current_user.name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only add notes to your own checks.",
            )

    now = datetime.now(timezone.utc)
    check.reviewed_by = current_user.user_id
    check.reviewed_at = now
    check.corrective_action = payload.corrective_action
    db.add(check)
    db.flush()

    write_audit_event(
        db,
        actor=current_user.user_id,
        action="CHECK_ACKNOWLEDGED",
        entity_type="daily_inventory_check",
        entity_id=str(check_id),
        station_id=check.station_id,
        vehicle_id=check.vehicle_id,
        metadata={
            "check_status": check.status.value,
            "corrective_action": payload.corrective_action,
        },
        severity="INFO",
    )

    db.refresh(check)
    logger.info(
        "Check %s acknowledged by %s",
        check_id,
        current_user.user_id,
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
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> DailyInventoryCheck:
    check = _get_check_or_404(check_id, db, include_deleted=True)

    if check.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This check has already been deleted.",
        )

    now = datetime.now(timezone.utc)
    check.deleted_at = now
    check.deleted_by = current_user.user_id
    check.deletion_reason = payload.deletion_reason
    db.add(check)
    db.flush()

    write_audit_event(
        db,
        actor=current_user.user_id,
        action="CHECK_SOFT_DELETED",
        entity_type="daily_inventory_check",
        entity_id=str(check_id),
        station_id=check.station_id,
        vehicle_id=check.vehicle_id,
        metadata={
            "deletion_reason": payload.deletion_reason,
            "check_date": check.check_date,
            "check_status": check.status.value,
        },
        severity="WARNING",
    )

    db.refresh(check)
    logger.warning(
        "Check %s soft-deleted by %s — reason: %s",
        check_id,
        current_user.user_id,
        payload.deletion_reason,
        extra={"check_id": check_id, "actor": current_user.user_id},
    )
    return check


# ── CH-F7: GET deleted checks for a station ─────────────────────────────────


@router.get(
    "/checks/daily/deleted",
    response_model=List[DailyInventoryCheckRead],
    summary="List soft-deleted checks for a station (CH-F7)",
)
def list_deleted_checks(
    station_id: int = Query(..., gt=0, description="Station to scope the query"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[DailyInventoryCheck]:
    return (
        db.query(DailyInventoryCheck)
        .filter(
            DailyInventoryCheck.station_id == station_id,
            DailyInventoryCheck.deleted_at.isnot(None),
        )
        .order_by(DailyInventoryCheck.deleted_at.desc())
        .all()
    )


# ── CH-F8: DELETE /checks/daily/{id}/force — permanent hard-delete ────────────


@router.delete(
    "/checks/daily/{check_id}/force",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a soft-deleted check (CH-F8, Admin only)",
)
def force_delete_check(
    check_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ADMIN_ONLY)),
) -> None:
    check = _get_check_or_404(check_id, db, include_deleted=True)
    if check.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only soft-deleted checks can be permanently deleted. Soft-delete it first.",
        )

    write_audit_event(
        db,
        actor=current_user.user_id,
        action="CHECK_HARD_DELETED",
        entity_type="daily_inventory_check",
        entity_id=str(check_id),
        station_id=check.station_id,
        vehicle_id=check.vehicle_id,
        metadata={
            "deletion_reason": check.deletion_reason,
            "check_date": check.check_date,
            "check_status": check.status.value,
        },
        severity="CRITICAL",
    )

    db.delete(check)
    db.commit()
    logger.warning(
        "Check %s permanently deleted by %s",
        check_id,
        current_user.user_id,
        extra={"check_id": check_id, "actor": current_user.user_id},
    )
