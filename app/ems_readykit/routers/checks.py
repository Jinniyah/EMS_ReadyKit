"""
routers/checks.py
Daily inventory check and controlled substance check endpoints.

Endpoints:
  POST /checks/daily                            — submit a daily check (all roles)
  GET  /checks/daily/{id}                       — get a daily check (Supervisor, Administrator)
  GET  /checks/daily/vehicle/{vehicle_id}       — list checks for a vehicle (all roles)
  GET  /checks/daily/station/{station_id}/today — compliance status for today (Supervisor, Administrator)
  POST /checks/controlled-substance             — submit a CS check (all roles)
  GET  /checks/controlled-substance/{id}        — get a CS check (Supervisor, Administrator)
  GET  /checks/controlled-substance/vehicle/{vehicle_id} — list CS checks (Supervisor, Administrator)

RBAC notes:
- POST endpoints allow all authenticated roles (Responders perform checks).
- GET detail/list endpoints are restricted to Supervisor+ to prevent
  Responders from browsing other vehicles' check history.
- The vehicle/{id} list is all-roles so a Responder can see their own
  vehicle's history. Station-scoped compliance is Supervisor+ only.

Identity binding:
- performed_by and primary_signer are set from the JWT identity (current_user.name)
  rather than from the request body. The fields are still present in the schema
  as Optional so existing seeded data and tests without identity are still valid.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    ROLE_RESPONDER,
    ROLE_SUPERVISOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.audit_event import AuditEvent
from ems_readykit.models.controlled_substance_check import ControlledSubstanceCheck
from ems_readykit.models.daily_inventory_check import DailyInventoryCheck
from ems_readykit.models.station import Station
from ems_readykit.models.vehicle import Vehicle, VehicleType
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.controlled_substance_check import (
    ControlledSubstanceCheckCreate,
    ControlledSubstanceCheckRead,
)
from ems_readykit.schemas.daily_inventory_check import (
    DailyInventoryCheckCreate,
    DailyInventoryCheckRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/checks", tags=["checks"])

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


def _write_audit_event(
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
    """Write an immutable audit event record after a successful commit."""
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
        "Audit event written",
        extra={
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "severity": severity,
        },
    )


# ── Daily Inventory Checks ────────────────────────────────────────────────────

@router.post(
    "/daily",
    response_model=DailyInventoryCheckRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a daily inventory check",
)
def create_daily_check(
    payload: DailyInventoryCheckCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*_ALL_ROLES)),
) -> DailyInventoryCheck:
    """
    Submits a daily inventory check for a vehicle.
    performed_by is set from the authenticated user's identity.
    Returns 404 if the vehicle or station does not exist.
    Returns 409 if a check for this vehicle on this date already exists.
    """
    vehicle = _get_vehicle_or_404(payload.vehicle_id, db)

    station = db.query(Station).filter(Station.station_id == payload.station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {payload.station_id} not found.",
        )

    # Bind identity from JWT — override any value submitted in the request body
    performed_by = current_user.name

    check = DailyInventoryCheck(
        vehicle_id=payload.vehicle_id,
        station_id=payload.station_id,
        check_date=payload.check_date,
        performed_by=performed_by,
        timestamp=payload.timestamp,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(check)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A daily inventory check for vehicle {payload.vehicle_id} "
                f"on {payload.check_date} already exists. "
                "Use GET /checks/daily/vehicle/{vehicle_id} to retrieve it."
            ),
        )
    db.refresh(check)

    _write_audit_event(
        db,
        actor=performed_by,
        action="CHECK_COMPLETED",
        entity_type="DailyInventoryCheck",
        entity_id=str(check.check_id),
        station_id=payload.station_id,
        vehicle_id=payload.vehicle_id,
        metadata={"status": payload.status.value, "check_date": payload.check_date},
        severity="INFO",
    )
    return check


@router.get(
    "/daily/{check_id}",
    response_model=DailyInventoryCheckRead,
    summary="Get a daily inventory check",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def get_daily_check(check_id: int, db: Session = Depends(get_db)) -> DailyInventoryCheck:
    """Returns a single daily inventory check by ID. Requires Supervisor or Administrator."""
    check = (
        db.query(DailyInventoryCheck)
        .filter(DailyInventoryCheck.check_id == check_id)
        .first()
    )
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daily inventory check {check_id} not found.",
        )
    return check


@router.get(
    "/daily/vehicle/{vehicle_id}",
    response_model=List[DailyInventoryCheckRead],
    summary="List daily checks for a vehicle",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def list_vehicle_daily_checks(
    vehicle_id: int, db: Session = Depends(get_db)
) -> List[DailyInventoryCheck]:
    """Returns all daily inventory checks for a vehicle, most recent first. All authenticated roles."""
    _get_vehicle_or_404(vehicle_id, db)
    return (
        db.query(DailyInventoryCheck)
        .filter(DailyInventoryCheck.vehicle_id == vehicle_id)
        .order_by(DailyInventoryCheck.check_date.desc())
        .all()
    )


@router.get(
    "/daily/station/{station_id}/today",
    response_model=List[DailyInventoryCheckRead],
    summary="Get today's compliance status for a station",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def get_station_compliance_today(
    station_id: int, db: Session = Depends(get_db)
) -> List[DailyInventoryCheck]:
    """
    Returns all completed daily checks for a station for today.
    Requires Supervisor or Administrator.
    """
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )

    today = datetime.now(timezone.utc).date().isoformat()
    return (
        db.query(DailyInventoryCheck)
        .filter(
            DailyInventoryCheck.station_id == station_id,
            DailyInventoryCheck.check_date == today,
        )
        .all()
    )


# ── Controlled Substance Checks ───────────────────────────────────────────────

@router.post(
    "/controlled-substance",
    response_model=ControlledSubstanceCheckRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a controlled substance check",
)
def create_cs_check(
    payload: ControlledSubstanceCheckCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*_ALL_ROLES)),
) -> ControlledSubstanceCheck:
    """
    Submits a dual-signature controlled substance check for an ALS vehicle.
    primary_signer is set from the authenticated user's identity.
    secondary_signer must still be provided in the request body (dual-signature requirement).
    Returns 422 if the vehicle is not an ALS unit.
    Generates a HIGH severity audit event if discrepancy_flag=True.
    """
    vehicle = _get_vehicle_or_404(payload.vehicle_id, db)

    if not vehicle.requires_controlled_substance_check:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Vehicle {payload.vehicle_id} is type '{vehicle.vehicle_type.value}'. "
                "Controlled substance checks are only required for ALS vehicles."
            ),
        )

    # Bind primary signer from JWT identity
    primary_signer = current_user.name

    # Validate that secondary signer differs from the JWT-bound primary signer
    if primary_signer.strip().lower() == payload.secondary_signer.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "primary_signer and secondary_signer must be different people. "
                "The dual-signature workflow requires two witnesses."
            ),
        )

    check = ControlledSubstanceCheck(
        vehicle_id=payload.vehicle_id,
        primary_signer=primary_signer,
        secondary_signer=payload.secondary_signer,
        timestamp=payload.timestamp,
        discrepancy_flag=payload.discrepancy_flag,
        notes=payload.notes,
    )
    db.add(check)
    db.commit()
    db.refresh(check)

    severity = "HIGH" if payload.discrepancy_flag else "INFO"
    action = "CS_DISCREPANCY" if payload.discrepancy_flag else "CS_CHECK_COMPLETED"

    if payload.discrepancy_flag:
        logger.warning(
            "Controlled substance discrepancy flagged",
            extra={
                "vehicle_id": payload.vehicle_id,
                "primary_signer": primary_signer,
                "secondary_signer": payload.secondary_signer,
                "cs_check_id": check.cs_check_id,
            },
        )

    _write_audit_event(
        db,
        actor=primary_signer,
        action=action,
        entity_type="ControlledSubstanceCheck",
        entity_id=str(check.cs_check_id),
        vehicle_id=payload.vehicle_id,
        station_id=vehicle.station_id,
        metadata={
            "secondary_signer": payload.secondary_signer,
            "discrepancy_flag": payload.discrepancy_flag,
            "notes": payload.notes,
        },
        severity=severity,
    )
    return check


@router.get(
    "/controlled-substance/{cs_check_id}",
    response_model=ControlledSubstanceCheckRead,
    summary="Get a controlled substance check",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def get_cs_check(
    cs_check_id: int, db: Session = Depends(get_db)
) -> ControlledSubstanceCheck:
    """Returns a single CS check by ID. Requires Supervisor or Administrator."""
    check = (
        db.query(ControlledSubstanceCheck)
        .filter(ControlledSubstanceCheck.cs_check_id == cs_check_id)
        .first()
    )
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Controlled substance check {cs_check_id} not found.",
        )
    return check


@router.get(
    "/controlled-substance/vehicle/{vehicle_id}",
    response_model=List[ControlledSubstanceCheckRead],
    summary="List CS checks for a vehicle",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def list_vehicle_cs_checks(
    vehicle_id: int, db: Session = Depends(get_db)
) -> List[ControlledSubstanceCheck]:
    """Returns all CS checks for a vehicle, most recent first. Requires Supervisor or Administrator."""
    vehicle = _get_vehicle_or_404(vehicle_id, db)

    if not vehicle.requires_controlled_substance_check:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Vehicle {vehicle_id} is type '{vehicle.vehicle_type.value}'. "
                "Only ALS vehicles have controlled substance checks."
            ),
        )
    return (
        db.query(ControlledSubstanceCheck)
        .filter(ControlledSubstanceCheck.vehicle_id == vehicle_id)
        .order_by(ControlledSubstanceCheck.timestamp.desc())
        .all()
    )
