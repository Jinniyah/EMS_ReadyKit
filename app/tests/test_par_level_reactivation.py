"""
tests/test_par_level_reactivation.py
PAR-B1 -- Reactivating a soft-deactivated par level on re-add.

Bug (Session AF): the unique constraint uq_par_item_compartment
(item_id, compartment_id) has no concept of `active`. Soft-deactivating a
par level (Remove in Station Administration / the check-wizard admin
screens) leaves a row occupying that slot, so re-adding the same item to
the same compartment always hit the IntegrityError fallback and reported
"already assigned" -- even though no active duplicate existed and the item
correctly showed as removed everywhere active-only par levels are
displayed (Station Supplies catalog, check wizard Step 3 Items, etc).

Covers both creation entry points that hit this constraint:
  - POST /admin/items/{id}/assign        (admin_items.py -- Station Admin UI path)
  - POST /inventory/par-levels           (inventory.py -- direct creation path)

Fixture isolation note: every route handler exercised here calls db.commit(),
which releases the active SAVEPOINT (see CLAUDE.md / conftest.py's isolation
notes and the get-or-create pattern already used in test_supply_room.py).
A compartment that is reused across tests would therefore carry forward
whatever par levels a prior test in this file committed against it, which
defeats the very "still blocks an active duplicate" assertions this file
exists to make. The `compartment` fixture is parametrized per test name so
every test gets its own compartment row and never collides with another
test's committed par levels. `vehicle_location` and `test_item` stay
get-or-create (matching test_supply_room.py) since they're not the rows
under test here and Vehicle/Item both enforce global name uniqueness.

Second isolation note: because `test_item` is shared across tests (get-or-
create) while each test gets its own compartment, GET .../par-levels for the
whole vehicle_location can legitimately contain an active row for test_item
left behind by a *different* test's compartment. Assertions that check
"is this item gone/back" must therefore scope on (item_id, compartment_id)
together, never item_id alone -- see test_reactivated_item_visible_to_check_wizard.
"""

from __future__ import annotations

import pytest

from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item, ItemCategory, ItemCheckType
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.vehicle import Vehicle, VehicleType

ADMIN = "/api/v1/admin"
INV = "/api/v1/inventory"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def station(db):
    s = Station(
        name="PAR-B1 Test Station", address="1 Test Way", region="Test", active=True
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def membership(db, station):
    for user_id, role in [
        ("test-administrator@ems.local", "Administrator"),
        ("test-supervisor@ems.local", "Supervisor"),
    ]:
        db.add(
            StationMember(
                station_id=station.station_id,
                user_id=user_id,
                role=role,
                assigned_by="test",
                active=True,
            )
        )
    db.flush()


@pytest.fixture
def vehicle_location(db, station):
    """Get-or-create, matching the pattern in test_supply_room.py."""
    v = db.query(Vehicle).filter(Vehicle.vehicle_number == "PARB1-T01").first()
    if v is None:
        v = Vehicle(
            station_id=station.station_id,
            vehicle_number="PARB1-T01",
            vehicle_type=VehicleType.BLS,
            active=True,
        )
        db.add(v)
        db.flush()
    else:
        v.station_id = station.station_id
        db.flush()

    loc = (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.vehicle_id == v.vehicle_id,
            InventoryLocation.location_type == LocationType.VEHICLE,
        )
        .first()
    )
    if loc is None:
        loc = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=station.station_id,
            vehicle_id=v.vehicle_id,
            label="Unit PARB1-T01",
        )
        db.add(loc)
        db.flush()
    else:
        loc.station_id = station.station_id
        db.flush()
    return loc


@pytest.fixture
def compartment(db, vehicle_location, request):
    """
    One fresh compartment per test (named after the test's nodeid) so a par
    level committed by one test can never collide with another test's
    "still blocks an active duplicate" assertions. Compartment names are
    only unique within a location (see create_compartment's conflict check),
    so a per-test name is enough -- no need to also vary vehicle/location.
    """
    name = f"PAR-B1 Compartment [{request.node.name}]"
    comp = Compartment(
        location_id=vehicle_location.location_id,
        name=name,
        sort_order=1,
        active=True,
    )
    db.add(comp)
    db.flush()
    return comp


@pytest.fixture
def test_item(db, station):
    item = (
        db.query(Item)
        .filter(Item.name == "PAR-B1 Test Item", Item.station_id == station.station_id)
        .first()
    )
    if item is None:
        item = Item(
            name="PAR-B1 Test Item",
            station_id=station.station_id,
            category=ItemCategory.CONSUMABLE,
            check_type=ItemCheckType.SUPPLY,
            unit_of_measure="each",
            active=True,
        )
        db.add(item)
        db.flush()
    return item


def _vehicle_id(db, vehicle_location):
    return vehicle_location.vehicle_id


# ---------------------------------------------------------------------------
# POST /admin/items/{id}/assign -- assign_item_to_compartment
# ---------------------------------------------------------------------------


class TestAssignReactivation:

    def test_assign_after_remove_succeeds(
        self,
        client,
        db,
        station,
        vehicle_location,
        compartment,
        test_item,
        membership,
        auth_supervisor,
    ):
        """Reproduces the reported bug: assign, remove, re-assign same item
        to the same compartment must succeed (not 409 'already assigned')."""
        vehicle_id = _vehicle_id(db, vehicle_location)

        r1 = client.post(
            f"{ADMIN}/items/{test_item.item_id}/assign",
            json={
                "vehicle_id": vehicle_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 1,
                "max_quantity": 4,
            },
            headers=auth_supervisor,
        )
        assert r1.status_code == 201
        original_par_id = r1.json()["par_id"]

        r2 = client.patch(
            f"{ADMIN}/par-levels/{original_par_id}/deactivate",
            json={"reason": "Testing removal"},
            headers=auth_supervisor,
        )
        assert r2.status_code == 204

        # Re-assign the same item to the same compartment -- must succeed.
        r3 = client.post(
            f"{ADMIN}/items/{test_item.item_id}/assign",
            json={
                "vehicle_id": vehicle_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 2,
                "max_quantity": 6,
            },
            headers=auth_supervisor,
        )
        assert r3.status_code == 201
        data = r3.json()
        assert data["active"] is True
        assert data["min_quantity"] == 2
        assert data["max_quantity"] == 6
        # Reactivates the original row rather than creating an orphaned duplicate.
        assert data["par_id"] == original_par_id

    def test_reactivated_row_clears_deactivation_fields(
        self,
        client,
        db,
        station,
        vehicle_location,
        compartment,
        test_item,
        membership,
        auth_supervisor,
    ):
        vehicle_id = _vehicle_id(db, vehicle_location)

        r1 = client.post(
            f"{ADMIN}/items/{test_item.item_id}/assign",
            json={
                "vehicle_id": vehicle_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 1,
                "max_quantity": 4,
            },
            headers=auth_supervisor,
        )
        par_id = r1.json()["par_id"]
        client.patch(
            f"{ADMIN}/par-levels/{par_id}/deactivate",
            json={"reason": "No longer stocked"},
            headers=auth_supervisor,
        )

        client.post(
            f"{ADMIN}/items/{test_item.item_id}/assign",
            json={
                "vehicle_id": vehicle_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 1,
                "max_quantity": 4,
            },
            headers=auth_supervisor,
        )

        db.expire_all()
        par = db.query(ParLevel).filter(ParLevel.par_id == par_id).first()
        assert par.active is True
        assert par.deactivated_at is None
        assert par.deactivation_reason is None

    def test_reactivated_item_visible_to_check_wizard(
        self,
        client,
        db,
        station,
        vehicle_location,
        compartment,
        test_item,
        membership,
        auth_supervisor,
    ):
        """The whole point of the fix: GET par-levels (what the check wizard
        reads) must include the item again after remove -> re-add."""
        vehicle_id = _vehicle_id(db, vehicle_location)

        r1 = client.post(
            f"{ADMIN}/items/{test_item.item_id}/assign",
            json={
                "vehicle_id": vehicle_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 1,
                "max_quantity": 4,
            },
            headers=auth_supervisor,
        )
        par_id = r1.json()["par_id"]
        client.patch(
            f"{ADMIN}/par-levels/{par_id}/deactivate",
            json={"reason": "Testing"},
            headers=auth_supervisor,
        )

        # Confirm it's gone from the wizard-facing endpoint while inactive.
        # Scoped to this test's own compartment_id, not just item_id --
        # test_item is a shared get-or-create fixture (Item enforces global
        # name uniqueness) and may carry an unrelated active par level on a
        # different compartment under the same vehicle_location from another
        # test in this file. GET .../par-levels returns every active par for
        # the whole location, so item_id alone isn't a precise enough check.
        gone = client.get(
            f"{INV}/locations/{vehicle_location.location_id}/par-levels",
            headers=auth_supervisor,
        )
        assert not any(
            p["item_id"] == test_item.item_id
            and p["compartment_id"] == compartment.compartment_id
            for p in gone.json()
        )

        client.post(
            f"{ADMIN}/items/{test_item.item_id}/assign",
            json={
                "vehicle_id": vehicle_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 1,
                "max_quantity": 4,
            },
            headers=auth_supervisor,
        )

        back = client.get(
            f"{INV}/locations/{vehicle_location.location_id}/par-levels",
            headers=auth_supervisor,
        )
        assert any(
            p["item_id"] == test_item.item_id
            and p["compartment_id"] == compartment.compartment_id
            for p in back.json()
        )

    def test_assign_still_blocks_active_duplicate(
        self,
        client,
        db,
        station,
        vehicle_location,
        compartment,
        test_item,
        membership,
        auth_supervisor,
    ):
        """Unrelated to the fix: assigning the same item twice while still
        active must still 409 -- only inactive rows get reactivated."""
        vehicle_id = _vehicle_id(db, vehicle_location)

        r1 = client.post(
            f"{ADMIN}/items/{test_item.item_id}/assign",
            json={
                "vehicle_id": vehicle_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 1,
                "max_quantity": 4,
            },
            headers=auth_supervisor,
        )
        assert r1.status_code == 201

        r2 = client.post(
            f"{ADMIN}/items/{test_item.item_id}/assign",
            json={
                "vehicle_id": vehicle_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 1,
                "max_quantity": 4,
            },
            headers=auth_supervisor,
        )
        assert r2.status_code == 409
        assert "already assigned" in r2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /inventory/par-levels -- create_par_level
# ---------------------------------------------------------------------------


class TestCreateParLevelReactivation:

    def test_create_after_deactivate_succeeds(
        self,
        client,
        db,
        station,
        vehicle_location,
        compartment,
        test_item,
        membership,
        auth_supervisor,
    ):
        r1 = client.post(
            f"{INV}/par-levels",
            json={
                "item_id": test_item.item_id,
                "location_id": vehicle_location.location_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 1,
                "max_quantity": 4,
            },
            headers=auth_supervisor,
        )
        assert r1.status_code == 201
        original_par_id = r1.json()["par_id"]

        client.patch(
            f"{INV}/par-levels/{original_par_id}",
            json={"reason": "Removed for test"},
            headers=auth_supervisor,
        )

        r2 = client.post(
            f"{INV}/par-levels",
            json={
                "item_id": test_item.item_id,
                "location_id": vehicle_location.location_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 3,
                "max_quantity": 8,
            },
            headers=auth_supervisor,
        )
        assert r2.status_code == 201
        data = r2.json()
        assert data["par_id"] == original_par_id
        assert data["active"] is True
        assert data["min_quantity"] == 3
        assert data["max_quantity"] == 8

    def test_create_still_blocks_active_duplicate(
        self,
        client,
        db,
        station,
        vehicle_location,
        compartment,
        test_item,
        membership,
        auth_supervisor,
    ):
        r1 = client.post(
            f"{INV}/par-levels",
            json={
                "item_id": test_item.item_id,
                "location_id": vehicle_location.location_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 1,
                "max_quantity": 4,
            },
            headers=auth_supervisor,
        )
        assert r1.status_code == 201

        r2 = client.post(
            f"{INV}/par-levels",
            json={
                "item_id": test_item.item_id,
                "location_id": vehicle_location.location_id,
                "compartment_id": compartment.compartment_id,
                "min_quantity": 1,
                "max_quantity": 4,
            },
            headers=auth_supervisor,
        )
        assert r2.status_code == 409
