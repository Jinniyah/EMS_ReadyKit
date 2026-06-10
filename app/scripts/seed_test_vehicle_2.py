"""
scripts/seed_test_vehicle_2.py
Creates a second test vehicle (TEST-2 / QRV) at the dev station
with a basic set of compartments for par level assignment testing.

Usage:
    cd app
    python scripts/seed_test_vehicle_2.py

Safe to run multiple times — checks for existing records before inserting.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ems_readykit.core.database import SessionLocal
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.models.vehicle import Vehicle, VehicleType

VEHICLE_NUMBER = "TEST-2"
VEHICLE_TYPE   = VehicleType.QRV

COMPARTMENTS = [
    {"name": "PC 1 (Airway)",    "location_descriptor": "Interior, left side front",  "sort_order": 1},
    {"name": "PC 2 (Cardiac)",   "location_descriptor": "Interior, left side mid",    "sort_order": 2},
    {"name": "PC 3 (Trauma)",    "location_descriptor": "Interior, right side front", "sort_order": 3},
    {"name": "Drug Bag",         "location_descriptor": "Interior, centre console",   "sort_order": 4, "restriction_note": "ALS crews only"},
    {"name": "Driver Side EC 1", "location_descriptor": "Exterior, driver side",      "sort_order": 5},
]


def main() -> None:
    db = SessionLocal()
    try:
        station = db.query(Station).first()
        if not station:
            print("ERROR: No stations found. Run the main seed script first.")
            sys.exit(1)

        print(f"Using station: {station.name} (id={station.station_id})")

        existing = db.query(Vehicle).filter(
            Vehicle.vehicle_number == VEHICLE_NUMBER
        ).first()

        if existing:
            print(f"Vehicle {VEHICLE_NUMBER} already exists (id={existing.vehicle_id}) — skipping vehicle creation.")
            vehicle = existing
        else:
            vehicle = Vehicle(
                station_id     = station.station_id,
                vehicle_number = VEHICLE_NUMBER,
                vehicle_type   = VEHICLE_TYPE,
                active         = True,
            )
            db.add(vehicle)
            db.flush()

            location = InventoryLocation(
                location_type = LocationType.VEHICLE,
                station_id    = station.station_id,
                vehicle_id    = vehicle.vehicle_id,
                label         = f"{VEHICLE_NUMBER} — {VEHICLE_TYPE.value}",
            )
            db.add(location)
            db.flush()

            print(f"Created vehicle {VEHICLE_NUMBER} (id={vehicle.vehicle_id})")
            print(f"Created inventory location (id={location.location_id})")

        location = db.query(InventoryLocation).filter(
            InventoryLocation.vehicle_id == vehicle.vehicle_id
        ).first()

        if not location:
            print(f"ERROR: No inventory location found for vehicle {vehicle.vehicle_id}")
            sys.exit(1)

        created = 0
        for comp_data in COMPARTMENTS:
            existing_comp = db.query(Compartment).filter(
                Compartment.location_id == location.location_id,
                Compartment.name        == comp_data["name"],
            ).first()

            if existing_comp:
                print(f"  Compartment '{comp_data['name']}' already exists — skipping.")
            else:
                comp = Compartment(
                    location_id         = location.location_id,
                    name                = comp_data["name"],
                    location_descriptor = comp_data.get("location_descriptor"),
                    sort_order          = comp_data.get("sort_order", 0),
                    restriction_note    = comp_data.get("restriction_note"),
                    active              = True,
                )
                db.add(comp)
                created += 1
                print(f"  Created compartment: {comp_data['name']}")

        db.commit()
        print(f"\nDone. {created} compartment(s) created.")
        print("Vehicle TEST-2 is ready for par level assignment testing.")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
