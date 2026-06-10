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
  - Newberg Township Station 1 exists and is active
  - Unit 712 (BLS) exists, belongs to Newberg, has an inventory location
  - Unit 712 Jump Bag exists; Unit 710 Jump Bag does NOT exist at Newberg
  - PC 8 compartment has all 7 AED/LUCAS items with correct check types
  - AED Battery has priority_check=True and a priority_question
  - AED Date of Last Charge has recurrence_days=90
  - LUCAS Date of Last Charge has recurrence_days=30
  - AED/LUCAS items have station_supply=False
  - O2 PSI items have measurement_minimum=500 and correct check types
  - Truck Operations compartment has requires_full_check=True
  - Marcellus Township Station 1 and Unit 540 (ALS) exist
  - TEST STATION and Unit TEST (QRV) exist
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
    loc = db.query(InventoryLocation).filter(
        InventoryLocation.vehicle_id == vehicle.vehicle_id
    ).first()
    assert loc is not None, f"No inventory location for vehicle {vehicle.vehicle_number}"
    return loc


def _item(db: Session, name: str) -> Item:
    item = db.query(Item).filter(Item.name == name).first()
    assert item is not None, (
        f"Item '{name}' not found in item catalog -- check seed.py for name changes"
    )
    return item


def _compartment(db: Session, location: InventoryLocation, name: str) -> Compartment:
    comp = db.query(Compartment).filter(
        Compartment.location_id == location.location_id,
        Compartment.name == name,
    ).first()
    assert comp is not None, (
        f"Compartment '{name}' not found on location {location.label} "
        f"(location_id={location.location_id}) -- check seed.py"
    )
    return comp


def _par_for_item_in_compartment(
    db: Session, item: Item, comp: Compartment
) -> ParLevel:
    par = db.query(ParLevel).filter(
        ParLevel.item_id == item.item_id,
        ParLevel.compartment_id == comp.compartment_id,
    ).first()
    assert par is not None, (
        f"No par level for item '{item.name}' in compartment '{comp.name}'"
    )
    return par


# ---------------------------------------------------------------------------
# Station existence
# ---------------------------------------------------------------------------

class TestStationIntegrity:

    def test_newberg_township_station_exists(self, seeded_db):
        s = _station(seeded_db, "Newberg Township Station 1")
        assert s.active is True

    def test_marcellus_township_station_exists(self, seeded_db):
        s = _station(seeded_db, "Marcellus Township Station 1")
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
        assert v.vehicle_type == VehicleType.BLS, (
            f"Unit 712 is {v.vehicle_type} -- must be BLS"
        )
        assert v.active is True

    def test_unit_712_belongs_to_newberg(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        newberg = _station(seeded_db, "Newberg Township Station 1")
        assert v.station_id == newberg.station_id, (
            "Unit 712 does not belong to Newberg Township Station 1"
        )

    def test_unit_712_has_inventory_location(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        assert loc.location_type == LocationType.VEHICLE

    def test_unit_540_is_als(self, seeded_db):
        v = _vehicle(seeded_db, "540")
        assert v.vehicle_type == VehicleType.ALS, (
            f"Unit 540 is {v.vehicle_type} -- must be ALS"
        )

    def test_unit_test_is_qrv(self, seeded_db):
        v = _vehicle(seeded_db, "TEST")
        assert v.vehicle_type == VehicleType.QRV


# ---------------------------------------------------------------------------
# Jump bag integrity
# ---------------------------------------------------------------------------

class TestJumpBagIntegrity:

    def test_unit_712_jump_bag_exists_at_newberg(self, seeded_db):
        newberg = _station(seeded_db, "Newberg Township Station 1")
        jb = seeded_db.query(InventoryLocation).filter(
            InventoryLocation.station_id == newberg.station_id,
            InventoryLocation.location_type == LocationType.JUMP_BAG,
            InventoryLocation.label == "Unit 712 Jump Bag",
        ).first()
        assert jb is not None, "Unit 712 Jump Bag not found at Newberg Township"

    def test_unit_710_jump_bag_does_not_exist_at_newberg(self, seeded_db):
        """
        Unit 710 has no ambulance seeded yet. Its jump bag was an orphan
        in the check wizard Step 1 picker and was removed in v1.66.
        """
        newberg = _station(seeded_db, "Newberg Township Station 1")
        jb_710 = seeded_db.query(InventoryLocation).filter(
            InventoryLocation.station_id == newberg.station_id,
            InventoryLocation.location_type == LocationType.JUMP_BAG,
            InventoryLocation.label == "Unit 710 Jump Bag",
        ).first()
        assert jb_710 is None, (
            "Unit 710 Jump Bag found at Newberg Township -- it was removed because "
            "Unit 710 has no ambulance seeded. Remove it from the DB and re-seed."
        )

    def test_unit_712_jump_bag_has_compartments(self, seeded_db):
        newberg = _station(seeded_db, "Newberg Township Station 1")
        jb = seeded_db.query(InventoryLocation).filter(
            InventoryLocation.station_id == newberg.station_id,
            InventoryLocation.label == "Unit 712 Jump Bag",
        ).first()
        assert jb is not None
        comp_count = seeded_db.query(Compartment).filter(
            Compartment.location_id == jb.location_id,
            Compartment.active,
        ).count()
        assert comp_count >= 4, (
            f"Unit 712 Jump Bag only has {comp_count} compartment(s) -- expected at least 4"
        )


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
        assert item.check_type == ItemCheckType.FUNCTIONAL, (
            f"AED Battery check_type is {item.check_type} -- must be FUNCTIONAL"
        )
        par = _par_for_item_in_compartment(seeded_db, item, comp)
        assert par.priority_check is True, (
            "AED Battery priority_check is False -- must be True for priority check wizard"
        )
        assert par.priority_question is not None, (
            "AED Battery has no priority_question set"
        )

    def test_aed_battery_not_in_supply_room(self, seeded_db):
        item = _item(seeded_db, "AED Battery")
        assert item.station_supply is False, (
            "AED Battery has station_supply=True -- must be False (not a stockable supply)"
        )

    def test_aed_date_of_last_charge_in_pc8(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "AED Date of Last Charge")
        assert item.check_type == ItemCheckType.DATE_RECORD, (
            f"AED Date of Last Charge check_type is {item.check_type} -- must be DATE_RECORD"
        )
        assert item.recurrence_days == 90, (
            f"AED Date of Last Charge recurrence_days={item.recurrence_days} -- must be 90"
        )
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_aed_pads_adult_in_pc8(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "AED Pads Adult")
        assert item.check_type == ItemCheckType.DATE_RECORD, (
            f"AED Pads Adult check_type is {item.check_type} -- must be DATE_RECORD"
        )
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

    def test_lucas_device_ready_check_in_pc8_is_functional(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "LUCAS Device Ready Check")
        assert item.check_type == ItemCheckType.FUNCTIONAL, (
            f"LUCAS Device Ready Check check_type is {item.check_type} -- must be FUNCTIONAL"
        )
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_lucas_date_of_last_charge_in_pc8(self, seeded_db):
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")
        item = _item(seeded_db, "LUCAS Date of Last Charge")
        assert item.check_type == ItemCheckType.DATE_RECORD, (
            f"LUCAS Date of Last Charge check_type is {item.check_type} -- must be DATE_RECORD"
        )
        assert item.recurrence_days == 30, (
            f"LUCAS Date of Last Charge recurrence_days={item.recurrence_days} -- must be 30"
        )
        _par_for_item_in_compartment(seeded_db, item, comp)

    def test_lucas_not_in_supply_room(self, seeded_db):
        for name in ["LUCAS Device", "LUCAS Device Ready Check", "LUCAS Date of Last Charge"]:
            item = _item(seeded_db, name)
            assert item.station_supply is False, (
                f"'{name}' has station_supply=True -- must be False"
            )

    def test_pc8_has_all_seven_items(self, seeded_db):
        """All seven AED/LUCAS items must be present in PC 8 as par levels."""
        v = _vehicle(seeded_db, "712")
        loc = _location_for_vehicle(seeded_db, v)
        comp = _compartment(seeded_db, loc, "PC 8")

        expected_items = [
            "AED Battery",
            "AED Date of Last Charge",
            "AED Pads Adult",
            "AED Pads Pediatric",
            "LUCAS Device",
            "LUCAS Device Ready Check",
            "LUCAS Date of Last Charge",
        ]
        for item_name in expected_items:
            item = _item(seeded_db, item_name)
            par = seeded_db.query(ParLevel).filter(
                ParLevel.item_id == item.item_id,
                ParLevel.compartment_id == comp.compartment_id,
            ).first()
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
        assert item.check_type == ItemCheckType.MEASUREMENT, (
            f"On-Board O2 PSI check_type is {item.check_type} -- must be MEASUREMENT"
        )
        assert item.measurement_minimum == 500.0, (
            f"On-Board O2 PSI measurement_minimum={item.measurement_minimum} -- must be 500.0 PSI"
        )

    def test_stretcher_o2_psi_measurement_minimum(self, seeded_db):
        item = _item(seeded_db, "Stretcher O2 PSI")
        assert item.check_type == ItemCheckType.MEASUREMENT
        assert item.measurement_minimum == 500.0, (
            f"Stretcher O2 PSI measurement_minimum={item.measurement_minimum} -- must be 500.0 PSI"
        )

    def test_jump_bag_o2_psi_measurement_minimum(self, seeded_db):
        item = _item(seeded_db, "Jump Bag O2 PSI")
        assert item.check_type == ItemCheckType.MEASUREMENT
        assert item.measurement_minimum == 500.0, (
            f"Jump Bag O2 PSI measurement_minimum={item.measurement_minimum} -- must be 500.0 PSI"
        )

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
        functional_pars = seeded_db.query(ParLevel).join(Item).filter(
            ParLevel.compartment_id == comp.compartment_id,
            Item.check_type == ItemCheckType.FUNCTIONAL,
        ).count()
        assert functional_pars >= 10, (
            f"Truck Operations only has {functional_pars} FUNCTIONAL items -- "
            "expected at least 10 (Runs and Starts, Lights & Sirens, etc.)"
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
