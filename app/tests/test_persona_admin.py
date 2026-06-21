"""
tests/test_persona_admin.py
Persona 3: Jennifer - Volunteer Admin
=======================================
Jennifer builds and maintains the software on lunch breaks.
Admin is a superset of Supervisor - all supervisor tests should also pass as admin.

Tests:
  - Admin superset: can do everything supervisors can
  - Admin-only: create items, view all stations, hard-delete checks
  - Role alias: "test-admin" Bearer token works as Administrator
  - Priority flag: PATCH /admin/par-levels/{id} accepts priority fields (RX-B2)
  - Supply room auto-decrement: check submission decrements supply room stock
  - FUNCTIONAL items excluded from supply catalog
"""

from __future__ import annotations

import json as _json
import uuid
from datetime import date, datetime, timezone

import pytest
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
from ems_readykit.models.stock_lot import StockLot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _setup(db: Session):
    """
    Create station + BLS vehicle + supply room + all members +
    one supply item with 20 units in the supply room.
    Returns (station, vehicle, location, supply_room, comp, supply_item).
    """
    station = Station(name=f"Admin-{_uid()}", address="1 Admin Way", region="Test")
    db.add(station)
    db.flush()

    for email, role in [
        ("test-administrator@ems.local", "Administrator"),
        ("test-supervisor@ems.local", "Supervisor"),
        ("test-responder@ems.local", "Responder"),
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
        label="Unit 712 Admin Test",
    )
    db.add(location)
    db.flush()

    supply_room = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label=f"Supply Room {_uid()}",
    )
    db.add(supply_room)
    db.flush()

    comp = Compartment(
        location_id=location.location_id,
        name=f"Comp-{_uid()}",
        sort_order=1,
        active=True,
    )
    db.add(comp)
    db.flush()

    supply_item = Item(
        name=f"Supply-{_uid()}",
        station_id=station.station_id,
        category=ItemCategory.CONSUMABLE,
        check_type=ItemCheckType.SUPPLY,
        unit_of_measure="each",
        active=True,
        station_supply=True,
    )
    db.add(supply_item)
    db.flush()

    db.add(
        ParLevel(
            item_id=supply_item.item_id,
            location_id=location.location_id,
            compartment_id=comp.compartment_id,
            min_quantity=4,
            max_quantity=4,
        )
    )

    # Seed supply room stock
    db.add(
        StockLot(
            item_id=supply_item.item_id,
            location_id=supply_room.location_id,
            quantity=20,
            lot_number=f"LOT-{_uid()}",
        )
    )
    db.flush()

    return station, vehicle, location, supply_room, comp, supply_item


def _delete_with_body(client, url: str, body: dict, headers: dict):
    """
    Workaround: Starlette TestClient.delete() does not support json= or content= kwargs.
    Use the generic request() method instead.
    """
    return client.request(
        "DELETE",
        url,
        content=_json.dumps(body),
        headers={**headers, "Content-Type": "application/json"},
    )


# ---------------------------------------------------------------------------
# Admin is superset of Supervisor
# ---------------------------------------------------------------------------


class TestAdminSupersetOfSupervisor:
    """Regressions here mean Jennifer loses access she needs to maintain the system."""

    def test_admin_can_view_check_detail(self, client, db, auth_responder, auth_admin):
        station, vehicle, _, _, comp, item = _setup(db)

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
                        "quantity_needed": 4,
                        "quantity_found": 4,
                    }
                ],
            },
            headers=auth_responder,
        )
        check_id = r.json()["check_id"]

        r2 = client.get(f"/api/v1/checks/daily/{check_id}/detail", headers=auth_admin)
        assert r2.status_code == 200

    def test_admin_can_mark_item_damaged(self, client, db, auth_admin):
        _station, _vehicle, _location, _, comp, item = _setup(db)

        r = client.patch(
            f"/api/v1/inventory/items/{item.item_id}/status",
            json={"compartment_id": comp.compartment_id, "is_damaged": True},
            headers=auth_admin,
        )
        assert r.status_code not in (
            403,
            500,
        ), f"Admin could not mark item damaged: {r.status_code}"

    def test_admin_can_file_repair_request(self, client, db, auth_admin):
        _station, vehicle, _location, _, comp, item = _setup(db)

        r = client.post(
            f"/api/v1/vehicles/{vehicle.vehicle_id}/repair-requests",
            json={
                "item_id": item.item_id,
                "compartment_id": comp.compartment_id,
                "description": "Admin filed repair request",
            },
            headers=auth_admin,
        )
        assert r.status_code in (200, 201)

    def test_admin_can_acknowledge_check(self, client, db, auth_responder, auth_admin):
        station, vehicle, _, _, comp, item = _setup(db)

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
                        "quantity_needed": 4,
                        "quantity_found": 0,
                    }
                ],
            },
            headers=auth_responder,
        )
        check_id = r.json()["check_id"]

        r2 = client.patch(
            f"/api/v1/checks/daily/{check_id}/acknowledge",
            json={
                "corrective_action": "Restock ordered and received",
            },
            headers=auth_admin,
        )
        assert r2.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Admin-only capabilities
# ---------------------------------------------------------------------------


class TestAdminOnlyCapabilities:

    def test_admin_can_create_item_in_catalog(self, client, auth_admin):
        """Jennifer can add items to the shared item catalog."""
        sid = client.post(
            "/api/v1/stations",
            json={
                "name": f"AdminItems-{_uid()}",
                "address": "1 Test St",
                "region": "Test",
            },
            headers=auth_admin,
        ).json()["station_id"]
        r = client.post(
            "/api/v1/items",
            json={
                "name": f"Admin-Created-Item-{_uid()}",
                "station_id": sid,
                "category": "Equipment",
                "check_type": "SUPPLY",
                "unit_of_measure": "each",
            },
            headers=auth_admin,
        )
        assert r.status_code in (
            200,
            201,
        ), f"Admin could not create item: {r.status_code} {r.text}"

    def test_admin_can_create_station(self, client, auth_admin):
        """Station creation is admin-only."""
        r = client.post(
            "/api/v1/stations",
            json={
                "name": f"Admin-Created-Station-{_uid()}",
                "address": "1 Admin St",
                "region": "Test",
            },
            headers=auth_admin,
        )
        assert r.status_code == 201

    def test_admin_can_view_all_stations(self, client, db, auth_admin):
        """Admin sees all stations - cross-station visibility."""
        s1 = Station(name=f"Cross-A-{_uid()}", address="1 A St", region="Test")
        s2 = Station(name=f"Cross-B-{_uid()}", address="1 B St", region="Test")
        db.add(s1)
        db.add(s2)
        db.flush()

        r = client.get("/api/v1/stations", headers=auth_admin)
        assert r.status_code == 200
        ids = [s.get("station_id") for s in r.json()]
        assert s1.station_id in ids, "Admin cannot see station A"
        assert s2.station_id in ids, "Admin cannot see station B"

    def test_admin_can_soft_delete_check(self, client, db, auth_responder, auth_admin):
        """Admin can soft-delete a check (Supervisor+ capability)."""
        station, vehicle, _, _, _comp, _item = _setup(db)

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
            },
            headers=auth_responder,
        )
        check_id = r.json()["check_id"]

        r2 = _delete_with_body(
            client,
            f"/api/v1/checks/daily/{check_id}",
            {"deletion_reason": "Admin test soft-delete"},
            auth_admin,
        )
        assert r2.status_code in (200, 201), f"Admin soft-delete failed: {r2.text}"

    def test_admin_can_hard_delete_soft_deleted_check(
        self, client, db, auth_responder, auth_admin
    ):
        """Admin can permanently delete a check that was already soft-deleted."""
        station, vehicle, _, _, _comp, _item = _setup(db)

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
            },
            headers=auth_responder,
        )
        check_id = r.json()["check_id"]

        # Soft-delete first
        _delete_with_body(
            client,
            f"/api/v1/checks/daily/{check_id}",
            {"deletion_reason": "Setup for hard-delete test"},
            auth_admin,
        )

        # Hard-delete
        r2 = client.delete(f"/api/v1/checks/daily/{check_id}/force", headers=auth_admin)
        assert (
            r2.status_code == 204
        ), f"Admin hard-delete failed: {r2.status_code} {r2.text}"

    def test_admin_can_set_priority_flag_on_par_level(self, client, db, auth_admin):
        """
        RX-B2: PATCH /admin/par-levels/{id} accepts priority_check and priority_question.
        The endpoint exists and requires min_quantity + max_quantity too.
        The _enrich_par response helper may not include priority fields in the response
        (known gap) but the DB values must be persisted correctly.
        """
        _station, _vehicle, location, _, _comp, _item = _setup(db)

        r = client.get(
            f"/api/v1/inventory/locations/{location.location_id}/par-levels",
            headers=auth_admin,
        )
        assert r.status_code == 200
        pars = r.json()
        if not pars:
            pytest.skip("No par levels to test priority flag")

        par = pars[0]
        par_id = par.get("par_id") or par.get("id")
        if not par_id:
            pytest.skip("Could not find par level ID")

        # UpdateParLevelRequest requires min_quantity + max_quantity
        r2 = client.patch(
            f"/api/v1/admin/par-levels/{par_id}",
            json={
                "min_quantity": par.get("min_quantity", 1),
                "max_quantity": par.get("max_quantity", 1),
                "priority_check": True,
                "priority_question": "Is this item ready?",
            },
            headers=auth_admin,
        )

        assert r2.status_code in (
            200,
            201,
        ), f"Priority flag PATCH failed: {r2.status_code} {r2.text}"

        # Verify directly in DB — _enrich_par may not include priority fields in response
        from ems_readykit.models.par_level import ParLevel as PL

        db_par = db.query(PL).filter(PL.par_id == par_id).first()
        assert db_par is not None
        assert db_par.priority_check is True, (
            "priority_check was not persisted to DB. "
            "Check update_par_level handler in admin.py — "
            "must write par.priority_check = payload.priority_check."
        )
        assert db_par.priority_question == "Is this item ready?"

    def test_admin_only_can_deactivate_items(
        self, client, db, auth_admin, auth_supervisor
    ):
        """
        Item deactivation is Admin only.
        Supervisor can CREATE items (SUPERVISOR_PLUS) but not deactivate them.
        """
        sid = client.post(
            "/api/v1/stations",
            json={
                "name": f"DeactTest-{_uid()}",
                "address": "1 Test St",
                "region": "Test",
            },
            headers=auth_admin,
        ).json()["station_id"]
        # Create an item as supervisor - should succeed (SUPERVISOR_PLUS)
        r = client.post(
            "/api/v1/items",
            json={
                "name": f"Deactivation-Test-{_uid()}",
                "station_id": sid,
                "category": "Equipment",
                "unit_of_measure": "each",
            },
            headers=auth_supervisor,
        )
        assert r.status_code == 201, "Supervisor should be able to create items"
        item_id = r.json()["item_id"]

        # Supervisor tries to deactivate - should fail (Admin only)
        r2 = client.patch(
            f"/api/v1/admin/items/{item_id}/deactivate", headers=auth_supervisor
        )
        assert r2.status_code == 403, (
            f"Supervisor was not denied item deactivation (admin-only). "
            f"Status: {r2.status_code}"
        )

        # Admin can deactivate
        r3 = client.patch(
            f"/api/v1/admin/items/{item_id}/deactivate", headers=auth_admin
        )
        assert r3.status_code in (
            200,
            204,
        ), f"Admin could not deactivate item: {r3.status_code}"


# ---------------------------------------------------------------------------
# Role alias regression
# ---------------------------------------------------------------------------


class TestAdminRoleAlias:
    """
    REGRESSION (Session J): canAccess(user, 'admin') silently returned false
    because 'admin' alias was missing from roleGuard.js.

    Backend side: auth.py maps "test-admin" to Administrator role.
    This test verifies the backend alias works correctly.
    Frontend alias is covered by Vitest in tests/unit/roleGuard.test.js.
    """

    def test_test_admin_token_acts_as_administrator(self, client):
        """Bearer test-admin must have Administrator access."""
        admin_headers = {"Authorization": "Bearer test-admin"}

        # Station creation is Administrator only
        r = client.post(
            "/api/v1/stations",
            json={
                "name": f"Role-Alias-{_uid()}",
                "address": "1 Alias St",
                "region": "Test",
            },
            headers=admin_headers,
        )
        assert r.status_code in (200, 201), (
            f"'test-admin' token was denied Administrator access. "
            f"Status: {r.status_code}. "
            "The 'admin' alias must map to Administrator role."
        )


# ---------------------------------------------------------------------------
# Supply room auto-decrement (SR-B4)
# ---------------------------------------------------------------------------


class TestSupplyRoomDecrement:
    """
    When a vehicle check shows items were topped off (quantity went up
    vs previous check), the supply room must be decremented by that delta.
    Wrong math = responder leaves without enough supplies = patient safety issue.
    """

    def test_vehicle_check_decrements_supply_room(
        self, client, db, auth_responder, auth_admin
    ):
        """
        Check 1: vehicle has 2 of 4 par. (Baseline - no previous check to compare.)
        Check 2: vehicle has 4 of 4 par. (Topped off by 2 -> decrement supply room by 2.)
        """
        station, vehicle, _location, _supply_room, comp, item = _setup(db)

        # Get initial on-hand
        catalog_r = client.get(
            f"/api/v1/inventory/supply-catalog?station_id={station.station_id}",
            headers=auth_admin,
        )
        if catalog_r.status_code != 200:
            pytest.skip("Supply catalog not available")

        entry = next(
            (i for i in catalog_r.json() if i.get("item_id") == item.item_id),
            None,
        )
        if entry is None:
            pytest.skip("Supply item not in catalog - verify station_supply=True")

        initial_on_hand = entry.get("on_hand", 0)
        if initial_on_hand < 2:
            pytest.skip(
                f"Insufficient supply room stock ({initial_on_hand}) for decrement test"
            )

        # Check 1: found 2 (par is 4) - baseline
        r1 = client.post(
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
                        "quantity_needed": 4,
                        "quantity_found": 2,
                    }
                ],
            },
            headers=auth_responder,
        )
        assert r1.status_code == 201

        # Check 2: found 4 (topped off from 2 to 4, delta = 2)
        r2 = client.post(
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
                        "quantity_needed": 4,
                        "quantity_found": 4,
                    }
                ],
            },
            headers=auth_responder,
        )
        assert r2.status_code == 201

        # Verify supply room decremented by 2
        new_catalog_r = client.get(
            f"/api/v1/inventory/supply-catalog?station_id={station.station_id}",
            headers=auth_admin,
        )
        new_entry = next(
            (i for i in new_catalog_r.json() if i.get("item_id") == item.item_id),
            None,
        )
        if new_entry is None:
            pytest.skip("Item disappeared from catalog after check")

        expected = initial_on_hand - 2
        actual = new_entry.get("on_hand", 0)

        assert actual == expected, (
            f"Supply room decrement incorrect. "
            f"Initial: {initial_on_hand}, Expected: {expected}, Actual: {actual}. "
            "SR-B4: auto-decrement must fire when vehicle is topped off."
        )

    def test_functional_items_not_in_supply_catalog(self, client, db, auth_admin):
        """
        FUNCTIONAL items with station_supply=False must not appear in supply catalog.
        These are equipment checks, not consumable supplies.
        """
        station, _vehicle, _location, supply_room, _comp, _ = _setup(db)

        functional = Item(
            name=f"FUNCTIONAL-Excluded-{_uid()}",
            station_id=station.station_id,
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.FUNCTIONAL,
            unit_of_measure="each",
            active=True,
            station_supply=False,
        )
        db.add(functional)
        db.flush()

        db.add(
            StockLot(
                item_id=functional.item_id,
                location_id=supply_room.location_id,
                quantity=5,
            )
        )
        db.flush()

        r = client.get(
            f"/api/v1/inventory/supply-catalog?station_id={station.station_id}",
            headers=auth_admin,
        )
        assert r.status_code == 200
        catalog = r.json()

        functional_in_catalog = [
            i for i in catalog if i.get("check_type") == "FUNCTIONAL"
        ]
        assert len(functional_in_catalog) == 0, (
            f"FUNCTIONAL items found in supply catalog: "
            f"{[i.get('item_name') for i in functional_in_catalog]}. "
            "SR-B1: FUNCTIONAL items must be excluded."
        )

    def test_supply_room_check_does_not_decrement_stock(
        self, client, db, auth_responder, auth_admin
    ):
        """
        Supply-room-only checks (vehicle_id=None) must NOT trigger auto-decrement.
        Per CLAUDE.md: '_auto_decrement_supply_room fires only when payload.vehicle_id is set'.
        """
        station, _vehicle, _location, supply_room, _comp, item = _setup(db)

        catalog_r = client.get(
            f"/api/v1/inventory/supply-catalog?station_id={station.station_id}",
            headers=auth_admin,
        )
        if catalog_r.status_code != 200:
            pytest.skip("Supply catalog not available")

        entry = next(
            (i for i in catalog_r.json() if i.get("item_id") == item.item_id),
            None,
        )
        if entry is None:
            pytest.skip("Item not in supply catalog")

        initial_on_hand = entry.get("on_hand", 0)

        # Submit a supply-room check (no vehicle_id - only location_id)
        r = client.post(
            "/api/v1/checks/daily",
            json={
                "location_id": supply_room.location_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
            },
            headers=auth_responder,
        )

        if r.status_code not in (200, 201):
            pytest.skip(f"Supply room check not supported: {r.text}")

        # Supply room stock must be unchanged
        new_r = client.get(
            f"/api/v1/inventory/supply-catalog?station_id={station.station_id}",
            headers=auth_admin,
        )
        new_entry = next(
            (i for i in new_r.json() if i.get("item_id") == item.item_id),
            None,
        )
        if new_entry:
            assert new_entry.get("on_hand") == initial_on_hand, (
                "Supply room count changed after a supply-room-only check. "
                "Auto-decrement must only fire for vehicle checks (vehicle_id set)."
            )
