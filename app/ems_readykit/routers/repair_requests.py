"""
routers/repair_requests.py
Vehicle inactive status and repair request endpoints.

Endpoints:
  PATCH /vehicles/{id}                           — mark vehicle active/inactive (Supervisor+)
  POST  /vehicles/{id}/repair-requests           — file a repair request (all roles)
  PATCH /vehicles/{id}/repair-requests/{rid}     — update repair request status (Supervisor+)
  GET   /vehicles/{id}/repair-requests           — list repair requests for a vehicle (Supervisor+)

RBAC:
  All roles can file a repair request — a Responder discovering a broken
  piece of equipment during a check needs this without supervisor intervention.
  Status updates and the inactive toggle are Supervisor+ only.

URGENT handling:
  URGENT requests are flagged in the audit log with severity HIGH so that
  supervisors are alerted immediately via any connected audit monitoring.
  The notification system (B-E12) will consume this once it is built.

Inactive logic:
  Setting active=False requires an inactive_reason. The router sets
  inactive_since automatically to the current UTC time.
  Setting active=True clears both inactive_reason and inactive_since.
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
)
from ems_readykit.core.database import get_db
from ems_readykit.models.audit_event import AuditEvent
from ems_readykit.models.repair_request import RepairRequest, RepairSeverity, RepairStatus
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.repair_request import (
    RepairRequestCreate,
    RepairRequestOut,
    RepairRequestUpdate,
)
from ems_readykit.schemas.vehicle import VehicleRead, VehicleUpdate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vehicles", "repair-requests"])

_ALL_ROLES       = (ROLE_RESPONDER, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)


def _get_vehicle_or_404(vehicle_id: int, db: Session) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    return vehicle


def _get_repair_or_404(repair_id: int, vehicle_id: int, db: Session) -> RepairRequest:
    repair = (
        db.query(RepairRequest)
        .filter(
            RepairRequest.repair_id == repair_id,
            RepairRequest.vehicle_id == vehicle_id,
        )
        .first()
    )
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request {repair_id} not found for vehicle {vehicle_id}.",
        )
    return repair


# ── B-E1: Mark vehicle active / inactive ─────────────────────────────────────

@router.patch(
    "/vehicles/{vehicle_id}",
    response_model=VehicleRead,
    summary="Mark vehicle active or inactive",
)
def update_vehicle_status(
    vehicle_id: int,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(*_SUPERVISOR_PLUS)),
) -> Vehicle:
    """
    Toggle a vehicle's active status. Supervisor or Administrator only.

    - Setting active=False requires an inactive_reason.
      inactive_since is set automatically to the current UTC time.
    - Setting active=True clears inactive_reason and inactive_since.
    """
    vehicle = _get_vehicle_or_404(vehicle_id, db)

    if not payload.active and not payload.inactive_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="inactive_reason is required when setting a vehicle inactive.",
        )

    vehicle.active = payload.active
    if payload.active:
        vehicle.inactive_reason = None
        vehicle.inactive_since  = None
    else:
        vehicle.inactive_reason = payload.inactive_reason
        vehicle.inactive_since  = datetime.now(timezone.utc)

    db.add(
        AuditEvent(
            actor=current_user.user_id,
            action="VEHICLE_STATUS_CHANGED",
            entity_type="vehicle",
            entity_id=str(vehicle_id),
            station_id=vehicle.station_id,
            vehicle_id=vehicle_id,
            severity="INFO",
            timestamp=datetime.now(timezone.utc),
            metadata_json={
                "active":          payload.active,
                "inactive_reason": payload.inactive_reason,
            },
        )
    )

    db.commit()
    db.refresh(vehicle)
    logger.info(
        "Vehicle %s status changed to active=%s by %s",
        vehicle_id, payload.active, current_user.user_id,
        extra={"vehicle_id": vehicle_id, "actor": current_user.user_id},
    )
    return vehicle


# ── B-E4: File a repair request ───────────────────────────────────────────────

@router.post(
    "/vehicles/{vehicle_id}/repair-requests",
    response_model=RepairRequestOut,
    status_code=status.HTTP_201_CREATED,
    summary="File a repair request",
)
def create_repair_request(
    vehicle_id: int,
    payload: RepairRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(*_ALL_ROLES)),
) -> RepairRequest:
    """
    File a maintenance issue against a vehicle. All authenticated roles.

    URGENT requests are written to the audit log at severity HIGH so that
    supervisors and any connected monitoring are alerted immediately.
    """
    vehicle = _get_vehicle_or_404(vehicle_id, db)

    now = datetime.now(timezone.utc)
    repair = RepairRequest(
        vehicle_id=vehicle_id,
        station_id=vehicle.station_id,
        reported_by=current_user.user_id,
        reported_at=now,
        severity=payload.severity,
        description=payload.description,
        status=RepairStatus.OPEN,
    )
    db.add(repair)
    db.flush()

    audit_severity = "HIGH" if payload.severity == RepairSeverity.URGENT else "INFO"
    db.add(
        AuditEvent(
            actor=current_user.user_id,
            action="REPAIR_REQUEST_FILED",
            entity_type="repair_request",
            entity_id=str(repair.repair_id),
            station_id=vehicle.station_id,
            vehicle_id=vehicle_id,
            severity=audit_severity,
            timestamp=now,
            metadata_json={
                "severity":    payload.severity,
                "description": payload.description,
            },
        )
    )

    db.commit()
    db.refresh(repair)
    logger.info(
        "Repair request %s filed for vehicle %s (severity=%s) by %s",
        repair.repair_id, vehicle_id, payload.severity, current_user.user_id,
        extra={"repair_id": repair.repair_id, "actor": current_user.user_id},
    )
    return repair


# ── B-E16: Update repair request status ──────────────────────────────────────

@router.patch(
    "/vehicles/{vehicle_id}/repair-requests/{repair_id}",
    response_model=RepairRequestOut,
    summary="Update repair request status",
)
def update_repair_request(
    vehicle_id: int,
    repair_id: int,
    payload: RepairRequestUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(*_SUPERVISOR_PLUS)),
) -> RepairRequest:
    """
    Advance a repair request through its lifecycle. Supervisor+ only.

    - OPEN → IN_PROGRESS or RESOLVED
    - IN_PROGRESS → RESOLVED
    - resolution_notes is required when status is RESOLVED.
    - Cannot re-open a RESOLVED request.
    """
    repair = _get_repair_or_404(repair_id, vehicle_id, db)

    if repair.status == RepairStatus.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update a resolved repair request.",
        )

    if payload.status == RepairStatus.RESOLVED and not payload.resolution_notes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="resolution_notes is required when resolving a repair request.",
        )

    now = datetime.now(timezone.utc)
    repair.status = payload.status
    if payload.resolution_notes:
        repair.resolution_notes = payload.resolution_notes
    if payload.status == RepairStatus.RESOLVED:
        repair.resolved_by = current_user.user_id
        repair.resolved_at = now

    db.add(
        AuditEvent(
            actor=current_user.user_id,
            action="REPAIR_REQUEST_UPDATED",
            entity_type="repair_request",
            entity_id=str(repair_id),
            station_id=repair.station_id,
            vehicle_id=vehicle_id,
            severity="INFO",
            timestamp=now,
            metadata_json={
                "new_status":       payload.status,
                "resolution_notes": payload.resolution_notes,
            },
        )
    )

    db.commit()
    db.refresh(repair)
    return repair


# ── B-E17: List repair requests for a vehicle ─────────────────────────────────

@router.get(
    "/vehicles/{vehicle_id}/repair-requests",
    response_model=List[RepairRequestOut],
    summary="List repair requests for a vehicle",
)
def list_repair_requests(
    vehicle_id: int,
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by status: OPEN, IN_PROGRESS, or RESOLVED",
    ),
    db: Session = Depends(get_db),
    current_user=Depends(require_role(*_SUPERVISOR_PLUS)),
) -> List[RepairRequest]:
    """
    List all repair requests for a vehicle, most recent first.
    Optionally filter by status. Supervisor+ only.
    """
    _get_vehicle_or_404(vehicle_id, db)

    query = db.query(RepairRequest).filter(RepairRequest.vehicle_id == vehicle_id)

    if status_filter:
        try:
            parsed = RepairStatus(status_filter.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status '{status_filter}'. Must be one of: {[s.value for s in RepairStatus]}",
            )
        query = query.filter(RepairRequest.status == parsed)

    return query.order_by(RepairRequest.reported_at.desc()).all()
