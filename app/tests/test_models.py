"""
tests/test_models.py
Phase 1 model sanity tests.
Verifies that all tables create correctly and relationships are wired up.
No network or Azure dependencies required.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from ems_readykit.models import (
    AuditEvent,
    CheckStatus,
    Compartment,
    ControlledSubstanceCheck,
    DailyInventoryCheck,
    InventoryLocation,
    Item,
    ItemCategory,
    LocationType,
    ParLevel,
    Station,
    StockLot,
    Vehicle,
    VehicleType,
)


def _utcnow():
    return datetime.now(timezone.utc)


def test_create_station(db):
    station = Station(name="Station 1", address="123 Main St", region="North")
    db.add(station)
    db.flush()
    assert station.station_id is not None
    assert station.active is True


def test_create_vehicle_linked_to_station(db):
    station = Station(name="Station 1", address="123 Main St", region="North")
    db.add(station)
    db.flush()

    vehicle = Vehicle(
        station_id=station.station_id,
        vehicle_number="AMB-401",
        vehicle_type=VehicleType.ALS,
    )
    db.add(vehicle)
    db.flush()

    assert vehicle.vehicle_id is not None
    assert vehicle.station_id == station.station_id
    assert vehicle.requires_controlled_substance_check is True


def test_non_als_vehicle_no_cs_check(db):
    station = Station(name="Station 2", address="456 Oak Ave", region="South")
    db.add(station)
    db.flush()

    vehicle = Vehicle(
        station_id=station.station_id,
        vehicle_number="QRV-101",
        vehicle_type=VehicleType.QRV,
    )
    db.add(vehicle)
    db.flush()

    assert vehicle.requires_controlled_substance_check is False


def test_inventory_location_vehicle(db):
    station = Station(name="Station 1", address="1 Fire Ln", region="East")
    db.add(station)
    db.flush()

    vehicle = Vehicle(
        station_id=station.station_id,
        vehicle_number="AMB-402",
        vehicle_type=VehicleType.BLS,
    )
    db.add(vehicle)
    db.flush()

    loc = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station.station_id,
        vehicle_id=vehicle.vehicle_id,
        label="AMB-402 — BLS",
    )
    db.add(loc)
    db.flush()

    assert loc.location_id is not None
    assert loc.location_type == LocationType.VEHICLE


def test_inventory_location_supply_room(db):
    station = Station(name="Station 3", address="7 Hose Way", region="West")
    db.add(station)
    db.flush()

    supply_room = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label="Station 3 Supply Room",
    )
    db.add(supply_room)
    db.flush()

    assert supply_room.vehicle_id is None


def test_item_and_stock_lot(db):
    station = Station(name="S1", address="1 St", region="R")
    db.add(station)
    db.flush()

    loc = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label="Supply Room",
    )
    db.add(loc)
    db.flush()

    item = Item(
        name="Epinephrine 1mg/mL",
        category=ItemCategory.MEDICATION,
        controlled_substance=False,
        unit_of_measure="mg",
    )
    db.add(item)
    db.flush()

    lot = StockLot(
        item_id=item.item_id,
        location_id=loc.location_id,
        quantity=10,
        lot_number="LOT-2024-ABC",
        expiration_date=date(2026, 12, 31),
    )
    db.add(lot)
    db.flush()

    assert lot.lot_id is not None
    assert lot.expiration_date == date(2026, 12, 31)


def test_par_level_unique_constraint(db):
    """
    uq_par_item_compartment — the same item cannot appear twice in the same compartment.

    The legacy uq_par_item_location (item_id, location_id) constraint was dropped
    in migration 0004 because the same item legitimately appears in multiple
    compartments on the same vehicle (e.g. Stethoscope in PC3 and PC18).
    The correct uniqueness boundary is per-compartment, not per-location.
    """
    import pytest
    from sqlalchemy.exc import IntegrityError

    station = Station(name="S1", address="1 St", region="R")
    db.add(station)
    db.flush()

    loc = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label="Supply Room",
    )
    db.add(loc)
    db.flush()

    item = Item(
        name="Gauze 4x4", category=ItemCategory.CONSUMABLE, unit_of_measure="each"
    )
    db.add(item)
    db.flush()

    now = datetime.now(timezone.utc)
    comp = Compartment(
        location_id=loc.location_id,
        name="Compartment A",
        sort_order=1,
        active=True,
        als_only=False,
        created_at=now,
        updated_at=now,
    )
    db.add(comp)
    db.flush()

    # First par level for this item in this compartment — must succeed
    par1 = ParLevel(
        item_id=item.item_id,
        location_id=loc.location_id,
        compartment_id=comp.compartment_id,
        min_quantity=5,
        max_quantity=20,
    )
    db.add(par1)
    db.flush()

    # Duplicate: same item, same compartment — must raise IntegrityError
    par2 = ParLevel(
        item_id=item.item_id,
        location_id=loc.location_id,
        compartment_id=comp.compartment_id,
        min_quantity=3,
        max_quantity=10,
    )
    db.add(par2)
    with pytest.raises(IntegrityError):
        db.flush()


def test_daily_inventory_check(db):
    station = Station(name="S1", address="1 St", region="R")
    db.add(station)
    db.flush()

    vehicle = Vehicle(
        station_id=station.station_id,
        vehicle_number="AMB-501",
        vehicle_type=VehicleType.ALS,
    )
    db.add(vehicle)
    db.flush()

    check = DailyInventoryCheck(
        vehicle_id=vehicle.vehicle_id,
        station_id=station.station_id,
        check_date="2026-05-06",
        performed_by="j.smith",
        timestamp=_utcnow(),
        status=CheckStatus.PASS,
    )
    db.add(check)
    db.flush()

    assert check.check_id is not None
    assert check.status == CheckStatus.PASS


def test_controlled_substance_check(db):
    station = Station(name="S1", address="1 St", region="R")
    db.add(station)
    db.flush()

    vehicle = Vehicle(
        station_id=station.station_id,
        vehicle_number="AMB-601",
        vehicle_type=VehicleType.ALS,
    )
    db.add(vehicle)
    db.flush()

    cs_check = ControlledSubstanceCheck(
        vehicle_id=vehicle.vehicle_id,
        primary_signer="j.smith",
        secondary_signer="m.jones",
        timestamp=_utcnow(),
        discrepancy_flag=False,
    )
    db.add(cs_check)
    db.flush()

    assert cs_check.cs_check_id is not None
    assert cs_check.discrepancy_flag is False


def test_audit_event(db):
    event = AuditEvent(
        actor="j.smith",
        action="CHECK_COMPLETED",
        entity_type="DailyInventoryCheck",
        entity_id="1",
        severity="INFO",
        timestamp=_utcnow(),
    )
    db.add(event)
    db.flush()

    assert event.event_id is not None


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
