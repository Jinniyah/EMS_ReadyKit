"""
tests/test_repair_requests.py
Tests for repair request endpoints and vehicle inactive status.

Covers:
  - POST   /vehicles/{id}/repair-requests  — all roles can file
  - GET    /vehicles/{id}/repair-requests  — Supervisor+ only
  - PATCH  /vehicles/{id}/repair-requests/{rid}  — Supervisor+ lifecycle
  - PATCH  /vehicles/{id}  — mark vehicle inactive/active (Supervisor+)
  - RBAC enforcement on all restricted endpoints
  - URGENT audit severity
  - Business rule validation (inactive_reason required, resolution_notes required)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import pytest
from sqlalchemy.orm import Session

from ems_readykit.models import (
    AuditEvent,
    InventoryLocation,
    LocationType,
    Station,
    Vehicle,
    VehicleType,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _station(db: Session, *, name: Optional[str] = None) -> Station:
    s = Station(name=name or f"Station-{_uid()}", address="1 Main St", region="Downriver")
    db.add(s)
    db.flush()
    return s


def _vehicle(db: Session, station_id: int, *, number: Optional[str] = None) -> Vehicle:
    number = number or f"AMB-{_uid()}"
    v = Vehicle(station_id=station_id, vehicle_number=number, vehicle_type=VehicleType.ALS)
    db.add(v)
    db.flush()
    loc = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station_id,
        vehicle_id=v.vehicle_id,
        label=f"{number} — ALS",
    )
    db.add(loc)
    db.flush()
    return v


# ── File a repair request (POST) ───────────────────────────────────────────────

class TestFileRepairRequest:
    def test_responder_can_file_routine(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"severity": "ROUTINE", "description": "Rear cabinet door latch is broken."},
            headers=auth_responder,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["vehicle_id"] == v.vehicle_id
        assert data["severity"] == "ROUTINE"
        assert data["status"] == "OPEN"
        assert data["description"] == "Rear cabinet door latch is broken."

    def test_supervisor_can_file_urgent(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"severity": "URGENT", "description": "Brakes are grinding badly — unsafe to operate."},
            headers=auth_supervisor,
        )
        assert resp.status_code == 201
        assert resp.json()["severity"] == "URGENT"

    def test_urgent_creates_high_severity_audit(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"severity": "URGENT", "description": "Engine warning light is on."},
            headers=auth_supervisor,
        )
        audit = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "REPAIR_REQUEST_FILED", AuditEvent.severity == "HIGH")
            .first()
        )
        assert audit is not None

    def test_routine_creates_info_severity_audit(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"severity": "ROUTINE", "description": "Overhead light is flickering."},
            headers=auth_responder,
        )
        audit = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "REPAIR_REQUEST_FILED", AuditEvent.severity == "INFO")
            .first()
        )
        assert audit is not None

    def test_description_too_short_returns_422(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Bad"},
            headers=auth_responder,
        )
        assert resp.status_code == 422

    def test_vehicle_not_found_returns_404(self, client, auth_responder):
        resp = client.post(
            "/api/v1/vehicles/99999/repair-requests",
            json={"description": "Something is wrong with this vehicle."},
            headers=auth_responder,
        )
        assert resp.status_code == 404

    def test_unauthenticated_returns_403(self, client, db):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Something is broken here."},
        )
        assert resp.status_code in (401, 403)


# ── List repair requests (GET) ─────────────────────────────────────────────────

class TestListRepairRequests:
    def test_supervisor_can_list(self, client, db, auth_supervisor, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "First issue to report here."},
            headers=auth_responder,
        )
        client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Second issue to report here."},
            headers=auth_responder,
        )
        resp = client.get(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            headers=auth_supervisor,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_responder_can_list(self, client, db, auth_responder):
        """All roles can view repair requests — responders need visibility into vehicle status."""
        s = _station(db)
        v = _vehicle(db, s.station_id)
        client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Overhead cabinet door hinge is broken."},
            headers=auth_responder,
        )
        resp = client.get(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            headers=auth_responder,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_filter_by_status(self, client, db, auth_supervisor, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Open issue that needs attention soon."},
            headers=auth_responder,
        )
        resp = client.get(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests?status=OPEN",
            headers=auth_supervisor,
        )
        assert resp.status_code == 200
        assert all(r["status"] == "OPEN" for r in resp.json())

    def test_filter_invalid_status_returns_422(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        resp = client.get(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests?status=BOGUS",
            headers=auth_supervisor,
        )
        assert resp.status_code == 422


# ── Update repair request status (PATCH) ──────────────────────────────────────

class TestUpdateRepairRequest:
    def test_supervisor_can_advance_to_in_progress(self, client, db, auth_supervisor, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        create_resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Siren speaker sounds distorted when tested."},
            headers=auth_responder,
        )
        repair_id = create_resp.json()["repair_id"]

        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests/{repair_id}",
            json={"status": "IN_PROGRESS"},
            headers=auth_supervisor,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "IN_PROGRESS"

    def test_resolve_requires_resolution_notes(self, client, db, auth_supervisor, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        create_resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Rear door seal is worn and leaking air."},
            headers=auth_responder,
        )
        repair_id = create_resp.json()["repair_id"]

        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests/{repair_id}",
            json={"status": "RESOLVED"},
            headers=auth_supervisor,
        )
        assert resp.status_code == 422

    def test_resolve_with_notes_succeeds(self, client, db, auth_supervisor, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        create_resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Windshield wiper blade is cracked and streaking."},
            headers=auth_responder,
        )
        repair_id = create_resp.json()["repair_id"]

        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests/{repair_id}",
            json={"status": "RESOLVED", "resolution_notes": "Replaced both wiper blades."},
            headers=auth_supervisor,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "RESOLVED"
        assert data["resolved_by"] is not None
        assert data["resolved_at"] is not None
        assert data["resolution_notes"] == "Replaced both wiper blades."

    def test_cannot_update_resolved_request(self, client, db, auth_supervisor, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        create_resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Oxygen tank mount bracket is slightly bent."},
            headers=auth_responder,
        )
        repair_id = create_resp.json()["repair_id"]

        client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests/{repair_id}",
            json={"status": "RESOLVED", "resolution_notes": "Bracket replaced and tested."},
            headers=auth_supervisor,
        )
        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests/{repair_id}",
            json={"status": "IN_PROGRESS"},
            headers=auth_supervisor,
        )
        assert resp.status_code == 409

    def test_responder_cannot_resolve(self, client, db, auth_responder):
        """Responders can mark In Progress but cannot resolve — Supervisor+ only."""
        s = _station(db)
        v = _vehicle(db, s.station_id)
        create_resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Interior dome light switch is intermittent."},
            headers=auth_responder,
        )
        repair_id = create_resp.json()["repair_id"]

        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests/{repair_id}",
            json={"status": "RESOLVED", "resolution_notes": "Replaced the light switch."},
            headers=auth_responder,
        )
        assert resp.status_code == 403

    def test_responder_can_mark_in_progress(self, client, db, auth_responder):
        """Any role can advance OPEN → IN_PROGRESS."""
        s = _station(db)
        v = _vehicle(db, s.station_id)
        create_resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Headlights are flickering when the engine idles."},
            headers=auth_responder,
        )
        repair_id = create_resp.json()["repair_id"]

        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests/{repair_id}",
            json={"status": "IN_PROGRESS"},
            headers=auth_responder,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "IN_PROGRESS"

    def test_responder_can_mark_in_progress_with_optional_note(self, client, db, auth_responder):
        """IN_PROGRESS transition stores an optional note without requiring it."""
        s = _station(db)
        v = _vehicle(db, s.station_id)
        create_resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Rear step light is out and needs replacement."},
            headers=auth_responder,
        )
        repair_id = create_resp.json()["repair_id"]

        # With note
        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests/{repair_id}",
            json={"status": "IN_PROGRESS", "resolution_notes": "Ordered replacement bulb."},
            headers=auth_responder,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["resolution_notes"] == "Ordered replacement bulb."

    def test_responder_can_mark_in_progress_without_note(self, client, db, auth_responder):
        """IN_PROGRESS transition succeeds when no note is provided."""
        s = _station(db)
        v = _vehicle(db, s.station_id)
        create_resp = client.post(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests",
            json={"description": "Windshield has a small crack in the lower corner."},
            headers=auth_responder,
        )
        repair_id = create_resp.json()["repair_id"]

        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}/repair-requests/{repair_id}",
            json={"status": "IN_PROGRESS"},
            headers=auth_responder,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "IN_PROGRESS"
        assert resp.json()["resolution_notes"] is None


# ── Mark vehicle inactive / active (PATCH /vehicles/{id}) ─────────────────────

class TestVehicleInactiveStatus:
    def test_supervisor_can_deactivate_vehicle(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}",
            json={"active": False, "inactive_reason": "Transmission failure — awaiting repair."},
            headers=auth_supervisor,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is False
        assert data["inactive_reason"] == "Transmission failure — awaiting repair."
        assert data["inactive_since"] is not None

    def test_deactivate_without_reason_returns_422(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}",
            json={"active": False},
            headers=auth_supervisor,
        )
        assert resp.status_code == 422

    def test_reactivate_clears_inactive_fields(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}",
            json={"active": False, "inactive_reason": "Annual inspection required."},
            headers=auth_supervisor,
        )
        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}",
            json={"active": True},
            headers=auth_supervisor,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is True
        assert data["inactive_reason"] is None
        assert data["inactive_since"] is None

    def test_responder_cannot_deactivate(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        resp = client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}",
            json={"active": False, "inactive_reason": "Responder trying to deactivate."},
            headers=auth_responder,
        )
        assert resp.status_code == 403

    def test_deactivate_creates_audit_event(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        client.patch(
            f"/api/v1/vehicles/{v.vehicle_id}",
            json={"active": False, "inactive_reason": "Scheduled maintenance window."},
            headers=auth_supervisor,
        )
        audit = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "VEHICLE_STATUS_CHANGED")
            .first()
        )
        assert audit is not None
