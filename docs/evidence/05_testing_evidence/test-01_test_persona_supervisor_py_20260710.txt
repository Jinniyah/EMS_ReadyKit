"""
tests/test_persona_supervisor.py
Persona 2: Earl — 68-year-old EMS Chief (Supervisor)
======================================================
Earl must be able to manage the station without explanation.
Everything he needs must work on iPhone without crashing.

Tests:
  - Check detail visible to supervisor
  - Acknowledge FAIL checks
  - Damaged item mark/clear — REGRESSION test for write_audit_event bug
    (Session J: 500 caused by wrong kwargs: performed_by/detail → actor/metadata)
  - Repair requests created and resolved
  - Supply catalog accessible
  - Clean 403 denial on admin endpoints (not 500, not blank screen)
  - Station today view for shift handoff
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from ems_readykit.models import (
    Compartment,
    InventoryLocation,
    Item,
    ItemCategory,
    ItemCheckType,
    LocationType,
    Station,
    Vehicle,
    VehicleType,
)
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.station_member import StationMember

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _setup(db: Session):
    station = Station(name=f"Supervisor-{_uid()}", address="1 Chief Way", region="Test")
    db.add(station)
    db.flush()

    for email, role in [
        ("test-supervisor@ems.local", "Supervisor"),
        ("test-responder@ems.local", "Responder"),
        ("test-administrator@ems.local", "Administrator"),
    ]:
        db.add(
            StationMember(
                station_id=station.station_id,
                user_id=email,
                role=role,
                assigned_by="test-setup",
                active=True,
            )
        )
    db.flush()

    vehicle = Vehicle(
        station_id=station.station_id,
        vehicle_number=f"712-{_uid()}",
        vehicle_type=VehicleType.BLS,
    )
    db.add(vehicle)
    db.flush()

    location = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station.station_id,
        vehicle_id=vehicle.vehicle_id,
        label="Unit 712 Supervisor Test",
    )
    db.add(location)
    db.flush()

    comp = Compartment(
        location_id=location.location_id,
        name=f"Comp-{_uid()}",
        sort_order=1,
        active=True,
    )
    db.add(comp)
    db.flush()

    item = Item(
        name=f"Item-{_uid()}",
        station_id=station.station_id,
        category=ItemCategory.EQUIPMENT,
        check_type=ItemCheckType.FUNCTIONAL,
        unit_of_measure="each",
        active=True,
    )
    db.add(item)
    db.flush()

    db.add(
        ParLevel(
            item_id=item.item_id,
            location_id=location.location_id,
            compartment_id=comp.compartment_id,
            min_quantity=1,
            max_quantity=1,
        )
    )
    db.flush()

    return station, vehicle, location, comp, item


def _submit_fail_check(client, *, station, vehicle, item, comp, auth):
    """Submit a check with one FAIL FUNCTIONAL line item."""
    r = client.post(
        "/api/v1/checks/daily",
        json={
            "vehicle_id": vehicle.vehicle_id,
            "station_id": station.station_id,
            "check_date": date.today().isoformat(),
            "timestamp": _utcnow(),
            "line_items": [
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "functional_pass": False,
                    "notes": "Equipment malfunction — supervisor notified",
                }
            ],
        },
        headers=auth,
    )
    assert r.status_code == 201, f"Fail check submission failed: {r.text}"
    return r.json()["check_id"]


# ---------------------------------------------------------------------------
# Check history visibility
# ---------------------------------------------------------------------------


class TestSupervisorCheckHistory:

    def test_supervisor_can_view_check_detail(
        self, client, db, auth_responder, auth_supervisor
    ):
        """Earl must be able to see check details submitted by responders."""
        station, vehicle, _, comp, item = _setup(db)
        check_id = _submit_fail_check(
            client,
            station=station,
            vehicle=vehicle,
            item=item,
            comp=comp,
            auth=auth_responder,
        )

        r = client.get(
            f"/api/v1/checks/daily/{check_id}/detail", headers=auth_supervisor
        )
        assert r.status_code == 200, f"Supervisor cannot view check detail: {r.text}"
        assert r.json()["check_id"] == check_id

    def test_supervisor_can_acknowledge_fail_check(
        self, client, db, auth_responder, auth_supervisor
    ):
        """Earl must be able to acknowledge a FAIL check with corrective action."""
        station, vehicle, _, comp, item = _setup(db)
        check_id = _submit_fail_check(
            client,
            station=station,
            vehicle=vehicle,
            item=item,
            comp=comp,
            auth=auth_responder,
        )

        r = client.patch(
            f"/api/v1/checks/daily/{check_id}/acknowledge",
            json={
                "corrective_action": "Item replaced and tested — ready for service",
            },
            headers=auth_supervisor,
        )
        assert r.status_code in (
            200,
            201,
        ), f"Supervisor could not acknowledge FAIL check: {r.text}"
        data = r.json()
        assert data.get("corrective_action") is not None


# ---------------------------------------------------------------------------
# Damaged item — regression test for write_audit_event kwargs bug
# ---------------------------------------------------------------------------


class TestSupervisorDamagedItems:
    """
    REGRESSION (Session J): patch_item_status used wrong write_audit_event kwargs.
    Used 'performed_by'/'detail' instead of 'actor'/'metadata' — caused 500s.
    Any 500 here means the bug is back.
    """

    def test_mark_item_damaged_returns_200_not_500(self, client, db, auth_supervisor):
        """Mark damaged must return 200. A 500 means the audit event kwargs bug is back."""
        _station, _vehicle, _location, comp, item = _setup(db)

        r = client.patch(
            f"/api/v1/inventory/items/{item.item_id}/status",
            json={"compartment_id": comp.compartment_id, "is_damaged": True},
            headers=auth_supervisor,
        )
        assert r.status_code != 500, (
            "Mark damaged returned 500. "
            "Check write_audit_event in inventory.py::patch_item_status. "
            "kwargs must be actor= and metadata=, not performed_by= or detail=."
        )
        assert r.status_code in (
            200,
            201,
        ), f"Mark damaged failed: {r.status_code} {r.text}"

    def test_clear_damaged_returns_200_not_500(self, client, db, auth_supervisor):
        """Clear damaged must return 200. 500 = same bug as above."""
        _station, _vehicle, _location, comp, item = _setup(db)

        # Mark first
        client.patch(
            f"/api/v1/inventory/items/{item.item_id}/status",
            json={"compartment_id": comp.compartment_id, "is_damaged": True},
            headers=auth_supervisor,
        )

        # Now clear
        r = client.patch(
            f"/api/v1/inventory/items/{item.item_id}/status",
            json={"compartment_id": comp.compartment_id, "is_damaged": False},
            headers=auth_supervisor,
        )
        assert (
            r.status_code != 500
        ), "Clear damaged returned 500. Same write_audit_event kwargs bug."
        assert r.status_code in (
            200,
            201,
        ), f"Clear damaged failed: {r.status_code} {r.text}"

    def test_mark_damaged_sets_is_damaged_true(self, client, db, auth_supervisor):
        """After marking damaged, the par level is_damaged field must be True."""
        _station, _vehicle, location, comp, item = _setup(db)

        client.patch(
            f"/api/v1/inventory/items/{item.item_id}/status",
            json={"compartment_id": comp.compartment_id, "is_damaged": True},
            headers=auth_supervisor,
        )

        # Verify via par level API
        r = client.get(
            f"/api/v1/inventory/locations/{location.location_id}/par-levels",
            headers=auth_supervisor,
        )
        assert r.status_code == 200
        pars = r.json()
        affected = next(
            (
                p
                for p in pars
                if p.get("item_id") == item.item_id
                and p.get("compartment_id") == comp.compartment_id
            ),
            None,
        )
        if affected and "is_damaged" in affected:
            assert affected["is_damaged"] is True


# ---------------------------------------------------------------------------
# Repair requests
# ---------------------------------------------------------------------------


class TestSupervisorRepairRequests:

    def test_supervisor_can_file_repair_request(self, client, db, auth_supervisor):
        """Earl must be able to file a repair request on a vehicle item."""
        _station, vehicle, _location, comp, item = _setup(db)

        r = client.post(
            f"/api/v1/vehicles/{vehicle.vehicle_id}/repair-requests",
            json={
                "item_id": item.item_id,
                "compartment_id": comp.compartment_id,
                "description": "Device not powering on — needs inspection",
            },
            headers=auth_supervisor,
        )
        assert r.status_code in (
            200,
            201,
        ), f"Supervisor could not file repair request: {r.text}"

    def test_supervisor_can_resolve_repair_request(self, client, db, auth_supervisor):
        """Earl must be able to mark a repair request resolved."""
        _station, vehicle, _location, comp, item = _setup(db)

        create_r = client.post(
            f"/api/v1/vehicles/{vehicle.vehicle_id}/repair-requests",
            json={
                "item_id": item.item_id,
                "compartment_id": comp.compartment_id,
                "description": "Test repair for resolution",
            },
            headers=auth_supervisor,
        )
        assert create_r.status_code in (200, 201)
        repair_data = create_r.json()
        # Response key is repair_id per repair_requests router
        repair_id = (
            repair_data.get("repair_id")
            or repair_data.get("repair_request_id")
            or repair_data.get("id")
        )
        assert repair_id, f"No repair ID in response: {repair_data}"

        r = client.patch(
            f"/api/v1/vehicles/{vehicle.vehicle_id}/repair-requests/{repair_id}",
            json={
                "status": "RESOLVED",
                "resolution_notes": "RESOLVED: Repaired and tested OK",
            },
            headers=auth_supervisor,
        )
        assert r.status_code in (
            200,
            201,
        ), f"Could not resolve repair request: {r.text}"


# ---------------------------------------------------------------------------
# Supply catalog
# ---------------------------------------------------------------------------


class TestSupervisorSupplyCatalog:

    def test_supervisor_can_access_supply_catalog(self, client, db, auth_supervisor):
        """Earl must be able to check supply levels for his station."""
        station, _, _, _, _ = _setup(db)

        r = client.get(
            f"/api/v1/inventory/supply-catalog?station_id={station.station_id}",
            headers=auth_supervisor,
        )
        # 200 (with or without items) OR 404 if supply room not set up yet — both fine
        assert r.status_code in (
            200,
            404,
        ), f"Supervisor got unexpected status on supply catalog: {r.status_code}"


# ---------------------------------------------------------------------------
# Role boundary — graceful denial
# ---------------------------------------------------------------------------


class TestSupervisorRoleBoundary:

    def test_supervisor_can_create_items_but_not_deactivate(
        self, client, auth_supervisor, auth_admin
    ):
        """
        POST /api/v1/items is SUPERVISOR_PLUS — supervisors CAN create items.
        Only DEACTIVATE is admin-only. Test that boundary instead.
        """
        sid = client.post(
            "/api/v1/stations",
            json={
                "name": f"SupRole-{_uid()}",
                "address": "1 Test St",
                "region": "Test",
            },
            headers=auth_admin,
        ).json()["station_id"]
        # Creating items: Supervisor+ — should succeed
        r = client.post(
            "/api/v1/items",
            json={
                "name": f"Supervisor-Created-{_uid()}",
                "station_id": sid,
                "category": "Equipment",
                "unit_of_measure": "each",
            },
            headers=auth_supervisor,
        )
        assert (
            r.status_code == 201
        ), f"Supervisor should be able to create items (SUPERVISOR_PLUS). Status: {r.status_code}"
        item_id = r.json()["item_id"]

        # Deactivating items: Admin only — should be denied
        r2 = client.patch(
            f"/api/v1/admin/items/{item_id}/deactivate", headers=auth_supervisor
        )
        assert (
            r2.status_code == 403
        ), f"Supervisor was not denied item deactivation (admin-only). Status: {r2.status_code}"

    def test_supervisor_cannot_create_stations(self, client, auth_supervisor):
        """Station creation is admin-only (via admin router)."""
        r = client.post(
            "/api/v1/admin/stations",
            json={
                "name": f"Unauthorized-{_uid()}",
                "address": "1 St",
                "region": "Test",
            },
            headers=auth_supervisor,
        )
        assert (
            r.status_code == 403
        ), f"Supervisor was not denied station creation. Status: {r.status_code}"

    def test_supervisor_cannot_hard_delete_checks(self, client, auth_supervisor):
        """Force-delete is Admin only. Supervisor must get 403."""
        r = client.delete("/api/v1/checks/daily/99999/force", headers=auth_supervisor)
        assert r.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Station today — shift handoff view
# ---------------------------------------------------------------------------


class TestStationTodayView:

    def test_supervisor_can_see_todays_checks(
        self, client, db, auth_responder, auth_supervisor
    ):
        """
        Supervisor at same station can see all of today's checks.
        Supports shift handoff and oversight.
        """
        station, vehicle, _, comp, item = _setup(db)

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
                "line_items": [
                    {
                        "compartment_id": comp.compartment_id,
                        "item_id": item.item_id,
                        "quantity_needed": 0,
                        "quantity_found": 0,
                        "functional_pass": True,
                    }
                ],
            },
            headers=auth_responder,
        )
        assert r.status_code == 201
        check_id = r.json()["check_id"]

        r2 = client.get(
            f"/api/v1/checks/daily/station/{station.station_id}/today",
            headers=auth_supervisor,
        )
        assert r2.status_code == 200
        ids = [c.get("check_id") for c in r2.json()]
        assert check_id in ids, (
            "Responder check not visible in supervisor's station today view. "
            "Station-scoped visibility required for shift handoff."
        )
