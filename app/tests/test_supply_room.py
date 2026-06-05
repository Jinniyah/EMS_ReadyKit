"""
tests/test_supply_room.py
Supply Room & Restocking — SUPPLY-B1, SUPPLY-B2, SUPPLY-B3.

Covers:
  - GET /stations/{id}/supply-room
  - GET /inventory/locations/{id}/stock-summary
  - POST /inventory/transfer
  - GET /inventory/locations/{id}/transfers
  - GET /inventory/receive-stock/template
  - POST /inventory/locations/{id}/receive-stock/csv
"""
from __future__ import annotations

import io
from datetime import date, timedelta

import pytest

from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item, ItemCategory, ItemCheckType
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.models.vehicle import Vehicle, VehicleType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def station(db):
    s = Station(name="Test Supply Station", address="123 Test St", region="Test", active=True)
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def supply_room(db, station):
    loc = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label="Test Supply Room",
    )
    db.add(loc)
    db.flush()
    for name, descriptor, sort_order in [
        ("Cab 1 - Shelf 1", "Cabinet 1, top shelf", 1),
        ("Cab 1 - Shelf 2", "Cabinet 1, bottom shelf", 2),
    ]:
        db.add(Compartment(location_id=loc.location_id, name=name,
                           location_descriptor=descriptor, sort_order=sort_order, active=True))
    db.flush()
    return loc


@pytest.fixture
def vehicle_location(db, station):
    """
    Get-or-create semantics (same reason as test_item): route handlers that
    call db.commit() release the active savepoint, so SQLite may not fully
    undo the vehicle insert on the outer rollback. Re-using the existing row
    and re-pointing it at the current test's station avoids the UNIQUE
    constraint failure on vehicles.vehicle_number for subsequent tests.
    """
    v = db.query(Vehicle).filter(Vehicle.vehicle_number == "T01").first()
    if v is None:
        v = Vehicle(
            station_id=station.station_id,
            vehicle_number="T01",
            vehicle_type=VehicleType.BLS,
            active=True,
        )
        db.add(v)
        db.flush()
    else:
        v.station_id = station.station_id
        db.flush()

    loc = db.query(InventoryLocation).filter(
        InventoryLocation.vehicle_id == v.vehicle_id,
        InventoryLocation.location_type == LocationType.VEHICLE,
    ).first()
    if loc is None:
        loc = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=station.station_id,
            vehicle_id=v.vehicle_id,
            label="Unit T01",
        )
        db.add(loc)
        db.flush()
    else:
        loc.station_id = station.station_id
        db.flush()
    return loc


@pytest.fixture
def test_item(db):
    """
    Get-or-create semantics: after any test that calls db.commit() inside
    a route handler, SQLite's StaticPool may not fully undo the insert on
    rollback. Using an existing row avoids the UNIQUE constraint error on
    items.name without affecting test correctness — each test gets fresh
    StockLots and Stations via auto-increment PKs regardless.
    """
    item = db.query(Item).filter(Item.name == "Test Gauze Pad").first()
    if item is None:
        item = Item(
            name="Test Gauze Pad",
            category=ItemCategory.CONSUMABLE,
            check_type=ItemCheckType.SUPPLY,
            unit_of_measure="each",
            active=True,
        )
        db.add(item)
        db.flush()
    return item


@pytest.fixture
def supply_lot(db, supply_room, test_item):
    lot = StockLot(
        item_id=test_item.item_id,
        location_id=supply_room.location_id,
        quantity=20,
        lot_number="LOT-TEST-001",
        expiration_date=date.today() + timedelta(days=180),
    )
    db.add(lot)
    db.flush()
    return lot


@pytest.fixture
def membership(db, station):
    """Add admin, supervisor, and responder to the station."""
    for user_id, role in [
        ("test-administrator@ems.local", "Administrator"),
        ("test-supervisor@ems.local",    "Supervisor"),
        ("test-responder@ems.local",     "Responder"),
    ]:
        db.add(StationMember(
            station_id=station.station_id,
            user_id=user_id,
            role=role,
            assigned_by="test",
            active=True,
        ))
    db.flush()


# ---------------------------------------------------------------------------
# SUPPLY-B3: GET /stations/{id}/supply-room
# ---------------------------------------------------------------------------

def test_get_supply_room_ok(client, db, station, supply_room, membership, auth_admin):
    r = client.get(f"/api/v1/stations/{station.station_id}/supply-room", headers=auth_admin)
    assert r.status_code == 200
    data = r.json()
    assert data["location_type"] == "STATION_SUPPLY_ROOM"
    assert data["station_id"] == station.station_id


def test_get_supply_room_404_when_none(client, db, station, membership, auth_admin):
    """Station exists but has no supply room."""
    r = client.get(f"/api/v1/stations/{station.station_id}/supply-room", headers=auth_admin)
    assert r.status_code == 404


def test_get_supply_room_requires_membership(client, db, station, supply_room, auth_supervisor):
    """Supervisor without a membership row gets 403.
    Note: auth_admin bypasses membership checks entirely — use supervisor here."""
    # Intentionally no `membership` fixture so test-supervisor@ems.local has no row
    r = client.get(f"/api/v1/stations/{station.station_id}/supply-room", headers=auth_supervisor)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# SUPPLY-B2: GET /inventory/locations/{id}/stock-summary
# ---------------------------------------------------------------------------

def test_stock_summary_empty(client, db, supply_room, membership, auth_admin):
    r = client.get(f"/api/v1/inventory/locations/{supply_room.location_id}/stock-summary",
                   headers=auth_admin)
    assert r.status_code == 200
    assert r.json() == []


def test_stock_summary_with_lots(client, db, supply_room, supply_lot, membership, auth_admin):
    r = client.get(f"/api/v1/inventory/locations/{supply_room.location_id}/stock-summary",
                   headers=auth_admin)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    item = items[0]
    assert item["total_quantity"] == 20
    assert item["status"] == "NO_PAR"
    assert len(item["lots"]) == 1


def test_stock_summary_status_with_par(client, db, supply_room, supply_lot, test_item, membership, auth_admin):
    db.add(ParLevel(
        item_id=test_item.item_id, location_id=supply_room.location_id,
        min_quantity=25, max_quantity=50,
    ))
    db.flush()
    r = client.get(f"/api/v1/inventory/locations/{supply_room.location_id}/stock-summary",
                   headers=auth_admin)
    assert r.status_code == 200
    item = r.json()[0]
    assert item["status"] == "LOW"
    assert item["par_min"] == 25


def test_stock_summary_status_ok(client, db, supply_room, supply_lot, test_item, membership, auth_admin):
    db.add(ParLevel(
        item_id=test_item.item_id, location_id=supply_room.location_id,
        min_quantity=5, max_quantity=20,
    ))
    db.flush()
    r = client.get(f"/api/v1/inventory/locations/{supply_room.location_id}/stock-summary",
                   headers=auth_admin)
    assert r.status_code == 200
    assert r.json()[0]["status"] == "OK"


# ---------------------------------------------------------------------------
# SUPPLY-B1: POST /inventory/transfer
# ---------------------------------------------------------------------------

def test_transfer_supply_to_vehicle(
    client, db, station, supply_room, supply_lot, vehicle_location, test_item, membership, auth_supervisor
):
    payload = {
        "from_location_id": supply_room.location_id,
        "to_location_id":   vehicle_location.location_id,
        "item_id":          test_item.item_id,
        "quantity":         5,
        "notes":            "Restocked before shift",
    }
    r = client.post("/api/v1/inventory/transfer", json=payload, headers=auth_supervisor)
    assert r.status_code == 201
    data = r.json()
    assert data["quantity"] == 5
    assert data["item_id"] == test_item.item_id
    assert data["lot_number"] == "LOT-TEST-001"

    # Verify source lot was reduced
    db.expire_all()
    updated_lot = db.query(StockLot).filter(StockLot.lot_id == supply_lot.lot_id).first()
    assert updated_lot.quantity == 15

    # Verify destination lot was created
    dest_lot = db.query(StockLot).filter(
        StockLot.location_id == vehicle_location.location_id,
        StockLot.item_id     == test_item.item_id,
    ).first()
    assert dest_lot is not None
    assert dest_lot.quantity == 5


def test_transfer_insufficient_stock(
    client, db, station, supply_room, supply_lot, vehicle_location, test_item, membership, auth_supervisor
):
    payload = {
        "from_location_id": supply_room.location_id,
        "to_location_id":   vehicle_location.location_id,
        "item_id":          test_item.item_id,
        "quantity":         100,  # only 20 available
    }
    r = client.post("/api/v1/inventory/transfer", json=payload, headers=auth_supervisor)
    assert r.status_code == 422
    assert "Insufficient stock" in r.json()["detail"]


def test_transfer_requires_supervisor(
    client, db, station, supply_room, supply_lot, vehicle_location, test_item, membership, auth_responder
):
    payload = {
        "from_location_id": supply_room.location_id,
        "to_location_id":   vehicle_location.location_id,
        "item_id":          test_item.item_id,
        "quantity":         1,
    }
    r = client.post("/api/v1/inventory/transfer", json=payload, headers=auth_responder)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Transfer history
# ---------------------------------------------------------------------------

def test_transfer_history(
    client, db, station, supply_room, supply_lot, vehicle_location, test_item, membership, auth_supervisor
):
    # Create a transfer first
    payload = {
        "from_location_id": supply_room.location_id,
        "to_location_id":   vehicle_location.location_id,
        "item_id":          test_item.item_id,
        "quantity":         3,
    }
    client.post("/api/v1/inventory/transfer", json=payload, headers=auth_supervisor)

    r = client.get(f"/api/v1/inventory/locations/{supply_room.location_id}/transfers",
                   headers=auth_supervisor)
    assert r.status_code == 200
    transfers = r.json()

    # Each test has a unique supply_room.location_id (auto-increment PK), so
    # transfers from other test runs are at different location IDs and won't appear.
    assert len(transfers) >= 1
    # Most recent is first
    latest = transfers[0]
    assert latest["quantity"] == 3
    assert latest["item_name"] == test_item.name
    assert latest["from_location_id"] == supply_room.location_id


# ---------------------------------------------------------------------------
# CSV template
# ---------------------------------------------------------------------------

def test_csv_template_download(client, auth_supervisor):
    r = client.get("/api/v1/inventory/receive-stock/template", headers=auth_supervisor)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.strip().splitlines()
    assert lines[0] == "item_name,lot_number,expiration_date,quantity"


# ---------------------------------------------------------------------------
# CSV bulk receive
# ---------------------------------------------------------------------------

def test_csv_receive_valid(client, db, supply_room, test_item, membership, auth_supervisor):
    csv_content = (
        "item_name,lot_number,expiration_date,quantity\n"
        f"{test_item.name},LOT-CSV-001,2027-12-31,15\n"
    )
    r = client.post(
        f"/api/v1/inventory/locations/{supply_room.location_id}/receive-stock/csv",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        headers=auth_supervisor,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["rows_imported"] == 1
    assert data["rows_skipped"] == 0
    assert len(data["lots_created"]) == 1
    assert data["lots_created"][0]["quantity"] == 15


def test_csv_receive_unknown_item(client, db, supply_room, membership, auth_supervisor):
    csv_content = (
        "item_name,lot_number,expiration_date,quantity\n"
        "Totally Unknown Item XYZ,,, 5\n"
    )
    r = client.post(
        f"/api/v1/inventory/locations/{supply_room.location_id}/receive-stock/csv",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        headers=auth_supervisor,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["rows_imported"] == 0
    assert data["rows_skipped"] == 1
    assert "not found" in data["errors"][0]["error"]
