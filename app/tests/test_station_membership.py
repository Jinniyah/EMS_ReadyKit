"""
tests/test_station_membership.py
Session C (ACC-B7/B8) — Station membership enforcement tests.

These tests verify that non-Administrator users can only access data for
stations they are explicitly assigned to. Administrators bypass all
membership checks.

Fixtures:
  two_stations  — creates Station A and Station B plus one vehicle each
  member_db     — adds test-responder and test-supervisor to Station A only
                  (NOT Station B), then returns the station/vehicle IDs

Pattern:
  auth_responder / auth_supervisor hitting Station A endpoints → 200
  auth_responder / auth_supervisor hitting Station B endpoints → 403
  auth_admin hitting either station → 200 (bypass)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.vehicle import Vehicle, VehicleType


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def membership_setup(db: Session):
    """
    Creates two stations, one vehicle each.
    Assigns test-responder and test-supervisor to Station A only.

    Returns a dict with keys: station_a_id, station_b_id, vehicle_a_id, vehicle_b_id,
    location_a_id, location_b_id.
    """
    station_a = Station(name=f"Station-A-{_uid()}", address="1 Main St", region="R")
    station_b = Station(name=f"Station-B-{_uid()}", address="2 Main St", region="R")
    db.add_all([station_a, station_b])
    db.flush()

    # Vehicle + inventory location for A
    vehicle_a = Vehicle(
        station_id=station_a.station_id,
        vehicle_number=f"AMB-A-{_uid()}",
        vehicle_type=VehicleType.ALS,
    )
    db.add(vehicle_a)
    db.flush()
    loc_a = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station_a.station_id,
        vehicle_id=vehicle_a.vehicle_id,
        label=f"{vehicle_a.vehicle_number} — ALS",
    )
    db.add(loc_a)

    # Vehicle + inventory location for B
    vehicle_b = Vehicle(
        station_id=station_b.station_id,
        vehicle_number=f"AMB-B-{_uid()}",
        vehicle_type=VehicleType.ALS,
    )
    db.add(vehicle_b)
    db.flush()
    loc_b = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station_b.station_id,
        vehicle_id=vehicle_b.vehicle_id,
        label=f"{vehicle_b.vehicle_number} — ALS",
    )
    db.add(loc_b)
    db.flush()

    # Assign test-responder and test-supervisor to Station A only
    for user_email, role in [
        ("test-responder@ems.local",  "Responder"),
        ("test-supervisor@ems.local", "Supervisor"),
    ]:
        db.add(StationMember(
            station_id=station_a.station_id,
            user_id=user_email,
            role=role,
            assigned_by="test-administrator@ems.local",
            active=True,
        ))
    db.flush()

    return {
        "station_a_id":  station_a.station_id,
        "station_b_id":  station_b.station_id,
        "vehicle_a_id":  vehicle_a.vehicle_id,
        "vehicle_b_id":  vehicle_b.vehicle_id,
        "location_a_id": loc_a.location_id,
        "location_b_id": loc_b.location_id,
    }


# ── ACC-B7: Check submission enforcement ──────────────────────────────────────

class TestCheckMembershipEnforcement:

    def test_responder_can_submit_check_for_assigned_station(
        self, client, membership_setup, auth_responder
    ):
        sid = membership_setup["station_a_id"]
        vid = membership_setup["vehicle_a_id"]
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-01", "timestamp": _utcnow(),
        }, headers=auth_responder)
        assert response.status_code == 201

    def test_responder_cannot_submit_check_for_unassigned_station(
        self, client, membership_setup, auth_responder
    ):
        sid = membership_setup["station_b_id"]
        vid = membership_setup["vehicle_b_id"]
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-01", "timestamp": _utcnow(),
        }, headers=auth_responder)
        assert response.status_code == 403
        # Message should be human-readable
        assert "station" in response.json()["detail"].lower()
        assert "supervisor" in response.json()["detail"].lower()

    def test_supervisor_cannot_submit_check_for_unassigned_station(
        self, client, membership_setup, auth_supervisor
    ):
        sid = membership_setup["station_b_id"]
        vid = membership_setup["vehicle_b_id"]
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-01", "timestamp": _utcnow(),
        }, headers=auth_supervisor)
        assert response.status_code == 403

    def test_admin_can_submit_check_for_any_station(
        self, client, membership_setup, auth_admin
    ):
        """Administrator bypasses membership — can submit checks at any station."""
        sid = membership_setup["station_b_id"]
        vid = membership_setup["vehicle_b_id"]
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-01", "timestamp": _utcnow(),
        }, headers=auth_admin)
        assert response.status_code == 201

    def test_today_compliance_responder_can_access_assigned_station(
        self, client, membership_setup, auth_responder
    ):
        sid = membership_setup["station_a_id"]
        response = client.get(
            f"/api/v1/checks/daily/station/{sid}/today",
            headers=auth_responder,
        )
        assert response.status_code == 200

    def test_today_compliance_responder_cannot_access_unassigned_station(
        self, client, membership_setup, auth_responder
    ):
        sid = membership_setup["station_b_id"]
        response = client.get(
            f"/api/v1/checks/daily/station/{sid}/today",
            headers=auth_responder,
        )
        assert response.status_code == 403

    def test_vehicle_checks_responder_cannot_access_unassigned_station(
        self, client, membership_setup, auth_responder
    ):
        vid = membership_setup["vehicle_b_id"]
        response = client.get(
            f"/api/v1/checks/daily/vehicle/{vid}",
            headers=auth_responder,
        )
        assert response.status_code == 403


# ── ACC-B8: Vehicle endpoint enforcement ──────────────────────────────────────

class TestVehicleMembershipEnforcement:

    def test_responder_can_list_vehicles_for_assigned_station(
        self, client, membership_setup, auth_responder
    ):
        sid = membership_setup["station_a_id"]
        response = client.get(
            f"/api/v1/stations/{sid}/vehicles",
            headers=auth_responder,
        )
        assert response.status_code == 200

    def test_responder_cannot_list_vehicles_for_unassigned_station(
        self, client, membership_setup, auth_responder
    ):
        sid = membership_setup["station_b_id"]
        response = client.get(
            f"/api/v1/stations/{sid}/vehicles",
            headers=auth_responder,
        )
        assert response.status_code == 403
        assert "station" in response.json()["detail"].lower()

    def test_responder_can_get_vehicle_for_assigned_station(
        self, client, membership_setup, auth_responder
    ):
        vid = membership_setup["vehicle_a_id"]
        response = client.get(f"/api/v1/vehicles/{vid}", headers=auth_responder)
        assert response.status_code == 200

    def test_responder_cannot_get_vehicle_for_unassigned_station(
        self, client, membership_setup, auth_responder
    ):
        vid = membership_setup["vehicle_b_id"]
        response = client.get(f"/api/v1/vehicles/{vid}", headers=auth_responder)
        assert response.status_code == 403

    def test_admin_can_get_any_vehicle(
        self, client, membership_setup, auth_admin
    ):
        vid = membership_setup["vehicle_b_id"]
        response = client.get(f"/api/v1/vehicles/{vid}", headers=auth_admin)
        assert response.status_code == 200

    def test_supervisor_list_vehicles_filtered_to_their_stations(
        self, client, membership_setup, auth_supervisor
    ):
        """Supervisor's GET /vehicles returns only vehicles from their stations."""
        response = client.get("/api/v1/vehicles", headers=auth_supervisor)
        assert response.status_code == 200
        vehicle_ids = {v["vehicle_id"] for v in response.json()}
        # Station A vehicle should be included, Station B should not
        assert membership_setup["vehicle_a_id"] in vehicle_ids
        assert membership_setup["vehicle_b_id"] not in vehicle_ids

    def test_admin_list_vehicles_sees_all(
        self, client, membership_setup, auth_admin
    ):
        response = client.get("/api/v1/vehicles", headers=auth_admin)
        assert response.status_code == 200
        vehicle_ids = {v["vehicle_id"] for v in response.json()}
        assert membership_setup["vehicle_a_id"] in vehicle_ids
        assert membership_setup["vehicle_b_id"] in vehicle_ids


# ── ACC-B8: Inventory endpoint enforcement ────────────────────────────────────

class TestInventoryMembershipEnforcement:

    def test_responder_can_access_inventory_for_assigned_station(
        self, client, membership_setup, auth_responder
    ):
        loc_id = membership_setup["location_a_id"]
        response = client.get(
            f"/api/v1/inventory/locations/{loc_id}",
            headers=auth_responder,
        )
        assert response.status_code == 200

    def test_responder_cannot_access_inventory_for_unassigned_station(
        self, client, membership_setup, auth_responder
    ):
        loc_id = membership_setup["location_b_id"]
        response = client.get(
            f"/api/v1/inventory/locations/{loc_id}",
            headers=auth_responder,
        )
        assert response.status_code == 403
        assert "station" in response.json()["detail"].lower()

    def test_responder_can_list_locations_with_station_id(
        self, client, membership_setup, auth_responder
    ):
        sid = membership_setup["station_a_id"]
        response = client.get(
            f"/api/v1/inventory/locations?station_id={sid}",
            headers=auth_responder,
        )
        assert response.status_code == 200

    def test_responder_cannot_list_locations_without_station_id(
        self, client, membership_setup, auth_responder
    ):
        """Without station_id, only Administrators can list all locations."""
        response = client.get(
            "/api/v1/inventory/locations",
            headers=auth_responder,
        )
        assert response.status_code == 403

    def test_responder_cannot_list_locations_for_unassigned_station(
        self, client, membership_setup, auth_responder
    ):
        sid = membership_setup["station_b_id"]
        response = client.get(
            f"/api/v1/inventory/locations?station_id={sid}",
            headers=auth_responder,
        )
        assert response.status_code == 403

    def test_admin_can_list_all_locations_without_station_id(
        self, client, membership_setup, auth_admin
    ):
        response = client.get(
            "/api/v1/inventory/locations",
            headers=auth_admin,
        )
        assert response.status_code == 200

    def test_responder_can_list_compartments_for_assigned_station(
        self, client, membership_setup, auth_responder
    ):
        loc_id = membership_setup["location_a_id"]
        response = client.get(
            f"/api/v1/inventory/locations/{loc_id}/compartments",
            headers=auth_responder,
        )
        assert response.status_code == 200

    def test_responder_cannot_list_compartments_for_unassigned_station(
        self, client, membership_setup, auth_responder
    ):
        loc_id = membership_setup["location_b_id"]
        response = client.get(
            f"/api/v1/inventory/locations/{loc_id}/compartments",
            headers=auth_responder,
        )
        assert response.status_code == 403

    def test_admin_can_access_any_inventory_location(
        self, client, membership_setup, auth_admin
    ):
        loc_id = membership_setup["location_b_id"]
        response = client.get(
            f"/api/v1/inventory/locations/{loc_id}",
            headers=auth_admin,
        )
        assert response.status_code == 200


# ── Error message quality tests ───────────────────────────────────────────────

class TestMembershipErrorMessages:
    """
    Verify that 403 responses contain human-readable messages, not developer jargon.
    A tired EMS worker on a phone should be able to read and act on these messages.
    """

    def test_station_membership_403_mentions_supervisor(
        self, client, membership_setup, auth_responder
    ):
        """The message should tell the user who to contact."""
        sid = membership_setup["station_b_id"]
        vid = membership_setup["vehicle_b_id"]
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-01", "timestamp": _utcnow(),
        }, headers=auth_responder)
        detail = response.json()["detail"]
        assert "supervisor" in detail.lower(), (
            f"Error message should mention 'supervisor' so user knows who to contact. Got: {detail!r}"
        )

    def test_station_membership_403_mentions_station(
        self, client, membership_setup, auth_responder
    ):
        """The message should identify the problem (station access)."""
        loc_id = membership_setup["location_b_id"]
        response = client.get(
            f"/api/v1/inventory/locations/{loc_id}",
            headers=auth_responder,
        )
        detail = response.json()["detail"]
        assert "station" in detail.lower(), (
            f"Error message should mention 'station' to help user understand the issue. Got: {detail!r}"
        )

    def test_role_403_is_human_readable(
        self, client, auth_responder
    ):
        """Role-based 403 (not a membership issue) should also be clear."""
        response = client.post("/api/v1/stations", json={
            "name": f"S-{_uid()}", "address": "1 St", "region": "R",
        }, headers=auth_responder)
        assert response.status_code == 403
        detail = response.json()["detail"]
        # Should not be a raw technical string
        assert len(detail) > 20, f"Error message too short to be useful: {detail!r}"
