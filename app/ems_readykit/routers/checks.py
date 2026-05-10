"""
routers/checks.py
Daily inventory check and controlled substance check endpoints.

Endpoints:
  POST /checks/daily                            — submit a daily inventory check
  GET  /checks/daily/{id}                       — get a daily check
  GET  /checks/daily/vehicle/{vehicle_id}       — list checks for a vehicle
  GET  /checks/daily/station/{station_id}/today — compliance status for a station today
  POST /checks/controlled-substance             — submit a CS check
  GET  /checks/controlled-substance/{id}        — get a CS check
  GET  /checks/controlled-substance/vehicle/{vehicle_id} — list CS checks for a vehicle

Design decisions:
- Daily check uniqueness (one per vehicle per day) is enforced by the DB
  UniqueConstraint. The router catches IntegrityError and converts it to 409
  with a message explaining what already exists and how to retrieve it.
- The /today compliance endpoint is the primary supervisor dashboard view.
  It returns the check record for each vehicle if it exists, or null if not
  yet completed, so the dashboard can show a complete compliance picture.
- CS checks are restricted to ALS vehicles. Non-ALS vehicle IDs return 422
  with an explanation. This enforces FR-7 at the API layer.
- A HIGH severity AuditEvent is created when discrepancy_flag=True on a CS check.
  This is the primary SIEM trigger in the application.
- performed_by / primary_signer are free-form strings in Phase 2. Phase 3
  will bind these to the authenticated user's JWT identity claim.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db
from ems_readykit.models.audit_event import AuditEvent
from ems_readykit.models.controlled_substance_check import ControlledSubstanceCheck
from ems_readykit.models.daily_inventory_check import DailyInventoryCheck
from ems_readykit.models.station import Station
from ems_readykit.models.vehicle import Vehicle, VehicleType
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
    """
    Write an immutable audit event record.
    Called after successful DB commits so the audit record reflects
    a real persisted state change, not a speculative one.
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
    payload: DailyInventoryCheckCreate, db: Session = Depends(get_db)
) -> DailyInventoryCheck:
    """
    Submits a daily inventory check for a vehicle.
    Returns 404 if the vehicle or station does not exist.
    Returns 409 if a check for this vehicle on this date already exists.
    """
    # Validate vehicle exists
    vehicle = _get_vehicle_or_404(payload.vehicle_id, db)

    # Validate station exists
    station = db.query(Station).filter(Station.station_id == payload.station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {payload.station_id} not found.",
        )

    check = DailyInventoryCheck(
        vehicle_id=payload.vehicle_id,
        station_id=payload.station_id,
        check_date=payload.check_date,
        performed_by=payload.performed_by,
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

    # Write audit event after successful commit
    _write_audit_event(
        db,
        actor=payload.performed_by,
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
)
def get_daily_check(check_id: int, db: Session = Depends(get_db)) -> DailyInventoryCheck:
    """Returns a single daily inventory check by ID. Returns 404 if not found."""
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
)
def list_vehicle_daily_checks(
    vehicle_id: int, db: Session = Depends(get_db)
) -> List[DailyInventoryCheck]:
    """
    Returns all daily inventory checks for a vehicle, most recent first.
    Returns 404 if the vehicle does not exist.
    """
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
)
def get_station_compliance_today(
    station_id: int, db: Session = Depends(get_db)
) -> List[DailyInventoryCheck]:
    """
    Returns all completed daily checks for a station for today.
    Compare the count against active vehicles to determine compliance status.
    Returns 404 if the station does not exist.
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
    payload: ControlledSubstanceCheckCreate, db: Session = Depends(get_db)
) -> ControlledSubstanceCheck:
    """
    Submits a dual-signature controlled substance check for an ALS vehicle.
    Returns 404 if the vehicle does not exist.
    Returns 422 if the vehicle is not an ALS unit (CS checks are ALS-only).
    Automatically generates a HIGH severity audit event if discrepancy_flag=True.
    """
    vehicle = _get_vehicle_or_404(payload.vehicle_id, db)

    # Enforce ALS-only rule (FR-7) — non-ALS vehicles do not track CS items
    if not vehicle.requires_controlled_substance_check:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Vehicle {payload.vehicle_id} is type '{vehicle.vehicle_type.value}'. "
                "Controlled substance checks are only required for ALS vehicles."
            ),
        )

    check = ControlledSubstanceCheck(
        vehicle_id=payload.vehicle_id,
        primary_signer=payload.primary_signer,
        secondary_signer=payload.secondary_signer,
        timestamp=payload.timestamp,
        discrepancy_flag=payload.discrepancy_flag,
        notes=payload.notes,
    )
    db.add(check)
    db.commit()
    db.refresh(check)

    # Determine audit severity — discrepancies are HIGH, normal checks are INFO
    severity = "HIGH" if payload.discrepancy_flag else "INFO"
    action = "CS_DISCREPANCY" if payload.discrepancy_flag else "CS_CHECK_COMPLETED"

    if payload.discrepancy_flag:
        logger.warning(
            "Controlled substance discrepancy flagged",
            extra={
                "vehicle_id": payload.vehicle_id,
                "primary_signer": payload.primary_signer,
                "secondary_signer": payload.secondary_signer,
                "cs_check_id": check.cs_check_id,
            },
        )

    _write_audit_event(
        db,
        actor=payload.primary_signer,
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
)
def get_cs_check(
    cs_check_id: int, db: Session = Depends(get_db)
) -> ControlledSubstanceCheck:
    """Returns a single CS check by ID. Returns 404 if not found."""
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
)
def list_vehicle_cs_checks(
    vehicle_id: int, db: Session = Depends(get_db)
) -> List[ControlledSubstanceCheck]:
    """
    Returns all controlled substance checks for a vehicle, most recent first.
    Returns 404 if the vehicle does not exist.
    Returns 422 if the vehicle is not an ALS unit.
    """
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
