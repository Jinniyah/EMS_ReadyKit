"""
seed.py
Development / demo seed script for EMS ReadyKit.

Populates the database with the operational model defined in Requirements.md:
  - 1 Station (Newberg Township Station 1)
  - 2 ALS Ambulances + their inventory locations
  - 3 QRV/BLS Fire Trucks + their inventory locations
  - 1 Station Supply Room
  - Representative items (medications, consumables, equipment)
  - Par levels per item per location
  - Sample stock lots (with lot numbers and expiration dates)

IMPORTANT:
  This script is for LOCAL DEVELOPMENT AND DEMO PURPOSES ONLY.
  Do not run against a production database.
  It is safe to run multiple times — it checks for existing data before inserting.

Usage:
    cd app
    python seed.py

Prerequisites:
    - Virtual environment activated
    - Dependencies installed (pip install -r requirements.txt)
    - Migrations applied (alembic upgrade head)
    - .env configured (defaults to SQLite dev database)
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from ems_readykit.core.database import SessionLocal
from ems_readykit.models import (
    DailyInventoryCheck,
    CheckStatus,
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


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def seed(db: Session) -> None:
    # ── Guard: skip if already seeded ─────────────────────────────────────────
    if db.query(Station).count() > 0:
        print("Database already contains data. Skipping seed.")
        return

    print("Seeding database...")

    # ── Station ───────────────────────────────────────────────────────────────
    station = Station(
        name="Newberg Township Station 1",
        address="100 Fire Station Dr, Newberg Township, MI 48183",
        region="Downriver",
        active=True,
    )
    db.add(station)
    db.flush()  # get station_id before referencing it below
    print(f"  Created station: {station.name} (id={station.station_id})")

    # ── Vehicles ──────────────────────────────────────────────────────────────
    vehicles_data = [
        ("AMB-401", VehicleType.ALS, "Medic 401 — ALS Ambulance"),
        ("AMB-402", VehicleType.ALS, "Medic 402 — ALS Ambulance"),
        ("ENG-501", VehicleType.QRV, "Engine 501 — Fire Truck"),
        ("ENG-502", VehicleType.QRV, "Engine 502 — Fire Truck"),
        ("RESCUE-601", VehicleType.BLS, "Rescue 601 — BLS Unit"),
    ]

    vehicles: dict[str, Vehicle] = {}
    locations: dict[str, InventoryLocation] = {}

    for vnum, vtype, label in vehicles_data:
        v = Vehicle(
            station_id=station.station_id,
            vehicle_number=vnum,
            vehicle_type=vtype,
            active=True,
        )
        db.add(v)
        db.flush()

        loc = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=station.station_id,
            vehicle_id=v.vehicle_id,
            label=label,
        )
        db.add(loc)
        db.flush()

        vehicles[vnum] = v
        locations[vnum] = loc
        print(f"  Created vehicle: {vnum} ({vtype.value}) → location: {label}")

    # ── Station Supply Room ───────────────────────────────────────────────────
    supply_room = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        vehicle_id=None,
        label="Station 1 Supply Room",
    )
    db.add(supply_room)
    db.flush()
    locations["SUPPLY"] = supply_room
    print(f"  Created supply room: {supply_room.label} (id={supply_room.location_id})")

    # ── Items ─────────────────────────────────────────────────────────────────
    # (name, category, controlled_substance, unit_of_measure)
    items_data = [
        # Medications — ALS controlled substances
        ("Epinephrine 1mg/mL", ItemCategory.MEDICATION, True, "mL"),
        ("Morphine Sulfate 10mg", ItemCategory.MEDICATION, True, "mg"),
        ("Midazolam 5mg/mL", ItemCategory.MEDICATION, True, "mL"),
        # Medications — non-controlled
        ("Aspirin 325mg", ItemCategory.MEDICATION, False, "tablet"),
        ("Nitroglycerin 0.4mg SL", ItemCategory.MEDICATION, False, "tablet"),
        ("Diphenhydramine 50mg/mL", ItemCategory.MEDICATION, False, "mL"),
        # Consumables
        ("Gauze 4x4 Sterile", ItemCategory.CONSUMABLE, False, "each"),
        ("IV Catheter 18g", ItemCategory.CONSUMABLE, False, "each"),
        ("Normal Saline 1000mL", ItemCategory.CONSUMABLE, False, "bag"),
        ("Oxygen Mask — Non-Rebreather", ItemCategory.CONSUMABLE, False, "each"),
        ("Tourniquet — CAT", ItemCategory.CONSUMABLE, False, "each"),
        # Equipment
        ("AED Electrode Pads (adult)", ItemCategory.EQUIPMENT, False, "pair"),
        ("BVM — Adult", ItemCategory.EQUIPMENT, False, "each"),
        ("King LT Airway Size 4", ItemCategory.EQUIPMENT, False, "each"),
    ]

    items: dict[str, Item] = {}
    for name, category, controlled, uom in items_data:
        item = Item(
            name=name,
            category=category,
            controlled_substance=controlled,
            unit_of_measure=uom,
            active=True,
        )
        db.add(item)
        db.flush()
        items[name] = item
    print(f"  Created {len(items)} items.")

    # ── Par Levels ────────────────────────────────────────────────────────────
    # ALS ambulance par levels (controlled + non-controlled medications, all consumables)
    als_par_levels = [
        ("Epinephrine 1mg/mL",          2, 6),
        ("Morphine Sulfate 10mg",        2, 6),
        ("Midazolam 5mg/mL",            2, 4),
        ("Aspirin 325mg",               4, 12),
        ("Nitroglycerin 0.4mg SL",      4, 12),
        ("Diphenhydramine 50mg/mL",     2, 6),
        ("Gauze 4x4 Sterile",          10, 30),
        ("IV Catheter 18g",             4, 12),
        ("Normal Saline 1000mL",        2, 6),
        ("Oxygen Mask — Non-Rebreather", 2, 6),
        ("Tourniquet — CAT",            2, 4),
        ("AED Electrode Pads (adult)",  1, 3),
        ("BVM — Adult",                 1, 2),
        ("King LT Airway Size 4",       2, 4),
    ]

    # QRV/BLS par levels — no controlled substances
    non_als_par_levels = [
        ("Aspirin 325mg",               4, 12),
        ("Gauze 4x4 Sterile",          10, 30),
        ("Oxygen Mask — Non-Rebreather", 2, 6),
        ("Tourniquet — CAT",            2, 4),
        ("AED Electrode Pads (adult)",  1, 3),
        ("BVM — Adult",                 1, 2),
    ]

    # Supply room par levels (higher maximums for resupply buffer)
    supply_par_levels = [
        ("Epinephrine 1mg/mL",          6, 20),
        ("Morphine Sulfate 10mg",        6, 20),
        ("Midazolam 5mg/mL",            4, 12),
        ("Aspirin 325mg",              12, 48),
        ("Nitroglycerin 0.4mg SL",     12, 48),
        ("Diphenhydramine 50mg/mL",     6, 20),
        ("Gauze 4x4 Sterile",          30, 100),
        ("IV Catheter 18g",            12, 40),
        ("Normal Saline 1000mL",        6, 20),
        ("Oxygen Mask — Non-Rebreather", 6, 20),
        ("Tourniquet — CAT",            4, 12),
        ("AED Electrode Pads (adult)",  3, 10),
        ("BVM — Adult",                 2, 6),
        ("King LT Airway Size 4",       4, 12),
    ]

    par_count = 0

    for vnum, vehicle in vehicles.items():
        loc = locations[vnum]
        par_data = als_par_levels if vehicle.vehicle_type == VehicleType.ALS else non_als_par_levels
        for item_name, min_q, max_q in par_data:
            db.add(ParLevel(
                item_id=items[item_name].item_id,
                location_id=loc.location_id,
                min_quantity=min_q,
                max_quantity=max_q,
            ))
            par_count += 1

    for item_name, min_q, max_q in supply_par_levels:
        db.add(ParLevel(
            item_id=items[item_name].item_id,
            location_id=supply_room.location_id,
            min_quantity=min_q,
            max_quantity=max_q,
        ))
        par_count += 1

    db.flush()
    print(f"  Created {par_count} par level records.")

    # ── Stock Lots ────────────────────────────────────────────────────────────
    # Representative lots on each ALS vehicle and the supply room.
    # Includes one near-expiry lot to demonstrate expiration alerting.
    als_vehicles = [v for k, v in vehicles.items() if v.vehicle_type == VehicleType.ALS]

    lot_count = 0
    for vehicle in als_vehicles:
        loc = locations[vehicle.vehicle_number]
        lots = [
            ("Epinephrine 1mg/mL",       4, f"LOT-EPI-{vehicle.vehicle_number}", date(2027, 6, 30)),
            ("Morphine Sulfate 10mg",     4, f"LOT-MOR-{vehicle.vehicle_number}", date(2027, 3, 31)),
            # Near-expiry lot — triggers expiration alerting in Phase 3
            ("Midazolam 5mg/mL",         2, f"LOT-MID-{vehicle.vehicle_number}", date(2026, 6, 15)),
            ("Aspirin 325mg",            8, f"LOT-ASP-{vehicle.vehicle_number}", date(2028, 1, 31)),
            ("Nitroglycerin 0.4mg SL",   8, f"LOT-NTG-{vehicle.vehicle_number}", date(2027, 9, 30)),
            ("Diphenhydramine 50mg/mL",  4, f"LOT-DPH-{vehicle.vehicle_number}", date(2027, 12, 31)),
            ("Gauze 4x4 Sterile",       20, f"LOT-GAU-{vehicle.vehicle_number}", None),
            ("IV Catheter 18g",          8, f"LOT-IVC-{vehicle.vehicle_number}", date(2028, 6, 30)),
            ("Normal Saline 1000mL",     4, f"LOT-NSS-{vehicle.vehicle_number}", date(2027, 8, 31)),
            ("Oxygen Mask — Non-Rebreather", 4, f"LOT-OXM-{vehicle.vehicle_number}", None),
            ("Tourniquet — CAT",         2, f"LOT-TRQ-{vehicle.vehicle_number}", None),
            ("AED Electrode Pads (adult)", 2, f"LOT-AED-{vehicle.vehicle_number}", date(2028, 3, 31)),
            ("BVM — Adult",              1, f"LOT-BVM-{vehicle.vehicle_number}", None),
            ("King LT Airway Size 4",    2, f"LOT-KLT-{vehicle.vehicle_number}", date(2028, 12, 31)),
        ]
        for item_name, qty, lot_num, exp in lots:
            db.add(StockLot(
                item_id=items[item_name].item_id,
                location_id=loc.location_id,
                quantity=qty,
                lot_number=lot_num,
                expiration_date=exp,
            ))
            lot_count += 1

    # Supply room stock
    supply_lots = [
        ("Epinephrine 1mg/mL",       12, "LOT-EPI-SUPPLY-A", date(2027, 6, 30)),
        ("Morphine Sulfate 10mg",     12, "LOT-MOR-SUPPLY-A", date(2027, 3, 31)),
        ("Midazolam 5mg/mL",          8, "LOT-MID-SUPPLY-A", date(2027, 11, 30)),
        ("Aspirin 325mg",            24, "LOT-ASP-SUPPLY-A", date(2028, 1, 31)),
        ("Gauze 4x4 Sterile",        60, "LOT-GAU-SUPPLY-A", None),
        ("IV Catheter 18g",          24, "LOT-IVC-SUPPLY-A", date(2028, 6, 30)),
        ("Normal Saline 1000mL",     12, "LOT-NSS-SUPPLY-A", date(2027, 8, 31)),
        ("Tourniquet — CAT",          8, "LOT-TRQ-SUPPLY-A", None),
        ("AED Electrode Pads (adult)", 6, "LOT-AED-SUPPLY-A", date(2028, 3, 31)),
    ]
    for item_name, qty, lot_num, exp in supply_lots:
        db.add(StockLot(
            item_id=items[item_name].item_id,
            location_id=supply_room.location_id,
            quantity=qty,
            lot_number=lot_num,
            expiration_date=exp,
        ))
        lot_count += 1

    db.flush()
    print(f"  Created {lot_count} stock lot records.")

    # ── Sample Daily Inventory Check ──────────────────────────────────────────
    # One completed check per ALS vehicle for today, to demonstrate the
    # one-per-vehicle-per-day uniqueness constraint in action.
    today = utcnow().date().isoformat()
    check_count = 0
    for vehicle in als_vehicles:
        db.add(DailyInventoryCheck(
            vehicle_id=vehicle.vehicle_id,
            station_id=station.station_id,
            check_date=today,
            performed_by="seed.script",
            timestamp=utcnow(),
            status=CheckStatus.PASS,
            notes="Seeded by seed.py for demo purposes.",
        ))
        check_count += 1

    db.flush()
    print(f"  Created {check_count} sample daily inventory check(s) for today ({today}).")

    # ── Commit ────────────────────────────────────────────────────────────────
    db.commit()
    print("\nSeed complete.")
    print(f"  Station:       1")
    print(f"  Vehicles:      {len(vehicles)}")
    print(f"  Locations:     {len(locations)}")
    print(f"  Items:         {len(items)}")
    print(f"  Par levels:    {par_count}")
    print(f"  Stock lots:    {lot_count}")
    print(f"  Daily checks:  {check_count}")


def main() -> None:
    print("EMS ReadyKit — Development Seed Script")
    print("=" * 45)
    print("WARNING: For local development and demo use only.")
    print()

    db = SessionLocal()
    try:
        seed(db)
    except Exception as exc:
        db.rollback()
        print(f"\nSeed failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
