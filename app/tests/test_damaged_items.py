"""
tests/test_damaged_items.py
GET /stations/{station_id}/damaged-items (SUP-DMG1)
=====================================================
Verifies the endpoint that surfaces is_damaged=True par level entries
to the supervisor compliance dashboard.

Coverage targets:
  - Empty list when no items damaged
  - Returns correct item name, vehicle number, location label, compartment name
  - Damaged item on a portable location (no vehicle -- vehicle_number is None)
  - Retired location items are excluded (location.retired_at is not None)
  - Inactive par levels (active=False) are excluded
  - Responder gets 403
  - Non-member supervisor gets 403
  - Unknown station returns 404
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

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


def _make_station(db: Session) -> Station:
    station = Station(name=f"DMG-Station-{_uid()}", address="1 Test St", region="Test")
    db.add(station)
    db.flush()
    return station


def _add_member(db: Session, station_id: int, email: str, role: str) -> None:
    db.add(
        StationMember(
            station_id=station_id,
            user_id=email,
            role=role,
            assigned_by="test-administrator@ems.local",
            active=True,
        )
    )
    db.flush()


def _make_vehicle_location(db: Session, station: Station) -> tuple:
    """Create a vehicle + its VEHICLE inventory location. Returns (vehicle, location)."""
    vehicle = Vehicle(
        station_id=station.station_id,
        vehicle_number=f"DMG-{_uid()}",
        vehicle_type=VehicleType.BLS,
    )
    db.add(vehicle)
    db.flush()

    location = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station.station_id,
        vehicle_id=vehicle.vehicle_id,
        label=f"Unit {vehicle.vehicle_number}",
    )
    db.add(location)
    db.flush()
    return vehicle, location


def _make_portable_location(db: Session, station: Station) -> InventoryLocation:
    """Create a JUMP_BAG portable location (no vehicle)."""
    location = InventoryLocation(
        location_type=LocationType.JUMP_BAG,
        station_id=station.station_id,
        vehicle_id=None,
        label=f"Jump Bag {_uid()}",
    )
    db.add(location)
    db.flush()
    return location


def _make_compartment(
    db: Session, location: InventoryLocation, name: str | None = None
) -> Compartment:
    comp = Compartment(
        location_id=location.location_id,
        name=name or f"Comp-{_uid()}",
        sort_order=1,
        active=True,
    )
    db.add(comp)
    db.flush()
    return comp


def _make_item(db: Session, name: str | None = None) -> Item:
    item = Item(
        name=name or f"Item-{_uid()}",
        category=ItemCategory.EQUIPMENT,
        check_type=ItemCheckType.SUPPLY,
        unit_of_measure="each",
        active=True,
    )
    db.add(item)
    db.flush()
    return item


def _make_par(
    db: Session,
    item: Item,
    location: InventoryLocation,
    comp: Compartment,
    *,
    is_damaged: bool = False,
    active: bool = True,
) -> ParLevel:
    par = ParLevel(
        item_id=item.item_id,
        location_id=location.location_id,
        compartment_id=comp.compartment_id,
        min_quantity=1,
        max_quantity=5,
        is_damaged=is_damaged,
        active=active,
    )
    db.add(par)
    db.flush()
    return par


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetDamagedItemsEndpoint:

    def test_empty_when_no_items_damaged(self, client, db, auth_supervisor):
        """Returns [] when station has items but none are marked damaged."""
        station = _make_station(db)
        _add_member(db, station.station_id, "test-supervisor@ems.local", "Supervisor")
        _vehicle, location = _make_vehicle_location(db, station)
        comp = _make_compartment(db, location)
        item = _make_item(db)
        _make_par(db, item, location, comp, is_damaged=False)

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_damaged_item_on_vehicle(self, client, db, auth_supervisor):
        """Damaged item on a vehicle location returns item name and vehicle number."""
        station = _make_station(db)
        _add_member(db, station.station_id, "test-supervisor@ems.local", "Supervisor")
        vehicle, location = _make_vehicle_location(db, station)
        comp = _make_compartment(db, location, name="Compartment 2")
        item = _make_item(db, name="Testing Add Item")
        _make_par(db, item, location, comp, is_damaged=True)

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        row = data[0]
        assert row["item_name"] == "Testing Add Item"
        assert row["vehicle_number"] == vehicle.vehicle_number
        assert row["compartment_name"] == "Compartment 2"
        assert row["location_label"] == location.label

    def test_returns_damaged_item_on_portable_location(
        self, client, db, auth_supervisor
    ):
        """Damaged item on a portable (jump bag) location has vehicle_number=None."""
        station = _make_station(db)
        _add_member(db, station.station_id, "test-supervisor@ems.local", "Supervisor")
        location = _make_portable_location(db, station)
        comp = _make_compartment(db, location, name="Main Pouch")
        item = _make_item(db, name="Jump Bag Gloves")
        _make_par(db, item, location, comp, is_damaged=True)

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        row = data[0]
        assert row["item_name"] == "Jump Bag Gloves"
        assert row["vehicle_number"] is None
        assert row["location_label"] == location.label
        assert row["compartment_name"] == "Main Pouch"

    def test_returns_multiple_damaged_items(self, client, db, auth_supervisor):
        """Multiple damaged items across compartments all appear in results."""
        station = _make_station(db)
        _add_member(db, station.station_id, "test-supervisor@ems.local", "Supervisor")
        _vehicle, location = _make_vehicle_location(db, station)
        comp1 = _make_compartment(db, location, name="Compartment 1")
        comp2 = _make_compartment(db, location, name="Compartment 2")
        item1 = _make_item(db, name="AED Pads")
        item2 = _make_item(db, name="O2 Mask")
        _make_par(db, item1, location, comp1, is_damaged=True)
        _make_par(db, item2, location, comp2, is_damaged=True)

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        names = {row["item_name"] for row in data}
        assert "AED Pads" in names
        assert "O2 Mask" in names

    def test_excludes_undamaged_items(self, client, db, auth_supervisor):
        """Items with is_damaged=False are excluded even when damaged items exist."""
        station = _make_station(db)
        _add_member(db, station.station_id, "test-supervisor@ems.local", "Supervisor")
        _vehicle, location = _make_vehicle_location(db, station)
        comp = _make_compartment(db, location)
        item_ok = _make_item(db, name="Fine Item")
        item_dmg = _make_item(db, name="Broken Item")
        _make_par(db, item_ok, location, comp, is_damaged=False)
        _make_par(db, item_dmg, location, comp, is_damaged=True)

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 200
        data = r.json()
        names = [row["item_name"] for row in data]
        assert "Broken Item" in names
        assert "Fine Item" not in names

    def test_excludes_inactive_par_levels(self, client, db, auth_supervisor):
        """Soft-deactivated par levels (active=False) are not returned even if is_damaged=True."""
        station = _make_station(db)
        _add_member(db, station.station_id, "test-supervisor@ems.local", "Supervisor")
        _vehicle, location = _make_vehicle_location(db, station)
        comp = _make_compartment(db, location)
        item = _make_item(db, name="Deactivated Damaged Item")
        _make_par(db, item, location, comp, is_damaged=True, active=False)

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_excludes_retired_location(self, client, db, auth_supervisor):
        """Damaged items at a retired location are not surfaced."""
        station = _make_station(db)
        _add_member(db, station.station_id, "test-supervisor@ems.local", "Supervisor")
        _vehicle, location = _make_vehicle_location(db, station)
        # Retire the location
        location.retired_at = datetime.now(timezone.utc)
        location.retired_by = "test-administrator@ems.local"
        location.retirement_reason = "Vehicle retired"
        db.flush()

        comp = _make_compartment(db, location)
        item = _make_item(db, name="Item on Retired Vehicle")
        _make_par(db, item, location, comp, is_damaged=True)

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_only_returns_items_for_this_station(self, client, db, auth_supervisor):
        """Damaged items at a different station are not returned."""
        station_a = _make_station(db)
        station_b = _make_station(db)
        _add_member(db, station_a.station_id, "test-supervisor@ems.local", "Supervisor")

        # Damaged item at station B
        _vehicle_b, location_b = _make_vehicle_location(db, station_b)
        comp_b = _make_compartment(db, location_b)
        item_b = _make_item(db, name="Other Station Item")
        _make_par(db, item_b, location_b, comp_b, is_damaged=True)

        # Clean item at station A
        _vehicle_a, location_a = _make_vehicle_location(db, station_a)
        comp_a = _make_compartment(db, location_a)
        item_a = _make_item(db, name="Own Station Item")
        _make_par(db, item_a, location_a, comp_a, is_damaged=False)

        r = client.get(
            f"/api/v1/stations/{station_a.station_id}/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_admin_can_access_endpoint(self, client, db, auth_admin):
        """Administrator role satisfies SUPERVISOR_PLUS requirement."""
        station = _make_station(db)
        _add_member(
            db, station.station_id, "test-administrator@ems.local", "Administrator"
        )

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_admin,
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_responder_returns_403(self, client, db, auth_responder):
        """Responders do not have Supervisor+ access to this endpoint."""
        station = _make_station(db)
        _add_member(db, station.station_id, "test-responder@ems.local", "Responder")

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_responder,
        )
        assert r.status_code == 403

    def test_non_member_supervisor_returns_403(self, client, db, auth_supervisor):
        """A supervisor not assigned to this station gets 403, not leaking data."""
        station = _make_station(db)
        # Intentionally NOT adding test-supervisor@ems.local as a member

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 403

    def test_unknown_station_returns_404(self, client, auth_supervisor):
        """A non-existent station_id returns 404."""
        r = client.get(
            "/api/v1/stations/99999999/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 404

    def test_results_sorted_by_item_name(self, client, db, auth_supervisor):
        """Results are returned in alphabetical order by item name."""
        station = _make_station(db)
        _add_member(db, station.station_id, "test-supervisor@ems.local", "Supervisor")
        _vehicle, location = _make_vehicle_location(db, station)
        comp = _make_compartment(db, location)
        item_z = _make_item(db, name="Zebra Bandage")
        item_a = _make_item(db, name="Ace Wrap")
        item_m = _make_item(db, name="Morphine Syringe")
        _make_par(db, item_z, location, comp, is_damaged=True)
        # Need separate comps for unique constraint (one par per item per compartment)
        comp2 = _make_compartment(db, location)
        comp3 = _make_compartment(db, location)
        _make_par(db, item_a, location, comp2, is_damaged=True)
        _make_par(db, item_m, location, comp3, is_damaged=True)

        r = client.get(
            f"/api/v1/stations/{station.station_id}/damaged-items",
            headers=auth_supervisor,
        )
        assert r.status_code == 200
        names = [row["item_name"] for row in r.json()]
        assert names == sorted(names), f"Results not sorted alphabetically: {names}"
        assert names == ["Ace Wrap", "Morphine Syringe", "Zebra Bandage"]
