"""
tests/test_seed_integrity.py
Seed Data Integrity Tests
==========================
Verifies that after `alembic upgrade head && python seed.py`, the real
operational data is correct. These tests run against the SEEDED DEV DB
(ems_readykit_dev.db), not the in-memory test DB.

Uses the `seeded_db` fixture from conftest.py, which connects to the dev DB
read-only. If the dev DB does not exist, all tests are skipped with a clear
message.

What is verified:
  - Newberg Township Station exists and is active
  - Unit 712 (BLS) exists, belongs to Newberg, has an inventory location
  - Unit 712 Jump Bag exists; Unit 710 Jump Bag does NOT exist at Newberg
  - PC 8 compartment has all 6 AED/LUCAS items with correct check types (LUCAS Device Ready Check merged into LUCAS Device)
  - AED Battery has priority_check=True and a priority_question
  - AED Date of Last Charge has recurrence_days=90
  - LUCAS Date of Last Charge has recurrence_days=30
  - AED/LUCAS items have station_supply=False
  - On-Board O2 PSI has measurement_minimum=500; Stretcher/Jump Bag O2 PSI have 200 (small tank)
  - Truck Operations compartment has requires_full_check=True
  - Marcellus Township Station exists with its real fleet (Unit 612 BLS + Units 632/621
    QRV fire engines, ONBOARD-1) -- see TestMarcellusFleetIntegrity below
  - TEST STATION and Unit TEST (QRV) exist

Session AS (ONBOARD-1) note: station-name lookups in this file were corrected from
"Newberg Township Station 1" / "Marcellus Township Station 1" to the names the
current seed.py actually creates ("Newberg Township Station" / "Marcellus Township
Station", no trailing "1"). The old names only ever matched a stale, long-uncleaned
local ems_readykit_dev.db that had leftover stations from an older, pre-ITM-4 naming
convention -- a clean reseed (`Remove-Item ems_readykit_dev.db; alembic upgrade head;
python seed.py`, the documented sequence) surfaced the drift immediately. Also removed
`test_unit_540_is_als`: Unit 540 (ALS) no longer exists at Marcellus at all -- it was
renamed in place to Unit 612 (BLS) as part of ONBOARD-1 -- superseded by
TestMarcellusFleetIntegrity::test_unit_612_is_bls below.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ems_readykit.models import (
    Compartment,
    InventoryLocation,
    Item,
    ItemCheckType,
    LocationType,
    Station,
    Vehicle,
    VehicleType,
)
from ems_readykit.models.par_level import ParLevel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _station(db: Session, name: str) -> Station:
    s = db.query(Station).filter(Station.name == name).first()
    assert s is not None, f"Station '{name}' not found -- was seed.py run?"
    return s


def _vehicle(db: Session, number: str) -> Vehicle:
    v = db.query(Vehicle).filter(Vehicle.vehicle_number == number).first()
    assert v is not None, f"Vehicle '{number}' not found -- was seed.py run?"
    return v


def _location_for_vehicle(db: Session, vehicle: Vehicle) -> InventoryLocation:
    loc = (
        db.query(InventoryLocation)
        .filter(InventoryLocation.vehicle_id == vehicle.vehicle_id)
        .first()
    )
    assert (
        loc is not None
    ), f"No inventory location for vehicle {vehicle.vehicle_number}"
    return loc


def _item(db: Session, name: str) -> Item:
    item = db.query(Item).filter(Item.name == name).first()
    assert (
        item is not None
    ), f"Item '{name}' not found in item catalog -- check seed.py for name changes"
    return item


def _item_for_station(db: Session, station_id: int, name: str) -> Item:
    """Every BASE_ITEM_SEED item is created once per station (items.station_id FK,
    ITM-1), so a bare name lookup like _item() above is ambiguous for any item
    shared across stations -- it just returns whichever station's copy happens to
    come first. Use this station-scoped lookup instead for items that exist in
    more than one station's catalog (e.g. AED Battery, Blankets, or any Marcellus
    fire-truck item that Newberg/Training also pick up via BASE_ITEM_SEED)."""
    item = (
        db.query(Item)
        .filter(Item.station_id == station_id, Item.name == name)
        .first()
    )
    assert item is not None, (
        f"Item '{name}' not found in station {station_id}'s catalog -- "
        "check seed.py for name changes"
    )
    return item


def _compartment(db: Session, location: InventoryLocation, name: str) -> Compartment:
    comp = (
        db.query(Compartment)
        .filter(
            Compartment.location_id == location.location_id,
            Compartment.name == name,
        )
        .first()
    )
    assert comp is not None, (
        f"Compartment '{name}' not found on location {location.label} "
        f"(location_id={location.location_id}) -- check seed.py"
    )
    return comp


def _par_for_item_in_compartment(
    db: Session, item: Item, comp: Compartment
) -> ParLevel:
    par = (
        db.query(ParLevel)
        .filter(
            ParLevel.item_id == item.item_id,
            ParLevel.compartment_id == comp.compartment_id,
        )
        .first()
    )
    assert (
        par is not None
    ), f"No par level for item '{item.name}' in compartment '{comp.name}'"
    return par


# ---------------------------------------------------------------------------
# Station existence
# ---------------------------------------------------------------------------


class TestStationIntegrity:

    def test_newberg_township_station_exists(self, seeded_db):
        s = _station(seeded_db, "Newberg Township Station")
        assert s.active is True

    def test_marcellus_township_station_exists(self, seeded_db):
        s = _station(seeded_db, "Marcellus Township Station")
        assert s.active is True

    def test_test_station_exists(self, seeded_db):
        s = _station(seeded_db, "\u26a0 TEST STATION \u2014 Dev Only")
        assert s.active is True


# ---------------------------------------------------------------------------
# Vehicle integrity
# ---------------------------------------------------------------------------


class TestVehicleIntegrity:

    def test_unit_712_is_bls(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        assert (
            v.vehicle_type == VehicleType.BLS
        ), f"Unit 712 is {v.vehicle_type} -- must be BLS"
        assert v.active is True

    def test_unit_712_belongs_to_newberg(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        newberg = _station(seeded_db, "Newberg Township Station")
        assert (
            v.station_id == newberg.station_id
        ), "Unit 712 does not belong to Newberg Township Station"

    def test_unit_712_has_inventory_location(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        assert loc.location_type == LocationType.VEHICLE

    def test_unit_test_is_qrv(self, seeded_db):
        v = _vehicle(seeded_db, "TEST")
        assert v.vehicle_type == VehicleType.QRV


# ---------------------------------------------------------------------------
# Jump bag integrity
# ---------------------------------------------------------------------------


class TestJumpBagIntegrity:

    def test_unit_712_jump_bag_exists_at_newberg(self, seeded_db):
        newberg = _station(seeded_db, "Newberg Township Station")
        jb = (
            seeded_db.query(InventoryLocation)
            .filter(
                InventoryLocation.station_id == newberg.station_id,
                InventoryLocation.location_type == LocationType.JUMP_BAG,
                InventoryLocation.label == "Unit 712 Jump Bag",
            )
            .first()
        )
        assert jb is not None, "Unit 712 Jump Bag not found at Newberg Township"

    def test_unit_710_jump_bag_does_not_exist_at_newberg(self, seeded_db):
        """
        Unit 710 has no ambulance seeded yet. Its jump bag was an orphan
        in the check wizard Step 1 picker and was removed in v1.66.
        """
        newberg = _station(seeded_db, "Newberg Township Station")
        jb_710 = (
            seeded_db.query(InventoryLocation)
            .filter(
                InventoryLocation.station_id == newberg.station_id,
                InventoryLocation.location_type == LocationType.JUMP_BAG,
                InventoryLocation.label == "Unit 710 Jump Bag",
            )
            .first()
        )
        assert jb_710 is None, (
            "Unit 710 Jump Bag found at Newberg Township -- it was removed because "
            "Unit 710 has no ambulance seeded. Remove it from the DB and re-seed."
        )

    def test_unit_712_jump_bag_has_compartments(self, seeded_db):
        newberg = _station(seeded_db, "Newberg Township Station")
        jb = (
            seeded_db.query(InventoryLocation)
            .filter(
                InventoryLocation.station_id == newberg.station_id,
                InventoryLocation.label == "Unit 712 Jump Bag",
            )
            .first()
        )
        assert jb is not None
        comp_count = (
            seeded_db.query(Compartment)
            .filter(
                Compartment.location_id == jb.location_id,
                Compartment.active,
            )
            .count()
        )
        assert (
            comp_count >= 4
        ), f"Unit 712 Jump Bag only has {comp_count} compartment(s) -- expected at least 4"


# ---------------------------------------------------------------------------
# PC 8 -- AED and LUCAS
# ---------------------------------------------------------------------------


class TestPC8Integrity:
    """
    PC 8 is the most critical compartment on Unit 712.
    It contains all AED and LUCAS items. If any are missing or misconfigured,
    the check wizard will silently skip them.
    """

    def test_pc8_exists_on_unit_712(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        _compartment(seeded_db, loc, "PC 8")

    def test_aed_battery_in_pc8_is_functional(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "AED Battery")
        assert (
            item.check_type == ItemCheckType.FUNCTIONAL
        ), f"AED Battery check_type is {item.check_type} -- must be FUNCTIONAL"
        par = _par_for_item_in_compartment(seeded_db, item, comp)
        assert (
            par.priority_check is True
        ), "AED Battery priority_check is False -- must be True for priority check wizard"
        assert (
            par.priority_question is not None
        ), "AED Battery has no priority_question set"

    def test_aed_battery_not_in_supply_room(self, seeded_db):
        item = _item(seeded_db, "AED Battery")
        assert (
            item.station_supply is False
        ), "AED Battery has station_supply=True -- must be False (not a stockable supply)"

    def test_aed_date_of_last_charge_in_pc8(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "AED Date of Last Charge")
        assert (
            item.check_type == ItemCheckType.DATE_RECORD
        ), f"AED Date of Last Charge check_type is {item.check_type} -- must be DATE_RECORD"
        assert (
            item.recurrence_days == 90
        ), f"AED Date of Last Charge recurrence_days={item.recurrence_days} -- must be 90"
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_aed_pads_adult_in_pc8(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "AED Pads Adult")
        assert (
            item.check_type == ItemCheckType.EXPIRY_DATE
        ), f"AED Pads Adult check_type is {item.check_type} -- must be EXPIRY_DATE"
        assert (
            item.recurrence_days is None
        ), f"AED Pads Adult recurrence_days={item.recurrence_days} -- must be None (EXPIRY_DATE uses date_value directly)"
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_aed_pads_pediatric_in_pc8(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "AED Pads Pediatric")
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_lucas_device_in_pc8(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "LUCAS Device")
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_lucas_device_in_pc8_is_functional_priority(self, seeded_db):
        """LUCAS Device Ready Check was merged into LUCAS Device (ITM-2/4).
        One canonical FUNCTIONAL item with priority_check=True."""
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "LUCAS Device")
        assert (
            item.check_type == ItemCheckType.FUNCTIONAL
        ), f"LUCAS Device check_type is {item.check_type} -- must be FUNCTIONAL"
        par = _par_for_item_in_compartment(seeded_db, item, comp)
        assert (
            par.priority_check is True
        ), "LUCAS Device priority_check is False -- must be True"
        assert (
            par.priority_question is not None
        ), "LUCAS Device has no priority_question set"

    def test_lucas_date_of_last_charge_in_pc8(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "LUCAS Date of Last Charge")
        assert (
            item.check_type == ItemCheckType.DATE_RECORD
        ), f"LUCAS Date of Last Charge check_type is {item.check_type} -- must be DATE_RECORD"
        assert (
            item.recurrence_days == 30
        ), f"LUCAS Date of Last Charge recurrence_days={item.recurrence_days} -- must be 30"
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_lucas_not_in_supply_room(self, seeded_db):
        for name in [
            "LUCAS Device",
            "LUCAS Date of Last Charge",
        ]:
            item = _item(seeded_db, name)
            assert (
                item.station_supply is False
            ), f"'{name}' has station_supply=True -- must be False"

    def test_pc8_has_all_six_items(self, seeded_db):
        """Six AED/LUCAS items must be present in PC 8. LUCAS Device Ready Check was
        merged into LUCAS Device (ITM-2/4), reducing from 7 to 6 items."""
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")

        expected_items = [
            "AED Battery",
            "AED Date of Last Charge",
            "AED Pads Adult",
            "AED Pads Pediatric",
            "LUCAS Device",
            "LUCAS Date of Last Charge",
        ]
        for item_name in expected_items:
            item = _item(seeded_db, item_name)
            par = (
                seeded_db.query(ParLevel)
                .filter(
                    ParLevel.item_id == item.item_id,
                    ParLevel.compartment_id == comp.compartment_id,
                )
                .first()
            )
            assert par is not None, (
                f"'{item_name}' has no par level in PC 8 -- "
                "it will be invisible in the check wizard"
            )


# ---------------------------------------------------------------------------
# O2 PSI items
# ---------------------------------------------------------------------------


class TestO2PSIIntegrity:

    def test_on_board_o2_psi_measurement_minimum(self, seeded_db):
        item = _item(seeded_db, "On-Board O2 PSI")
        assert (
            item.check_type == ItemCheckType.MEASUREMENT
        ), f"On-Board O2 PSI check_type is {item.check_type} -- must be MEASUREMENT"
        assert (
            item.measurement_minimum == 500.0
        ), f"On-Board O2 PSI measurement_minimum={item.measurement_minimum} -- must be 500.0 PSI"

    def test_stretcher_o2_psi_measurement_minimum(self, seeded_db):
        item = _item(seeded_db, "Stretcher O2 PSI")
        assert item.check_type == ItemCheckType.MEASUREMENT
        assert (
            item.measurement_minimum == 200.0
        ), f"Stretcher O2 PSI measurement_minimum={item.measurement_minimum} -- must be 200.0 PSI (small tank, ITM-2)"

    def test_jump_bag_o2_psi_measurement_minimum(self, seeded_db):
        item = _item(seeded_db, "Jump Bag O2 PSI")
        assert item.check_type == ItemCheckType.MEASUREMENT
        assert (
            item.measurement_minimum == 200.0
        ), f"Jump Bag O2 PSI measurement_minimum={item.measurement_minimum} -- must be 200.0 PSI (small tank, ITM-2)"

    def test_on_board_o2_psi_in_driver_side_ec1(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Driver Side EC 1")
        item = _item(seeded_db, "On-Board O2 PSI")
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_stretcher_o2_psi_in_stretcher_compartment(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Stretcher")
        item = _item(seeded_db, "Stretcher O2 PSI")
        _par_for_item_in_compartment(seeded_db, item, comp)


# ---------------------------------------------------------------------------
# Truck Operations
# ---------------------------------------------------------------------------


class TestTruckOperationsIntegrity:

    def test_truck_operations_compartment_exists(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        _compartment(seeded_db, loc, "Truck Operations")

    def test_truck_operations_requires_full_check(self, seeded_db):
        """
        requires_full_check=True blocks No Change on this compartment.
        Responders must physically verify every Truck Operations item.
        If this is False, the constraint is silently unenforced.
        """
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Truck Operations")
        assert comp.requires_full_check is True, (
            "Truck Operations requires_full_check is False -- "
            "No Change is not blocked. Responders can skip physical truck verification."
        )

    def test_truck_operations_has_functional_items(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Truck Operations")
        functional_pars = (
            seeded_db.query(ParLevel)
            .join(Item)
            .filter(
                ParLevel.compartment_id == comp.compartment_id,
                Item.check_type == ItemCheckType.FUNCTIONAL,
            )
            .count()
        )
        assert functional_pars >= 9, (
            f"Truck Operations only has {functional_pars} FUNCTIONAL items -- "
            "expected at least 9 (Fire Extinguisher merged to SUPPLY in ITM-2; 9 remain)"
        )

    def test_runs_and_starts_in_truck_operations(self, seeded_db):
        """The most critical Truck Operations item -- verifies the truck can actually move."""
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Truck Operations")
        item = _item(seeded_db, "Runs and Starts")
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_lights_and_sirens_in_truck_operations(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Truck Operations")
        item = _item(seeded_db, "External Warning Systems (Lights & Sirens)")
        _par_for_item_in_compartment(seeded_db, item, comp)


# ---------------------------------------------------------------------------
# Marcellus Township — Unit 612 (BLS ambulance) + Unit 632/621 (QRV fire
# engines) (ONBOARD-1)
# ---------------------------------------------------------------------------


class TestMarcellusFleetIntegrity:
    """Marcellus has exactly 3 vehicles after ONBOARD-1: 612 (BLS ambulance), 632
    (QRV fire engine), 621 (QRV fire engine). Unit 540 (ALS) no longer exists as
    part of Marcellus's active fleet -- it was renamed in place to 612/BLS."""

    def test_unit_612_is_bls(self, seeded_db):
        v = _vehicle(seeded_db, "612")
        assert (
            v.vehicle_type == VehicleType.BLS
        ), f"Unit 612 is {v.vehicle_type} -- must be BLS"
        assert v.active is True

    def test_unit_612_belongs_to_marcellus(self, seeded_db):
        v = _vehicle(seeded_db, "612")
        marcellus = _station(seeded_db, "Marcellus Township Station")
        assert (
            v.station_id == marcellus.station_id
        ), "Unit 612 does not belong to Marcellus Township Station"

    def test_unit_612_has_inventory_location(self, seeded_db):
        v = _vehicle(seeded_db, "612")
        loc = _location_for_vehicle(seeded_db, v)
        assert loc.location_type == LocationType.VEHICLE

    def test_unit_632_is_qrv(self, seeded_db):
        v = _vehicle(seeded_db, "632")
        assert v.vehicle_type == VehicleType.QRV
        assert v.active is True

    def test_unit_621_is_qrv(self, seeded_db):
        v = _vehicle(seeded_db, "621")
        assert v.vehicle_type == VehicleType.QRV
        assert v.active is True

    def test_marcellus_has_exactly_three_vehicles(self, seeded_db):
        marcellus = _station(seeded_db, "Marcellus Township Station")
        vehicles = (
            seeded_db.query(Vehicle)
            .filter(Vehicle.station_id == marcellus.station_id)
            .all()
        )
        numbers = sorted(v.vehicle_number for v in vehicles)
        assert numbers == [
            "612",
            "621",
            "632",
        ], f"Marcellus vehicles are {numbers} -- expected exactly 612/621/632"


# ---------------------------------------------------------------------------
# Unit 612 -- Marcellus BLS ambulance (own compartment layout, not 712's)
# ---------------------------------------------------------------------------


class TestUnit612Integrity:

    def test_vehicle_operations_daily_checks_compartment_exists(self, seeded_db):
        v = _vehicle(seeded_db, "612")
        loc = _location_for_vehicle(seeded_db, v)
        _compartment(seeded_db, loc, "Vehicle Operations / Daily Checks")

    def test_vehicle_operations_daily_checks_requires_full_check(self, seeded_db):
        v = _vehicle(seeded_db, "612")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Vehicle Operations / Daily Checks")
        assert comp.requires_full_check is True, (
            "Vehicle Operations / Daily Checks requires_full_check is False -- "
            "No Change is not blocked. Responders can skip physical verification."
        )

    def test_612_has_twenty_one_compartments(self, seeded_db):
        v = _vehicle(seeded_db, "612")
        loc = _location_for_vehicle(seeded_db, v)
        comp_count = (
            seeded_db.query(Compartment)
            .filter(Compartment.location_id == loc.location_id, Compartment.active)
            .count()
        )
        assert comp_count == 21, f"Unit 612 has {comp_count} compartments -- expected 21"

    def test_aed_battery_priority_in_pass_side_front_comp(self, seeded_db):
        v = _vehicle(seeded_db, "612")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Pass. Side Front Comp #1 (top)")
        item = _item_for_station(seeded_db, v.station_id, "AED Battery")
        par = _par_for_item_in_compartment(seeded_db, item, comp)
        assert par.priority_check is True
        assert par.priority_question == "AED shows READY?"

    def test_lucas_device_priority_in_pass_side_front_comp(self, seeded_db):
        v = _vehicle(seeded_db, "612")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Pass. Side Front Comp #1 (top)")
        item = _item_for_station(seeded_db, v.station_id, "LUCAS Device")
        par = _par_for_item_in_compartment(seeded_db, item, comp)
        assert par.priority_check is True
        assert par.priority_question == "LUCAS shows READY?"

    def test_run_box_item_reused_across_two_compartments(self, seeded_db):
        """'Run Box' is one canonical item with two par-level rows: the box itself
        (Run Box compartment) and its contents callout (Airway Seat Drawer)."""
        v = _vehicle(seeded_db, "612")
        item = _item_for_station(seeded_db, v.station_id, "Run Box")
        loc = _location_for_vehicle(seeded_db, v)
        run_box_comp = _compartment(seeded_db, loc, "Run Box")
        airway_drawer_comp = _compartment(seeded_db, loc, "Airway Seat Drawer")
        _par_for_item_in_compartment(seeded_db, item, run_box_comp)
        _par_for_item_in_compartment(seeded_db, item, airway_drawer_comp)

    def test_blankets_reused_in_linen_and_curb_side(self, seeded_db):
        """'Blankets' covers both Heavy and Light Blankets form lines -- one
        canonical item, one par row per compartment (not one row per form line)."""
        v = _vehicle(seeded_db, "612")
        item = _item_for_station(seeded_db, v.station_id, "Blankets")
        loc = _location_for_vehicle(seeded_db, v)
        linen = _compartment(seeded_db, loc, "Linen Cabinet")
        curb_seat = _compartment(seeded_db, loc, "Curb Side Seat Comp")
        _par_for_item_in_compartment(seeded_db, item, linen)
        _par_for_item_in_compartment(seeded_db, item, curb_seat)

    def test_duct_tape_reused_across_two_compartments(self, seeded_db):
        v = _vehicle(seeded_db, "612")
        item = _item_for_station(seeded_db, v.station_id, "Duct Tape")
        loc = _location_for_vehicle(seeded_db, v)
        ds2 = _compartment(seeded_db, loc, "Drivers Side Compartment #2")
        ds_supply = _compartment(seeded_db, loc, "Drivers Side Supply Comp")
        _par_for_item_in_compartment(seeded_db, item, ds2)
        _par_for_item_in_compartment(seeded_db, item, ds_supply)

    def test_on_board_o2_psi_secured_in_daily_checks(self, seeded_db):
        """Main On-Board O2 Tank Secured reuses the canonical On-Board O2 PSI item
        (500-2200 PSI threshold) -- does not override its measurement range."""
        v = _vehicle(seeded_db, "612")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Vehicle Operations / Daily Checks")
        item = _item_for_station(seeded_db, v.station_id, "On-Board O2 PSI")
        assert item.measurement_minimum == 500.0
        assert item.measurement_maximum == 2200.0
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_fuel_level_seeded_as_functional_check(self, seeded_db):
        """Fuel Level was on the paper form's header section but has no gauge
        field in the schema -- modeled as a pass/fail presence check (Jennifer
        confirmed pass/fail is fine for now) in Vehicle Operations / Daily
        Checks, alongside Unit Starts / Radio Check / etc."""
        v = _vehicle(seeded_db, "612")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Vehicle Operations / Daily Checks")
        item = _item_for_station(seeded_db, v.station_id, "Fuel Level")
        assert item.check_type == ItemCheckType.FUNCTIONAL
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_612_par_level_count(self, seeded_db):
        v = _vehicle(seeded_db, "612")
        loc = _location_for_vehicle(seeded_db, v)
        par_count = (
            seeded_db.query(ParLevel)
            .filter(ParLevel.location_id == loc.location_id)
            .count()
        )
        assert par_count == 153, f"Unit 612 has {par_count} par levels -- expected 153"


# ---------------------------------------------------------------------------
# Unit 632 / Unit 621 -- Marcellus fire engine trucks
# ---------------------------------------------------------------------------


class TestFireTruckIntegrity:

    def test_632_has_five_compartments(self, seeded_db):
        v = _vehicle(seeded_db, "632")
        loc = _location_for_vehicle(seeded_db, v)
        comp_count = (
            seeded_db.query(Compartment)
            .filter(Compartment.location_id == loc.location_id, Compartment.active)
            .count()
        )
        assert comp_count == 5, f"Unit 632 has {comp_count} compartments -- expected 5"

    def test_621_has_seven_compartments(self, seeded_db):
        v = _vehicle(seeded_db, "621")
        loc = _location_for_vehicle(seeded_db, v)
        comp_count = (
            seeded_db.query(Compartment)
            .filter(Compartment.location_id == loc.location_id, Compartment.active)
            .count()
        )
        assert comp_count == 7, f"Unit 621 has {comp_count} compartments -- expected 7"

    def test_under_hood_shared_across_632_and_621(self, seeded_db):
        """Under Hood is identical on both trucks -- same canonical items, separate
        par-level rows per vehicle's own compartment."""
        v632 = _vehicle(seeded_db, "632")
        item = _item_for_station(seeded_db, v632.station_id, "Hood Battery")
        loc632 = _location_for_vehicle(seeded_db, v632)
        comp632 = _compartment(seeded_db, loc632, "Under Hood")
        _par_for_item_in_compartment(seeded_db, item, comp632)

        v621 = _vehicle(seeded_db, "621")
        loc621 = _location_for_vehicle(seeded_db, v621)
        comp621 = _compartment(seeded_db, loc621, "Under Hood")
        _par_for_item_in_compartment(seeded_db, item, comp621)

    def test_tire_pressure_and_depth_has_sixteen_items(self, seeded_db):
        v = _vehicle(seeded_db, "632")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "Tire Pressure & Depth")
        par_count = (
            seeded_db.query(ParLevel)
            .filter(ParLevel.compartment_id == comp.compartment_id)
            .count()
        )
        assert (
            par_count == 16
        ), f"Tire Pressure & Depth has {par_count} items -- expected 16 (8 positions x 2)"

    def test_tire_pressure_has_no_confirmed_threshold(self, seeded_db):
        """OPEN ITEM (ONBOARD-1): no confirmed min/max PSI threshold yet."""
        item = _item(seeded_db, "Tire Pressure — LF")
        assert item.measurement_minimum is None
        assert item.measurement_maximum is None

    def test_tire_tread_depth_minimum(self, seeded_db):
        item = _item(seeded_db, "Tire Tread Depth — LF")
        assert item.measurement_minimum == 4.0

    def test_scbas_compartment_on_621(self, seeded_db):
        v = _vehicle(seeded_db, "621")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "SCBA's")
        item = _item_for_station(seeded_db, v.station_id, "SCBA")
        par = _par_for_item_in_compartment(seeded_db, item, comp)
        assert par.min_quantity == 4

    def test_gas_meter_reading_unit_confirmed_range_still_open(self, seeded_db):
        """Confirmed (Jennifer): a PSI gauge, same pattern as On-Board O2 PSI.
        OPEN ITEM (ONBOARD-1): safe min/max range still needs confirmation."""
        item = _item(seeded_db, "Gas Meter Reading")
        assert item.check_type == ItemCheckType.MEASUREMENT
        assert item.unit_of_measure == "PSI"
        assert item.measurement_minimum is None
        assert item.measurement_maximum is None

    def test_fire_truck_items_station_supply_false(self, seeded_db):
        for name in ["SCBA", "Generator Gas", "Run Sheets", "Tire Pressure — LF"]:
            item = _item(seeded_db, name)
            assert (
                item.station_supply is False
            ), f"'{name}' has station_supply=True -- must be False (Vehicle Operations group)"

    def test_632_par_level_count(self, seeded_db):
        v = _vehicle(seeded_db, "632")
        loc = _location_for_vehicle(seeded_db, v)
        par_count = (
            seeded_db.query(ParLevel)
            .filter(ParLevel.location_id == loc.location_id)
            .count()
        )
        assert par_count == 56, f"Unit 632 has {par_count} par levels -- expected 56"

    def test_621_par_level_count(self, seeded_db):
        v = _vehicle(seeded_db, "621")
        loc = _location_for_vehicle(seeded_db, v)
        par_count = (
            seeded_db.query(ParLevel)
            .filter(ParLevel.location_id == loc.location_id)
            .count()
        )
        assert par_count == 55, f"Unit 621 has {par_count} par levels -- expected 55"
