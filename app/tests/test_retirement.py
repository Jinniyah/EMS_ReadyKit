"""
tests/test_retirement.py
Integration tests for vehicle, location, station, and stock lot retirement.
Covers RET-B1 through RET-B6.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item, ItemCategory, ItemCheckType
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.models.vehicle import Vehicle, VehicleType

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def station(db):
    s = Station(name="Test Station", address="1 Main St", region="Test", active=True)
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def admin_member(db, station):
    m = StationMember(
        station_id=station.station_id,
        user_id="test-administrator@ems.local",
        role="Administrator",
        active=True,
        assigned_by="test-administrator@ems.local",
        assigned_at=datetime.now(timezone.utc),
    )
    db.add(m)
    db.flush()
    return m


@pytest.fixture
def vehicle(db, station):
    uid = str(uuid.uuid4())[:8]
    v = Vehicle(
        station_id=station.station_id,
        vehicle_number=f"RET-{uid}",
        vehicle_type=VehicleType.BLS,
        active=True,
    )
    db.add(v)
    db.flush()
    loc = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station.station_id,
        vehicle_id=v.vehicle_id,
        label=f"RET-{uid} — BLS",
    )
    db.add(loc)
    db.flush()
    return v


@pytest.fixture
def jump_bag(db, station):
    loc = InventoryLocation(
        location_type=LocationType.JUMP_BAG,
        station_id=station.station_id,
        label="Test Jump Bag",
    )
    db.add(loc)
    db.flush()
    return loc


@pytest.fixture
def item(db, station):
    # Get-or-create: route handlers call db.commit() which releases the savepoint,
    # so the row persists across tests in the same session despite rollback.
    existing = (
        db.query(Item)
        .filter(
            Item.name == "Retirement Test Item", Item.station_id == station.station_id
        )
        .first()
    )
    if existing:
        return existing
    i = Item(
        name="Retirement Test Item",
        station_id=station.station_id,
        category=ItemCategory.CONSUMABLE,
        check_type=ItemCheckType.SUPPLY,
        unit_of_measure="each",
        active=True,
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def stock_lot(db, jump_bag, item):
    lot = StockLot(
        item_id=item.item_id,
        location_id=jump_bag.location_id,
        quantity=5,
        lot_number="LOT-RET-001",
    )
    db.add(lot)
    db.flush()
    return lot


# ── RET-B1: Retire vehicle ────────────────────────────────────────────────────


def test_retire_vehicle_happy_path(client, auth_admin, station, admin_member, vehicle):
    resp = client.patch(
        f"/api/v1/vehicles/{vehicle.vehicle_id}/retire",
        json={"retirement_reason": "Vehicle totaled in accident."},
        headers=auth_admin,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["retired_at"] is not None
    assert data["retirement_reason"] == "Vehicle totaled in accident."
    assert data["active"] is False


def test_retire_vehicle_403_for_supervisor(
    client, auth_supervisor, station, admin_member, vehicle
):
    resp = client.patch(
        f"/api/v1/vehicles/{vehicle.vehicle_id}/retire",
        json={"retirement_reason": "Reason"},
        headers=auth_supervisor,
    )
    assert resp.status_code == 403


def test_retire_vehicle_409_on_double_retire(
    client, auth_admin, station, admin_member, vehicle
):
    client.patch(
        f"/api/v1/vehicles/{vehicle.vehicle_id}/retire",
        json={"retirement_reason": "First time."},
        headers=auth_admin,
    )
    resp = client.patch(
        f"/api/v1/vehicles/{vehicle.vehicle_id}/retire",
        json={"retirement_reason": "Second time."},
        headers=auth_admin,
    )
    assert resp.status_code == 409


# ── RET-B2: Retire location ────────────────────────────────────────────────────


def test_retire_location_happy_path(
    client, auth_admin, station, admin_member, jump_bag
):
    resp = client.patch(
        f"/api/v1/inventory/locations/{jump_bag.location_id}/retire",
        json={"retirement_reason": "Jump bag worn out."},
        headers=auth_admin,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["retired_at"] is not None
    assert data["retirement_reason"] == "Jump bag worn out."


def test_retire_location_409_on_double_retire(
    client, auth_admin, station, admin_member, jump_bag
):
    client.patch(
        f"/api/v1/inventory/locations/{jump_bag.location_id}/retire",
        json={"retirement_reason": "First time."},
        headers=auth_admin,
    )
    resp = client.patch(
        f"/api/v1/inventory/locations/{jump_bag.location_id}/retire",
        json={"retirement_reason": "Second time."},
        headers=auth_admin,
    )
    assert resp.status_code == 409


# ── RET-B3: Retire station ─────────────────────────────────────────────────────


def test_retire_station_happy_path(client, auth_admin, station, admin_member):
    resp = client.patch(
        f"/api/v1/stations/{station.station_id}/retire",
        json={"retirement_reason": "Station merged with Station 2."},
        headers=auth_admin,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["retired_at"] is not None
    assert data["active"] is False


def test_retire_station_409_on_double_retire(client, auth_admin, station, admin_member):
    client.patch(
        f"/api/v1/stations/{station.station_id}/retire",
        json={"retirement_reason": "First time."},
        headers=auth_admin,
    )
    resp = client.patch(
        f"/api/v1/stations/{station.station_id}/retire",
        json={"retirement_reason": "Second time."},
        headers=auth_admin,
    )
    assert resp.status_code == 409


# ── RET-B4: List retired objects ──────────────────────────────────────────────


def test_list_retired_vehicles(client, auth_admin, station, admin_member, vehicle):
    client.patch(
        f"/api/v1/vehicles/{vehicle.vehicle_id}/retire",
        json={"retirement_reason": "Retired for test."},
        headers=auth_admin,
    )
    resp = client.get(
        f"/api/v1/admin/retired?type=vehicles&station_id={station.station_id}",
        headers=auth_admin,
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert any(i["id"] == vehicle.vehicle_id for i in items)


def test_list_retired_invalid_type(client, auth_admin):
    resp = client.get("/api/v1/admin/retired?type=invalid", headers=auth_admin)
    assert resp.status_code == 422


# ── RET-B5: Retire stock lot ──────────────────────────────────────────────────


def test_retire_lot_happy_path(client, auth_admin, station, admin_member, stock_lot):
    resp = client.patch(
        f"/api/v1/inventory/lots/{stock_lot.lot_id}/retire",
        json={"retirement_reason": "Lot expired — disposed."},
        headers=auth_admin,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["retired_at"] is not None
    assert data["quantity"] == 0
    assert data["retirement_reason"] == "Lot expired — disposed."


def test_retire_lot_409_on_double_retire(
    client, auth_admin, station, admin_member, stock_lot
):
    client.patch(
        f"/api/v1/inventory/lots/{stock_lot.lot_id}/retire",
        json={"retirement_reason": "First time."},
        headers=auth_admin,
    )
    resp = client.patch(
        f"/api/v1/inventory/lots/{stock_lot.lot_id}/retire",
        json={"retirement_reason": "Second time."},
        headers=auth_admin,
    )
    assert resp.status_code == 409


def test_retire_lot_403_for_responder(
    client, auth_responder, station, admin_member, stock_lot
):
    resp = client.patch(
        f"/api/v1/inventory/lots/{stock_lot.lot_id}/retire",
        json={"retirement_reason": "Reason"},
        headers=auth_responder,
    )
    assert resp.status_code == 403


# ── RET-B6: List retired lots ─────────────────────────────────────────────────


def test_list_retired_lots(
    client, auth_admin, station, admin_member, jump_bag, stock_lot
):
    client.patch(
        f"/api/v1/inventory/lots/{stock_lot.lot_id}/retire",
        json={"retirement_reason": "Expired."},
        headers=auth_admin,
    )
    resp = client.get(
        f"/api/v1/inventory/lots/retired?location_id={jump_bag.location_id}",
        headers=auth_admin,
    )
    assert resp.status_code == 200
    lots = resp.json()
    assert len(lots) >= 1
    assert any(lot["lot_id"] == stock_lot.lot_id for lot in lots)


# ── RET-B2b: Retired location excluded from check wizard ─────────────────────


def test_retired_location_excluded_from_station_locations(
    client, auth_admin, station, admin_member, jump_bag
):
    """A retired jump bag must not appear in GET /stations/{id}/locations."""
    # Verify it shows before retirement
    resp = client.get(
        f"/api/v1/stations/{station.station_id}/locations",
        headers=auth_admin,
    )
    assert resp.status_code == 200
    ids_before = [loc["location_id"] for loc in resp.json()]
    assert jump_bag.location_id in ids_before

    # Retire it
    client.patch(
        f"/api/v1/inventory/locations/{jump_bag.location_id}/retire",
        json={"retirement_reason": "Worn out."},
        headers=auth_admin,
    )

    # Must not appear after retirement
    resp = client.get(
        f"/api/v1/stations/{station.station_id}/locations",
        headers=auth_admin,
    )
    assert resp.status_code == 200
    ids_after = [loc["location_id"] for loc in resp.json()]
    assert jump_bag.location_id not in ids_after
