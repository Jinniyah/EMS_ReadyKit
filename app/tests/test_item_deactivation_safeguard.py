"""
tests/test_item_deactivation_safeguard.py
ONBOARD-2 -- deactivate_item blocks with 409 while the item still has any
active ParLevel assignment (a vehicle, jump bag, or supply room, possibly at
another station), instead of silently pulling it out of a crew's check
wizard. See admin_items.py's module docstring / SAFEGUARD comment for the
full incident description.

Uses the same direct-ORM fixture pattern as test_par_level_reactivation.py
(Vehicle/InventoryLocation/Compartment built via `db`, not the admin CRUD
routes) since these tests are about the par-level <-> deactivate interaction,
not about vehicle/compartment creation itself. `compartment` and `test_item`
are named per-test (request.node.name) rather than get-or-create: route
handlers here call db.commit(), which releases the SAVEPOINT (see CLAUDE.md),
so a shared item/compartment would carry an already-deactivated or
already-assigned state across tests in this file.
"""

from __future__ import annotations

import uuid

import pytest

from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item, ItemCategory, ItemCheckType
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.vehicle import Vehicle, VehicleType

ADMIN = "/api/v1/admin"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def station(db, request):
    s = Station(
        name=f"ONBOARD-2 Station [{request.node.name}]",
        address="1 Test Way",
        region="Test",
        active=True,
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def other_station(db, request):
    """A second, distinct station -- used for the cross-station block test."""
    s = Station(
        name=f"ONBOARD-2 Other Station [{request.node.name}]",
        address="2 Test Way",
        region="Test",
        active=True,
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def membership(db, station):
    db.add(
        StationMember(
            station_id=station.station_id,
            user_id="test-supervisor@ems.local",
            role="Supervisor",
            assigned_by="test",
            active=True,
        )
    )
    db.flush()


def _vehicle_location(db, station, suffix):
    v = Vehicle(
        station_id=station.station_id,
        vehicle_number=f"ONBOARD2-{uuid.uuid4().hex[:8]}",
        vehicle_type=VehicleType.BLS,
        active=True,
    )
    db.add(v)
    db.flush()
    loc = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station.station_id,
        vehicle_id=v.vehicle_id,
        label=f"Unit ONBOARD2-{suffix}",
    )
    db.add(loc)
    db.flush()
    return v, loc


@pytest.fixture
def vehicle_location(db, station, request):
    _, loc = _vehicle_location(db, station, request.node.name[:20])
    return loc


@pytest.fixture
def compartment(db, vehicle_location, request):
    comp = Compartment(
        location_id=vehicle_location.location_id,
        name=f"ONBOARD-2 Compartment [{request.node.name}]",
        sort_order=1,
        active=True,
    )
    db.add(comp)
    db.flush()
    return comp


@pytest.fixture
def test_item(db, station, request):
    item = Item(
        name=f"ONBOARD-2 Test Item [{request.node.name}]",
        station_id=station.station_id,
        category=ItemCategory.CONSUMABLE,
        check_type=ItemCheckType.SUPPLY,
        unit_of_measure="each",
        active=True,
    )
    db.add(item)
    db.flush()
    return item


def _assign(client, auth, item_id, vehicle_id, compartment_id, min_q=1, max_q=4):
    return client.post(
        f"{ADMIN}/items/{item_id}/assign",
        json={
            "vehicle_id": vehicle_id,
            "compartment_id": compartment_id,
            "min_quantity": min_q,
            "max_quantity": max_q,
        },
        headers=auth,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDeactivationSafeguard:

    def test_deactivate_blocked_when_active_par_level_exists(
        self,
        client,
        db,
        station,
        vehicle_location,
        compartment,
        test_item,
        membership,
        auth_admin,
    ):
        r = _assign(
            client,
            auth_admin,
            test_item.item_id,
            vehicle_location.vehicle_id,
            compartment.compartment_id,
        )
        assert r.status_code == 201

        resp = client.patch(
            f"{ADMIN}/items/{test_item.item_id}/deactivate", headers=auth_admin
        )
        assert resp.status_code == 409

        db.expire_all()
        item = db.query(Item).filter(Item.item_id == test_item.item_id).first()
        assert item.active is True

    def test_deactivate_succeeds_after_par_level_removed(
        self,
        client,
        db,
        station,
        vehicle_location,
        compartment,
        test_item,
        membership,
        auth_admin,
    ):
        r = _assign(
            client,
            auth_admin,
            test_item.item_id,
            vehicle_location.vehicle_id,
            compartment.compartment_id,
        )
        par_id = r.json()["par_id"]

        remove = client.patch(
            f"{ADMIN}/par-levels/{par_id}/deactivate",
            json={"reason": "No longer stocked"},
            headers=auth_admin,
        )
        assert remove.status_code == 204

        resp = client.patch(
            f"{ADMIN}/items/{test_item.item_id}/deactivate", headers=auth_admin
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    def test_deactivate_blocked_message_is_singular_for_one_assignment(
        self,
        client,
        db,
        station,
        vehicle_location,
        compartment,
        test_item,
        membership,
        auth_admin,
    ):
        _assign(
            client,
            auth_admin,
            test_item.item_id,
            vehicle_location.vehicle_id,
            compartment.compartment_id,
        )

        resp = client.patch(
            f"{ADMIN}/items/{test_item.item_id}/deactivate", headers=auth_admin
        )
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert "1 location" in detail
        assert "1 locations" not in detail

    def test_deactivate_still_blocked_when_assignment_is_at_another_station(
        self,
        client,
        db,
        station,
        other_station,
        test_item,
        membership,
        auth_admin,
        request,
    ):
        # Item belongs to `station`; assign it to a compartment on a vehicle
        # at a completely different station. Admins bypass station
        # membership, so this is a legal (if unusual) admin action.
        other_vehicle, other_loc = _vehicle_location(
            db, other_station, request.node.name[:20]
        )
        other_comp = Compartment(
            location_id=other_loc.location_id,
            name=f"Other Station Compartment [{request.node.name}]",
            sort_order=1,
            active=True,
        )
        db.add(other_comp)
        db.flush()

        r = _assign(
            client,
            auth_admin,
            test_item.item_id,
            other_vehicle.vehicle_id,
            other_comp.compartment_id,
        )
        assert r.status_code == 201

        resp = client.patch(
            f"{ADMIN}/items/{test_item.item_id}/deactivate", headers=auth_admin
        )
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        # Deliberately generic -- must not name the other station, since the
        # caller may have no visibility into it.
        assert other_station.name not in detail
        assert "1 location" in detail

    def test_assignment_count_agrees_with_deactivate_guard(
        self,
        client,
        db,
        station,
        vehicle_location,
        compartment,
        test_item,
        membership,
        auth_admin,
    ):
        _assign(
            client,
            auth_admin,
            test_item.item_id,
            vehicle_location.vehicle_id,
            compartment.compartment_id,
        )

        count_resp = client.get(
            f"{ADMIN}/items/{test_item.item_id}/assignments/count", headers=auth_admin
        )
        assert count_resp.status_code == 200
        count = count_resp.json()["count"]
        assert count == 1

        deactivate_resp = client.patch(
            f"{ADMIN}/items/{test_item.item_id}/deactivate", headers=auth_admin
        )
        assert deactivate_resp.status_code == 409
        assert f"{count} location" in deactivate_resp.json()["detail"]
