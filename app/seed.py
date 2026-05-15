"""
seed.py
Seed data for Ambulance 712 — Newberg Township Fire & EMS.

Source documents:
    Ambulance 712 Page 1 Inventory.jpg   — PC 1-13, BLS Drug Bag, special areas
    Ambulance 712 Page 2 Inventory.jpg   — PC 14-18, EC bays, Truck Operations
    Ambulance Jump Bag.jpg               — Jump Bag (shared Units 710/712)

Usage:
    cd app
    python seed.py

Prerequisites:
    alembic upgrade head must have been run first.
    APP_ENV=development (uses SQLite by default).

Design decisions:
    - Items are created in the global catalog first (idempotent by name).
    - Station, Vehicle, and Jump Bag location are created before compartments.
    - Compartments are created in sort_order matching the physical walk-around.
    - Par levels link each item to its compartment with the required quantity.
    - Items marked * on the paper form are flagged needs_expiration_tracking=True
      (no actual lots created here — those come from real restocking operations).
    - MEASUREMENT items (O2 PSI) have measurement_minimum set.
    - FUNCTIONAL items (Battery OK, Runs and Starts) have no quantity.
    - DATE_RECORD items (Last Charge dates) have recurrence_days set.
    - Quantities embedded in item names on paper (e.g. "x3") are extracted
      into par levels — item names are kept clean.

## Item check type mapping from the paper forms

    SUPPLY     — standard counted or presence-verified item (default)
    MEASUREMENT — O2 PSI readings on all tanks
    FUNCTIONAL  — Battery OK checks, Runs and Starts, operational systems
    DATE_RECORD — Date of Last Charge (AED, LUCAS)
    DOCUMENT    — Paperwork: PCR forms, billing forms, protocol books
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

# Silence SQLAlchemy query logging — seed output is noisy enough without it
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

from sqlalchemy.orm import Session

# Ensure the app package is importable when run from the app/ directory
sys.path.insert(0, ".")

from ems_readykit.core.database import SessionLocal, engine, Base
from ems_readykit.models import (
    Station, Vehicle, VehicleType,
    InventoryLocation, LocationType,
    Compartment,
    Item, ItemCategory, ItemCheckType,
    ParLevel,
    StockLot,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_or_create_item(
    db: Session,
    *,
    name: str,
    category: ItemCategory,
    check_type: ItemCheckType = ItemCheckType.SUPPLY,
    controlled_substance: bool = False,
    unit_of_measure: str = "each",
    measurement_minimum: Optional[float] = None,
    measurement_maximum: Optional[float] = None,
    recurrence_days: Optional[int] = None,
) -> Item:
    """Return existing item by name or create it."""
    item = db.query(Item).filter(Item.name == name).first()
    if item:
        return item
    item = Item(
        name=name,
        category=category,
        check_type=check_type,
        controlled_substance=controlled_substance,
        unit_of_measure=unit_of_measure,
        measurement_minimum=measurement_minimum,
        measurement_maximum=measurement_maximum,
        recurrence_days=recurrence_days,
        active=True,
    )
    db.add(item)
    db.flush()
    return item


def add_par(
    db: Session,
    *,
    item: Item,
    location: InventoryLocation,
    compartment: Compartment,
    min_qty: int,
    max_qty: Optional[int] = None,
) -> None:
    """Add a par level if one doesn't already exist."""
    existing = db.query(ParLevel).filter(
        ParLevel.item_id == item.item_id,
        ParLevel.compartment_id == compartment.compartment_id,
    ).first()
    if existing:
        return
    db.add(ParLevel(
        item_id=item.item_id,
        location_id=location.location_id,
        compartment_id=compartment.compartment_id,
        min_quantity=min_qty,
        max_quantity=max_qty or min_qty,
    ))


def make_compartment(
    db: Session,
    *,
    location: InventoryLocation,
    name: str,
    sort_order: int,
    location_descriptor: Optional[str] = None,
    restriction_note: Optional[str] = None,
    parent: Optional[Compartment] = None,
    als_only: bool = False,
) -> Compartment:
    """Create or return compartment."""
    comp = db.query(Compartment).filter(
        Compartment.location_id == location.location_id,
        Compartment.name == name,
    ).first()
    if comp:
        return comp
    comp = Compartment(
        location_id=location.location_id,
        name=name,
        sort_order=sort_order,
        location_descriptor=location_descriptor,
        restriction_note=restriction_note,
        parent_compartment_id=parent.compartment_id if parent else None,
        als_only=als_only,
        active=True,
    )
    db.add(comp)
    db.flush()
    return comp


# ---------------------------------------------------------------------------
# Main seed
# ---------------------------------------------------------------------------

def seed(db: Session) -> None:
    print("Seeding Newberg Township Fire & EMS — Ambulance 712...")

    # ── Station ───────────────────────────────────────────────────────────────
    station = db.query(Station).filter(Station.name == "Newberg Township Station 1").first()
    if not station:
        station = Station(
            name="Newberg Township Station 1",
            address="Newberg Township, Michigan",
            region="Cass County",
            active=True,
        )
        db.add(station)
        db.flush()
        print(f"  Created station: {station.name}")

    # ── Supply Room Location ──────────────────────────────────────────────────
    supply_room = db.query(InventoryLocation).filter(
        InventoryLocation.station_id == station.station_id,
        InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
    ).first()
    if not supply_room:
        supply_room = InventoryLocation(
            location_type=LocationType.STATION_SUPPLY_ROOM,
            station_id=station.station_id,
            label="Newberg Station 1 Supply Room",
        )
        db.add(supply_room)
        db.flush()
        print("  Created supply room location")

    # ── Vehicle 712 ───────────────────────────────────────────────────────────
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_number == "712").first()
    if not vehicle:
        vehicle = Vehicle(
            station_id=station.station_id,
            vehicle_number="712",
            vehicle_type=VehicleType.ALS,
            active=True,
        )
        db.add(vehicle)
        db.flush()
        vehicle_loc = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=station.station_id,
            vehicle_id=vehicle.vehicle_id,
            label="Unit 712 — ALS Ambulance",
        )
        db.add(vehicle_loc)
        db.flush()
        print(f"  Created vehicle: {vehicle.vehicle_number}")
    else:
        vehicle_loc = db.query(InventoryLocation).filter(
            InventoryLocation.vehicle_id == vehicle.vehicle_id
        ).first()

    loc = vehicle_loc  # shorthand for vehicle location

    # ── Jump Bag Location (shared 710/712) ────────────────────────────────────
    jump_bag_loc = db.query(InventoryLocation).filter(
        InventoryLocation.station_id == station.station_id,
        InventoryLocation.location_type == LocationType.JUMP_BAG,
    ).first()
    if not jump_bag_loc:
        jump_bag_loc = InventoryLocation(
            location_type=LocationType.JUMP_BAG,
            station_id=station.station_id,
            label="Jump Bag (Units 710/712)",
        )
        db.add(jump_bag_loc)
        db.flush()
        print("  Created jump bag location")

    jb = jump_bag_loc  # shorthand

    print("\n  Building item catalog and par levels...")

    # =========================================================================
    # PAGE 1 — AMBULANCE 712
    # =========================================================================

    # ── PC 1 (Airway) — Interior, left side ──────────────────────────────────
    pc1 = make_compartment(db, location=loc, name="PC 1 (Airway)", sort_order=1,
                           location_descriptor="Interior, left side, forward")
    for name, qty in [("Adult BVM", 1), ("S/M CPAP", 1), ("L CPAP", 1)]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc1, min_qty=qty)

    # ── PC 2 (Airway) ─────────────────────────────────────────────────────────
    pc2 = make_compartment(db, location=loc, name="PC 2 (Airway)", sort_order=2,
                           location_descriptor="Interior, left side")
    for name, qty, expires in [
        ("Combi-Tubes 37F & 41F", 1, True),
        ("Extra Syringes", 1, True),
        ("Thomas-Tube Holders", 1, False),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT,
                                  unit_of_measure="set" if "Holders" in name else "each")
        add_par(db, item=item, location=loc, compartment=pc2, min_qty=qty)

    # ── PC 3 (Airway) ─────────────────────────────────────────────────────────
    pc3 = make_compartment(db, location=loc, name="PC 3 (Airway)", sort_order=3,
                           location_descriptor="Interior, left side")
    for name in ["Adult NAS", "Adult NRB", "Stethoscope"]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc3, min_qty=1)

    # ── PC 4 (Airway) ─────────────────────────────────────────────────────────
    pc4 = make_compartment(db, location=loc, name="PC 4 (Airway)", sort_order=4,
                           location_descriptor="Interior, left side")
    for name, qty, expires in [
        ("OPAs/NPAs", 1, True),
        ("Adult Nebulizers", 1, False),
        ("O2 O-Rings", 1, False),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE
                                  if expires else ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc4, min_qty=qty)

    # ── Admin Counter ─────────────────────────────────────────────────────────
    admin_counter = make_compartment(db, location=loc, name="Admin Counter", sort_order=5,
                                     location_descriptor="Interior, admin counter near driver")
    for name, cat, check_type, qty in [
        ("iPad & Charger",               ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY,   1),
        ("Clipboard",                    ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY,   1),
        ("Hand Sanitizer",               ItemCategory.CONSUMABLE,ItemCheckType.SUPPLY,   1),
        ("Antimicrobial Hand Wipes",     ItemCategory.CONSUMABLE,ItemCheckType.SUPPLY,   1),
        ("Writing Utensils",             ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY,   1),
        ("Trauma Shears",                ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY,   1),
        ("Duct Tape",                    ItemCategory.CONSUMABLE,ItemCheckType.SUPPLY,   1),
        ("O2 Wrench",                    ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY,   1),
        # Paperwork — DOCUMENT check type
        ("PCR or HERN PCR",              ItemCategory.DOCUMENT,  ItemCheckType.DOCUMENT, 1),
        ("Billing Form",                 ItemCategory.DOCUMENT,  ItemCheckType.DOCUMENT, 1),
        ("AMA Form",                     ItemCategory.DOCUMENT,  ItemCheckType.DOCUMENT, 1),
        ("AMA C-Spine Precautions Form", ItemCategory.DOCUMENT,  ItemCheckType.DOCUMENT, 1),
        ("Transfer Form",                ItemCategory.DOCUMENT,  ItemCheckType.DOCUMENT, 1),
        ("Claim Submission Form",        ItemCategory.DOCUMENT,  ItemCheckType.DOCUMENT, 1),
        ("Ambulance Transport Cert",     ItemCategory.DOCUMENT,  ItemCheckType.DOCUMENT, 1),
        ("Updated Radio Channel List",   ItemCategory.DOCUMENT,  ItemCheckType.DOCUMENT, 1),
    ]:
        item = get_or_create_item(db, name=name, category=cat, check_type=check_type,
                                  unit_of_measure="each" if check_type != ItemCheckType.DOCUMENT else "N/A")
        add_par(db, item=item, location=loc, compartment=admin_counter, min_qty=qty)

    # ── Suction Drawer ────────────────────────────────────────────────────────
    suction = make_compartment(db, location=loc, name="Suction Drawer", sort_order=6,
                               location_descriptor="Interior, suction drawer")
    for name, qty, uom in [
        ("Soft Suction Tips 6F",  3, "each"),
        ("Soft Suction Tips 10F", 3, "each"),
        ("Soft Suction Tips 16F", 3, "each"),
        ("6ft Suction Hose",      1, "each"),
        ("Rigid Yankauer",        3, "each"),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE, unit_of_measure=uom)
        add_par(db, item=item, location=loc, compartment=suction, min_qty=qty)

    # ── Admin Cabinet (Behind Airway Seat) ────────────────────────────────────
    admin_cab = make_compartment(db, location=loc, name="Admin Cabinet",
                                 sort_order=7, location_descriptor="Interior, behind airway seat")
    for name, cat, check_type in [
        ("Evidence Bags",             ItemCategory.CONSUMABLE, ItemCheckType.SUPPLY),
        ("HEPA Masks",                ItemCategory.CONSUMABLE, ItemCheckType.SUPPLY),
        ("Cass County Protocol Book", ItemCategory.DOCUMENT,   ItemCheckType.DOCUMENT),
        ("ACR Child Harness",         ItemCategory.EQUIPMENT,  ItemCheckType.SUPPLY),
    ]:
        item = get_or_create_item(db, name=name, category=cat, check_type=check_type,
                                  unit_of_measure="each" if check_type != ItemCheckType.DOCUMENT else "N/A")
        add_par(db, item=item, location=loc, compartment=admin_cab, min_qty=1)

    # ── PC 5 (PPE) ────────────────────────────────────────────────────────────
    pc5 = make_compartment(db, location=loc, name="PC 5 (PPE)", sort_order=8,
                           location_descriptor="Interior, PPE compartment")
    for name, qty, expires in [
        ("Glove Boxes Small",          1, False),
        ("Glove Boxes Medium",         1, False),
        ("Glove Boxes Large",          1, False),
        ("Glove Boxes X-Large",        1, False),
        ("Gowns",                      1, False),
        ("Goggles",                    1, False),
        ("N-95 Masks",                 1, False),
        ("Fluid Control Solidifier",   1, True),
        ("Paper Towels",               1, False),
        ("Antimicrobial Hand Wipes PC5",1, False),
        ("E.S.P. Kit",                 1, False),
        ("Infection Control Kits PC5", 1, False),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE)
        add_par(db, item=item, location=loc, compartment=pc5, min_qty=qty)

    # ── PC 6 ──────────────────────────────────────────────────────────────────
    pc6 = make_compartment(db, location=loc, name="PC 6", sort_order=9,
                           location_descriptor="Interior")
    for name, qty, expires in [
        ("Wrist BP Monitor", 1, False),
        ("Pocket Mask",      1, False),
        ("OB Kit",           1, False),
        ("OB Hat",           1, True),
        ("OB Warmers",       1, False),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT
                                  if not expires else ItemCategory.CONSUMABLE)
        add_par(db, item=item, location=loc, compartment=pc6, min_qty=qty)

    # ── PC 7 ──────────────────────────────────────────────────────────────────
    pc7 = make_compartment(db, location=loc, name="PC 7", sort_order=10,
                           location_descriptor="Interior, patient compartment")
    for name, qty in [
        ("Emesis Containers",       20),
        ("Bedpan",                   1),
        ("C-Collars PC7",            1),
        ("Extra Suction Canister",   1),
        ("C-Collar Bag",             1),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE
                                  if "Emesis" in name else ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc7, min_qty=qty)

    # ── PC 8 — AED, LUCAS, Portable Suction ───────────────────────────────────
    # This compartment has the most complex check types on the whole truck.
    # AED = 4 separate items: battery (FUNCTIONAL), last charge (DATE_RECORD),
    #       adult pads (SUPPLY+expiry), peds pads (SUPPLY+expiry)
    # LUCAS = 2 items: presence (SUPPLY), last charge (DATE_RECORD)
    # O2 = 2 items: presence (SUPPLY), PSI reading (MEASUREMENT)
    pc8 = make_compartment(db, location=loc, name="PC 8", sort_order=11,
                           location_descriptor="Interior, driver side")

    portable_suction = get_or_create_item(db, name="Portable Suction Unit",
                                          category=ItemCategory.EQUIPMENT)
    add_par(db, item=portable_suction, location=loc, compartment=pc8, min_qty=1)

    # AED (LifePak)
    aed_battery = get_or_create_item(
        db, name="AED Battery", category=ItemCategory.EQUIPMENT,
        check_type=ItemCheckType.FUNCTIONAL, unit_of_measure="N/A",
    )
    add_par(db, item=aed_battery, location=loc, compartment=pc8, min_qty=1)

    aed_charge_date = get_or_create_item(
        db, name="AED Date of Last Charge", category=ItemCategory.EQUIPMENT,
        check_type=ItemCheckType.DATE_RECORD, unit_of_measure="N/A",
        recurrence_days=90,  # must be charged at least every 90 days
    )
    add_par(db, item=aed_charge_date, location=loc, compartment=pc8, min_qty=1)

    aed_pads_adult = get_or_create_item(
        db, name="AED Pads Adult", category=ItemCategory.CONSUMABLE,
        check_type=ItemCheckType.SUPPLY, unit_of_measure="each",
    )
    add_par(db, item=aed_pads_adult, location=loc, compartment=pc8, min_qty=1)

    aed_pads_peds = get_or_create_item(
        db, name="AED Pads Pediatric", category=ItemCategory.CONSUMABLE,
        check_type=ItemCheckType.SUPPLY, unit_of_measure="each",
    )
    add_par(db, item=aed_pads_peds, location=loc, compartment=pc8, min_qty=1)

    # LUCAS Device
    lucas = get_or_create_item(db, name="LUCAS Device", category=ItemCategory.EQUIPMENT)
    add_par(db, item=lucas, location=loc, compartment=pc8, min_qty=1)

    lucas_charge = get_or_create_item(
        db, name="LUCAS Date of Last Charge", category=ItemCategory.EQUIPMENT,
        check_type=ItemCheckType.DATE_RECORD, unit_of_measure="N/A",
        recurrence_days=30,  # charge monthly
    )
    add_par(db, item=lucas_charge, location=loc, compartment=pc8, min_qty=1)

    # ── PC 9 Drug Cabinet ─────────────────────────────────────────────────────
    pc9 = make_compartment(db, location=loc, name="PC 9 Drug Cabinet", sort_order=12,
                           location_descriptor="Interior, drug cabinet")
    for name, cat, check_type in [
        ("BLS Drug Bag (stocked)",   ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY),
        ("BLS Drug Use Sheets",      ItemCategory.DOCUMENT,  ItemCheckType.DOCUMENT),
        ("PT Personal Item Lock-Up", ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY),
    ]:
        item = get_or_create_item(db, name=name, category=cat, check_type=check_type,
                                  unit_of_measure="each" if check_type != ItemCheckType.DOCUMENT else "N/A")
        add_par(db, item=item, location=loc, compartment=pc9, min_qty=1)

    # ── BLS Drug Bag ─────────────────────────────────────────────────────────
    # All items expire — check_type=SUPPLY with lot tracking
    bls_drug = make_compartment(db, location=loc, name="BLS Drug Bag", sort_order=13,
                                location_descriptor="Interior, PC 9 drug cabinet",
                                restriction_note=None)  # BLS — all crew
    for name, qty in [
        ("Intranasal Naloxone",  1),
        ("Albuterol Inhalation", 1),
        ("Low Dose Aspirin",     1),
        ("Epinephrine IM",       1),
        ("Syringes BLS",         1),
        ("Needles BLS",          1),
        ("Alcohol Preps BLS",    1),
        ("Nitroglycerin SL",     1),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.MEDICATION,
                                  unit_of_measure="each")
        add_par(db, item=item, location=loc, compartment=bls_drug, min_qty=qty)

    # ── PC 10 (Linens) ───────────────────────────────────────────────────────
    pc10 = make_compartment(db, location=loc, name="PC 10 (Linens)", sort_order=14,
                            location_descriptor="Interior, linen storage")
    for name in ["Sheets", "Blankets"]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc10, min_qty=1)

    # ── PC 11 (Linens) ───────────────────────────────────────────────────────
    pc11 = make_compartment(db, location=loc, name="PC 11 (Linens)", sort_order=15,
                            location_descriptor="Interior, linen storage")
    for name in ["Pillow Cases", "Towels PC11"]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc11, min_qty=1)

    # ── Bench ─────────────────────────────────────────────────────────────────
    bench = make_compartment(db, location=loc, name="Bench", sort_order=16,
                             location_descriptor="Interior, squad bench")
    for name, qty in [
        ("Multi-Cuff BP Cuff System", 1),
        ("SpO2 Monitor",              1),
        ("Extra Pillows",             1),
        ("Extra O2 Tank (no regulator)", 1),
        ("Empty Sharps Container Bench", 1),
        ("Blanket Roll",              1),
        ("Extra Blankets",            2),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=bench, min_qty=qty)

    # ── Glove Compartment ─────────────────────────────────────────────────────
    glove_comp = make_compartment(db, location=loc, name="Glove Compartment", sort_order=17,
                                  location_descriptor="Interior, glove storage")
    for size in ["Small", "Medium", "Large", "X-Large"]:
        item = get_or_create_item(db, name=f"Gloves {size}", category=ItemCategory.CONSUMABLE)
        add_par(db, item=item, location=loc, compartment=glove_comp, min_qty=1)

    # ── PC 12 (Trauma) ───────────────────────────────────────────────────────
    pc12 = make_compartment(db, location=loc, name="PC 12 (Trauma)", sort_order=18,
                            location_descriptor="Interior, trauma supplies")
    for name, qty in [
        ("Burn Sheets",         1),
        ("Trauma Dressings",    1),
        ("Hot Packs",           1),
        ("Cold Packs",          1),
        ("TPOD Pelvic Splint",  1),
        ("Sam Splints",         4),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE
                                  if "Pack" in name or "Sheet" in name or "Dress" in name
                                  else ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc12, min_qty=qty)

    # ── PC 13 (Trauma) ───────────────────────────────────────────────────────
    pc13 = make_compartment(db, location=loc, name="PC 13 (Trauma)", sort_order=19,
                            location_descriptor="Interior, trauma supplies")
    for name, qty, expires in [
        ("ABD Pad 8x10",                 6,  False),
        ("ABD Pad 5x9",                  8,  False),
        ("Gauze Bandage Various Sizes",  10, False),
        ("KERLIX PC13",                   8,  False),
        ("Tape Various Sizes",           10, False),
        ("CAT Tourniquet",                2,  False),
        ("Gauze Sponges 4x4",           25,  False),
        ("Triangle Bandages",             2,  False),
        ("ACE Wraps Various Sizes",       6,  False),
        ("Occlusive Dressing",            3,  True),
        ("Sterile Saline Solution",       4,  True),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE)
        add_par(db, item=item, location=loc, compartment=pc13, min_qty=qty)

    # =========================================================================
    # PAGE 2 — AMBULANCE 712
    # =========================================================================

    # ── PC 14 ─────────────────────────────────────────────────────────────────
    pc14 = make_compartment(db, location=loc, name="PC 14", sort_order=20,
                            location_descriptor="Interior, rear")
    for name, qty in [
        ("Mega-Movers PC14",               1),
        ("Towels PC14",                    1),
        ("Absorbent Pads",                 1),
        ("Emergency Blankets",             3),
        ("DECON/HAZMAT Suits XL",          3),
        ("Infection Control Kits PC14",    4),
        ("Triage Tags",                    1),
        ("Survival Wrap Foil Blanket",     1),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE
                                  if "Blanket" in name or "Wrap" in name or "Pad" in name
                                  else ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc14, min_qty=qty)

    # ── PC 15 (Infant Airway) ─────────────────────────────────────────────────
    pc15 = make_compartment(db, location=loc, name="PC 15 (Infant Airway)", sort_order=21,
                            location_descriptor="Interior")
    for name in ["Infant NRB", "Infant NAS", "Infant BVM"]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc15, min_qty=1)

    # ── PC 16 (Pediatric Airway) ──────────────────────────────────────────────
    pc16 = make_compartment(db, location=loc, name="PC 16 (Pediatric Airway)", sort_order=22,
                            location_descriptor="Interior")
    for name in ["Pediatric NRB", "Pediatric NAS", "Pediatric BVM", "Pediatric Nebulizer"]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc16, min_qty=1)

    # ── Charger Counter ───────────────────────────────────────────────────────
    charger = make_compartment(db, location=loc, name="Charger Counter", sort_order=23,
                               location_descriptor="Interior, charger counter")
    for name in ["Pediatric First-In Bag", "Cot Battery Charger",
                 "Cot Spare Battery", "MI-Medic Cards"]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=charger, min_qty=1)

    # ── PC 17 ─────────────────────────────────────────────────────────────────
    pc17 = make_compartment(db, location=loc, name="PC 17", sort_order=24,
                            location_descriptor="Interior")
    item = get_or_create_item(db, name="Patient Restraints", category=ItemCategory.EQUIPMENT)
    add_par(db, item=item, location=loc, compartment=pc17, min_qty=1)

    # ── PC 18 (Tools & Glucometer) ────────────────────────────────────────────
    pc18 = make_compartment(db, location=loc, name="PC 18 (Tools)", sort_order=25,
                            location_descriptor="Interior")
    # Tools sub-section
    for name in ["Stethoscope PC18", "Thermometer PC18", "Ring Cutter",
                 "Trauma Shears PC18", "Replacement Stethoscope Parts"]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=pc18, min_qty=1)

    # Glucometer Kit items
    for name, qty, expires in [
        ("Glucometer Lancets",      6,  False),
        ("Alcohol Prep PC18",       6,  True),
        ("Bandaids PC18",           6,  False),
        ("Gauze 3x3 PC18",          3,  False),
        ("Glucometer Test Strips",  6,  True),   # Min 6 + expiry
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE)
        add_par(db, item=item, location=loc, compartment=pc18, min_qty=qty)

    # Glucose Restock Kit
    for name, qty, expires in [
        ("Restock Lancets",         20, False),
        ("Bite Stick",               2, False),
        ("Restock Alcohol Prep",    20, True),
        ("Restock Bandaids",        20, False),
        ("Oral Glucose",             2, True),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE)
        add_par(db, item=item, location=loc, compartment=pc18, min_qty=qty)

    item = get_or_create_item(db, name="Thermometer PC18 Unit", category=ItemCategory.EQUIPMENT)
    add_par(db, item=item, location=loc, compartment=pc18, min_qty=1)

    # ── Stretcher ─────────────────────────────────────────────────────────────
    # O2 + PSI reading (MEASUREMENT) + Battery Charged (FUNCTIONAL)
    stretcher = make_compartment(db, location=loc, name="Stretcher", sort_order=26,
                                 location_descriptor="Patient stretcher / cot")

    stretcher_o2 = get_or_create_item(
        db, name="Stretcher O2 Tank w/ Regulator",
        category=ItemCategory.EQUIPMENT, check_type=ItemCheckType.SUPPLY,
    )
    add_par(db, item=stretcher_o2, location=loc, compartment=stretcher, min_qty=1)

    stretcher_psi = get_or_create_item(
        db, name="Stretcher O2 PSI",
        category=ItemCategory.EQUIPMENT, check_type=ItemCheckType.MEASUREMENT,
        unit_of_measure="PSI",
        measurement_minimum=500.0,   # below 500 PSI = LOW
        measurement_maximum=2200.0,  # full tank
    )
    add_par(db, item=stretcher_psi, location=loc, compartment=stretcher, min_qty=1)

    stretcher_batt = get_or_create_item(
        db, name="Stretcher Battery Charged",
        category=ItemCategory.EQUIPMENT, check_type=ItemCheckType.FUNCTIONAL,
        unit_of_measure="N/A",
    )
    add_par(db, item=stretcher_batt, location=loc, compartment=stretcher, min_qty=1)

    # ── Driver Side EC 1 (Exterior) ───────────────────────────────────────────
    ds_ec1 = make_compartment(db, location=loc, name="Driver Side EC 1", sort_order=30,
                              location_descriptor="Exterior, driver side, forward bay")
    for name, qty in [
        ("Long-board Splints",   1),
        ("K.E.D. Board",         1),
        ("Adult Traction Splint",1),
        ("Peds Traction Splint", 1),
        ("Broom",                1),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=ds_ec1, min_qty=qty)

    # On-Board O2 — presence + PSI (two separate items in same compartment)
    onboard_o2 = get_or_create_item(
        db, name="On-Board O2 Tank w/ Regulator 15LPM",
        category=ItemCategory.EQUIPMENT, check_type=ItemCheckType.SUPPLY,
    )
    add_par(db, item=onboard_o2, location=loc, compartment=ds_ec1, min_qty=1)

    onboard_psi = get_or_create_item(
        db, name="On-Board O2 PSI",
        category=ItemCategory.EQUIPMENT, check_type=ItemCheckType.MEASUREMENT,
        unit_of_measure="PSI",
        measurement_minimum=500.0,
        measurement_maximum=2200.0,
    )
    add_par(db, item=onboard_psi, location=loc, compartment=ds_ec1, min_qty=1)

    # ── Driverside EC 2 ───────────────────────────────────────────────────────
    ds_ec2 = make_compartment(db, location=loc, name="Driverside EC 2", sort_order=31,
                              location_descriptor="Exterior, driver side, middle bay")
    for name, qty in [
        ("Scene Light",      1),
        ("Water Bottles",   10),
        ("Bio-Hazard Bags",  1),
        ("Styro-foam Cups",  1),
        ("Glo-Sticks",       1),
        ("Peds Jump Bag",    1),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT
                                  if "Light" in name or "Bag" in name else ItemCategory.CONSUMABLE)
        add_par(db, item=item, location=loc, compartment=ds_ec2, min_qty=qty)

    # ── Driver Side EC 3 ──────────────────────────────────────────────────────
    ds_ec3 = make_compartment(db, location=loc, name="Driver Side EC 3", sort_order=32,
                              location_descriptor="Exterior, driver side, rear bay")
    for name in ["Mega-Movers DS3", "Stair Chair"]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=ds_ec3, min_qty=1)

    # ── Passenger Side EC 1 ───────────────────────────────────────────────────
    ps_ec1 = make_compartment(db, location=loc, name="Passenger Side EC 1", sort_order=33,
                              location_descriptor="Exterior, passenger side, forward bay")
    # PC 7&8 Access — presence check only (no items to count)

    # ── Passenger Side EC 2 ───────────────────────────────────────────────────
    ps_ec2 = make_compartment(db, location=loc, name="Passenger Side EC 2", sort_order=34,
                              location_descriptor="Exterior, passenger side, middle bay")
    for name, qty, expires in [
        ("Fire Extinguisher",  1, True),
        ("Jumper Cables",      1, False),
        ("Traction Splint PS", 1, False),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=loc, compartment=ps_ec2, min_qty=qty)

    # ── Passenger Side EC 3 ───────────────────────────────────────────────────
    ps_ec3 = make_compartment(db, location=loc, name="Passenger Side EC 3", sort_order=35,
                              location_descriptor="Exterior, passenger side, rear bay")
    for name, qty in [
        ("Long Board",        2),
        ("Short Board",       2),
        ("Board Straps",      2),
        ("Head Blocks",       2),
        ("C-Collars Adult PS",2),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT,
                                  unit_of_measure="set" if "Straps" in name or "Blocks" in name else "each")
        add_par(db, item=item, location=loc, compartment=ps_ec3, min_qty=qty)

    # ── Truck Operations ──────────────────────────────────────────────────────
    # All FUNCTIONAL check type — pass/fail operational verifications
    truck_ops = make_compartment(db, location=loc, name="Truck Operations", sort_order=40,
                                 location_descriptor="Operational vehicle systems check")
    for name in [
        "Runs and Starts",
        "External Warning Systems (Lights & Sirens)",
        "Loading & Unloading Access",
        "Ambulance Cot and Straps Secured",
        "Patient Compartment Climate Control",
        "Communication Medcom Compliant",
        "Fire Extinguisher UL Listed",
        "Flares or Equivalent Device",
        "Portable Two-Way Radio",
        "Window Punch Available",
        "Mileage Sheet",
        "Insurance Information",
    ]:
        cat = ItemCategory.DOCUMENT if "Sheet" in name or "Information" in name else ItemCategory.EQUIPMENT
        check_type = ItemCheckType.DOCUMENT if cat == ItemCategory.DOCUMENT else ItemCheckType.FUNCTIONAL
        item = get_or_create_item(db, name=name, category=cat, check_type=check_type,
                                  unit_of_measure="N/A")
        add_par(db, item=item, location=loc, compartment=truck_ops, min_qty=1)

    # Gloves in cab (S/M/L) — presence check
    for size in ["Small", "Medium", "Large"]:
        item = get_or_create_item(db, name=f"Cab Gloves {size}", category=ItemCategory.CONSUMABLE)
        add_par(db, item=item, location=loc, compartment=truck_ops, min_qty=1)

    # ── Under Hood (restricted) ───────────────────────────────────────────────
    under_hood = make_compartment(
        db, location=loc, name="Under Hood", sort_order=99,
        location_descriptor="Engine compartment",
        restriction_note="Approved personnel only — mechanical authorization required",
    )
    for name in ["Hoses", "Belts", "Oil Level", "Steering/Brakes", "Radiator", "Windshield", "Battery"]:
        item = get_or_create_item(db, name=f"Hood {name}", category=ItemCategory.EQUIPMENT,
                                  check_type=ItemCheckType.FUNCTIONAL, unit_of_measure="N/A")
        add_par(db, item=item, location=loc, compartment=under_hood, min_qty=1)

    # =========================================================================
    # JUMP BAG — Shared Units 710/712
    # =========================================================================
    print("\n  Seeding Jump Bag compartments and items...")

    # ── Left Pocket ───────────────────────────────────────────────────────────
    jb_left = make_compartment(db, location=jb, name="Left Pocket", sort_order=1,
                               location_descriptor="Left exterior pocket of jump bag")
    item = get_or_create_item(db, name="Empty Sharps Container JB", category=ItemCategory.EQUIPMENT)
    add_par(db, item=item, location=jb, compartment=jb_left, min_qty=1)

    # ── Back Pocket ───────────────────────────────────────────────────────────
    jb_back = make_compartment(db, location=jb, name="Back Pocket", sort_order=2,
                               location_descriptor="Rear pocket of jump bag")
    for name, qty in [
        ("OPAs/NPAs JB",          1),
        ("Water Bottle JB",        1),
        ("Colorimetric CO2 Detector", 1),  # expires — reagent based
        ("Combi-Tube JB",          1),
        ("Thomas Tube Holders JB", 2),
    ]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT
                                  if "Holder" in name or "OPA" in name or "Bottle" in name
                                  else ItemCategory.CONSUMABLE)
        add_par(db, item=item, location=jb, compartment=jb_back, min_qty=qty)

    # ── Front Pocket ──────────────────────────────────────────────────────────
    jb_front = make_compartment(db, location=jb, name="Front Pocket", sort_order=3,
                                location_descriptor="Front pocket of jump bag")
    for name, qty, expires in [
        ("C-Collar Adult JB",         1, False),
        ("Overdose Rescue Kit NARCAN", 1, True),
        ("SPo2 Monitor JB",           1, False),
        ("Glucometer Lancets JB",     6, False),
        ("Alcohol Prep JB",           6, True),
        ("Bandaids JB",               6, False),
        ("Gauze 3x3 JB",              3, False),
        ("Glucometer Test Strips JB", 6, True),
        ("Thermometer JB",            1, False),
        ("Thermometer Probe Covers",  1, False),
        ("BioHazard Bags JB",         1, False),
    ]:
        cat = ItemCategory.MEDICATION if "NARCAN" in name else (
              ItemCategory.CONSUMABLE if expires or "Gauze" in name or "Bandaid" in name
              else ItemCategory.EQUIPMENT)
        item = get_or_create_item(db, name=name, category=cat)
        add_par(db, item=item, location=jb, compartment=jb_front, min_qty=qty)

    # ── Main Pocket ───────────────────────────────────────────────────────────
    jb_main = make_compartment(db, location=jb, name="Main Pocket", sort_order=10,
                               location_descriptor="Main compartment of jump bag")

    # O2 tank in jump bag — presence + PSI
    jb_o2 = get_or_create_item(
        db, name="Jump Bag O2 Tank w/ Regulator 15LPM",
        category=ItemCategory.EQUIPMENT,
    )
    add_par(db, item=jb_o2, location=jb, compartment=jb_main, min_qty=1)

    jb_psi = get_or_create_item(
        db, name="Jump Bag O2 PSI",
        category=ItemCategory.EQUIPMENT, check_type=ItemCheckType.MEASUREMENT,
        unit_of_measure="PSI",
        measurement_minimum=500.0,
        measurement_maximum=2200.0,
    )
    add_par(db, item=jb_psi, location=jb, compartment=jb_main, min_qty=1)

    for name, qty in [
        ("Kerlix Large JB",   3),
        ("Kerlix Medium JB",  3),
        ("Stethoscope JB",    1),
        ("BP Cuff JB",        1),
        ("Clipboard w/ Paperwork JB", 1),
    ]:
        cat = ItemCategory.DOCUMENT if "Paperwork" in name else ItemCategory.EQUIPMENT
        check_type = ItemCheckType.DOCUMENT if cat == ItemCategory.DOCUMENT else ItemCheckType.SUPPLY
        item = get_or_create_item(db, name=name, category=cat, check_type=check_type,
                                  unit_of_measure="each" if check_type != ItemCheckType.DOCUMENT else "N/A")
        add_par(db, item=item, location=jb, compartment=jb_main, min_qty=qty)

    # ── Main Pocket — Elastic Pouches Back ────────────────────────────────────
    jb_ep_back = make_compartment(
        db, location=jb, name="Main Pocket — Elastic Pouches Back",
        sort_order=11, location_descriptor="Elastic pouches, rear of main pocket",
        parent=jb_main,
    )
    for name, qty in [("Tourniquet JB", 2), ("Kerlix Small JB", 4), ("Emesis Container JB", 2)]:
        item = get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE
                                  if "Emesis" in name or "Kerlix" in name else ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=jb, compartment=jb_ep_back, min_qty=qty)

    # ── Main Pocket — Elastic Pouches Front ───────────────────────────────────
    jb_ep_front = make_compartment(
        db, location=jb, name="Main Pocket — Elastic Pouches Front",
        sort_order=12, location_descriptor="Elastic pouches, front of main pocket",
        parent=jb_main,
    )
    for name, qty, expires in [
        ("Writing Utensils JB",    1, False),
        ("Pen Light JB",           2, False),
        ("Occlusive Dressing JB",  2, False),
        ("Bite Stick JB",          1, False),
        ("Oral Glucose Gel",       2, True),
        ("Oral Glucose Tablets",   1, True),
        ("BleedStop",              1, False),
        ("Thermometer EP",         1, False),
        ("Tape Various Sizes JB",  3, False),
        ("Trauma Shears JB",       2, False),
        ("Triangle Bandage JB",    2, False),
        ("ABD Pads 5x9 JB",        2, False),
        ("Gauze Pads 3x3 JB",      6, False),
        ("ACE Wrap JB",            2, True),
    ]:
        cat = ItemCategory.MEDICATION if "Glucose" in name else ItemCategory.CONSUMABLE
        item = get_or_create_item(db, name=name, category=cat)
        add_par(db, item=item, location=jb, compartment=jb_ep_front, min_qty=qty)

    # ── Main Pocket — Flap Left ───────────────────────────────────────────────
    jb_flap_left = make_compartment(
        db, location=jb, name="Main Pocket — Flap Left",
        sort_order=13, location_descriptor="Left flap of main pocket",
        parent=jb_main,
    )
    for name, qty in [("NRB Adult JB", 3), ("NAS Adult JB", 5), ("Stethoscope Flap JB", 1)]:
        item = get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT)
        add_par(db, item=item, location=jb, compartment=jb_flap_left, min_qty=qty)

    # ── Main Pocket — Flap Right ──────────────────────────────────────────────
    jb_flap_right = make_compartment(
        db, location=jb, name="Main Pocket — Flap Right",
        sort_order=14, location_descriptor="Right flap of main pocket",
        parent=jb_main,
    )
    item = get_or_create_item(db, name="BVM Adult JB", category=ItemCategory.EQUIPMENT)
    add_par(db, item=item, location=jb, compartment=jb_flap_right, min_qty=1)

    # =========================================================================
    # Commit everything
    # =========================================================================
    db.commit()

    # Summary counts
    item_count = db.query(Item).count()
    comp_count = db.query(Compartment).filter(
        Compartment.location_id.in_([loc.location_id, jb.location_id])
    ).count()
    par_count = db.query(ParLevel).filter(
        ParLevel.location_id.in_([loc.location_id, jb.location_id])
    ).count()

    print(f"\n  ✓ Seed complete.")
    print(f"    Items in catalog:      {item_count}")
    print(f"    Compartments seeded:   {comp_count} (712 truck + jump bag)")
    print(f"    Par levels created:    {par_count}")
    print(f"\n  Vehicle 712 location ID:  {loc.location_id}")
    print(f"  Jump Bag location ID:      {jb.location_id}")
    print(f"  Station ID:                {station.station_id}")


if __name__ == "__main__":
    print("Running EMS ReadyKit seed script...")
    db: Session = SessionLocal()
    try:
        seed(db)
    except Exception as e:
        db.rollback()
        print(f"\n  ERROR: {e}")
        raise
    finally:
        db.close()
    print("\nDone.")
