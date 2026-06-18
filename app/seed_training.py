"""
seed_training.py
Ensures the Newberg Training Station exists in the database.

This script is called by startup.sh on EVERY deploy, including production.
It is fully idempotent — if the training station already exists, it updates
any changed fields (e.g. color) and adds any missing compartments or par
levels, but never duplicates or overwrites real check data.

Purpose:
    Safe playground for crew training. Crew members can learn EMS ReadyKit
    here without touching real Unit 712 compliance records. Nothing in this
    station affects operational compliance reporting.

Station:
    Name:   Newberg Training Station
    Color:  #e65100 (orange — immediately distinct from real blue stations)

Vehicles:
    Training Unit A (BLS)   + Training Jump Bag A
    Training Unit B (BLS)   + Training Jump Bag B

Compartments per ambulance (9 — vs 26 on Unit 712):
    PC 8             AED + LUCAS: FUNCTIONAL (priority), DATE_RECORD, EXPIRY_DATE
    PC 1 (Airway)    SUPPLY
    Admin Counter    SUPPLY + DOCUMENT
    PC 5 (PPE)       SUPPLY consumables
    PC 13 (Trauma)   SUPPLY consumables (~1/3 quantities)
    Stretcher        MEASUREMENT (O2 PSI, priority) + FUNCTIONAL
    Driver Side EC1  MEASUREMENT (on-board O2 PSI) + SUPPLY
    Truck Operations FUNCTIONAL + DOCUMENT, requires_full_check
    Under Hood       FUNCTIONAL, requires_full_check

Compartments per jump bag (2):
    Main Pocket      MEASUREMENT (O2 PSI, priority) + SUPPLY + DOCUMENT
    Front Pocket     SUPPLY consumables

A training check takes ~5 minutes. All 6 check types are exercised.

Members:
    jinniyah@gmail.com (Administrator) — always seeded.
    Other members added via Settings → Team Members.

Usage:
    cd app
    python seed_training.py
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

sys.path.insert(0, ".")

from sqlalchemy.orm import Session  # noqa: E402

from ems_readykit.core.database import SessionLocal  # noqa: E402
from ems_readykit.models import (  # noqa: E402
    Compartment,
    InventoryLocation,
    Item,
    ItemCategory,
    ItemCheckType,
    LocationType,
    ParLevel,
    Station,
    StationMember,
    Vehicle,
    VehicleType,
)

# ---------------------------------------------------------------------------
# Helpers (duplicated from seed.py so this script is fully self-contained)
# ---------------------------------------------------------------------------


def get_or_create_item(
    db: Session,
    *,
    name: str,
    category: ItemCategory,
    check_type: ItemCheckType = ItemCheckType.SUPPLY,
    unit_of_measure: str = "each",
    measurement_minimum: Optional[float] = None,
    measurement_maximum: Optional[float] = None,
    recurrence_days: Optional[int] = None,
) -> Item:
    item = db.query(Item).filter(Item.name == name).first()
    if item:
        item.check_type = check_type
        item.recurrence_days = recurrence_days
        item.unit_of_measure = unit_of_measure
        if measurement_minimum is not None:
            item.measurement_minimum = measurement_minimum
        if measurement_maximum is not None:
            item.measurement_maximum = measurement_maximum
        return item
    item = Item(
        name=name,
        category=category,
        check_type=check_type,
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
    priority_check: bool = False,
    priority_question: Optional[str] = None,
) -> None:
    existing = (
        db.query(ParLevel)
        .filter(
            ParLevel.item_id == item.item_id,
            ParLevel.compartment_id == compartment.compartment_id,
        )
        .first()
    )
    if existing:
        existing.priority_check = priority_check
        existing.priority_question = priority_question or None
        return
    db.add(
        ParLevel(
            item_id=item.item_id,
            location_id=location.location_id,
            compartment_id=compartment.compartment_id,
            min_quantity=min_qty,
            max_quantity=max_qty or min_qty,
            priority_check=priority_check,
            priority_question=priority_question or None,
        )
    )


def make_compartment(
    db: Session,
    *,
    location: InventoryLocation,
    name: str,
    sort_order: int,
    location_descriptor: Optional[str] = None,
    requires_full_check: bool = False,
) -> Compartment:
    comp = (
        db.query(Compartment)
        .filter(
            Compartment.location_id == location.location_id,
            Compartment.name == name,
        )
        .first()
    )
    if comp:
        comp.requires_full_check = requires_full_check
        return comp
    comp = Compartment(
        location_id=location.location_id,
        name=name,
        sort_order=sort_order,
        location_descriptor=location_descriptor,
        active=True,
        requires_full_check=requires_full_check,
    )
    db.add(comp)
    db.flush()
    return comp


def get_or_create_jump_bag_location(
    db: Session, *, station_id: int, label: str
) -> tuple[InventoryLocation, bool]:
    loc = (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.station_id == station_id,
            InventoryLocation.location_type == LocationType.JUMP_BAG,
            InventoryLocation.label == label,
        )
        .first()
    )
    if loc:
        return loc, False
    loc = InventoryLocation(
        location_type=LocationType.JUMP_BAG,
        station_id=station_id,
        label=label,
    )
    db.add(loc)
    db.flush()
    return loc, True


# ---------------------------------------------------------------------------
# Training ambulance inventory
# ---------------------------------------------------------------------------


def build_training_ambulance(db: Session, loc: InventoryLocation) -> None:
    """9 compartments covering all check types. ~1/3 par quantities. Idempotent."""

    # ── PC 8 — AED + LUCAS priority items ─────────────────────────────────────
    pc8 = make_compartment(
        db,
        location=loc,
        name="PC 8",
        sort_order=1,
        location_descriptor="Interior, driver side — AED and LUCAS",
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="AED Battery",
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.FUNCTIONAL,
            unit_of_measure="N/A",
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
        priority_check=True,
        priority_question="AED shows READY?",
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="AED Date of Last Charge",
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.DATE_RECORD,
            unit_of_measure="N/A",
            recurrence_days=90,
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="AED Pads Adult",
            category=ItemCategory.CONSUMABLE,
            check_type=ItemCheckType.EXPIRY_DATE,
            unit_of_measure="N/A",
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="AED Pads Pediatric",
            category=ItemCategory.CONSUMABLE,
            check_type=ItemCheckType.EXPIRY_DATE,
            unit_of_measure="N/A",
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="LUCAS Device",
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.FUNCTIONAL,
            unit_of_measure="N/A",
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
        priority_check=True,
        priority_question="LUCAS shows READY?",
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="LUCAS Date of Last Charge",
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.DATE_RECORD,
            unit_of_measure="N/A",
            recurrence_days=30,
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
    )
    add_par(
        db,
        item=get_or_create_item(
            db, name="Portable Suction Unit", category=ItemCategory.EQUIPMENT
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
    )

    # ── PC 1 (Airway) — SUPPLY ─────────────────────────────────────────────────
    pc1 = make_compartment(
        db,
        location=loc,
        name="PC 1 (Airway)",
        sort_order=2,
        location_descriptor="Interior, left side, forward — airway equipment",
    )
    for name in ["Adult BVM", "Adult NAS", "Adult NRB"]:
        add_par(
            db,
            item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
            location=loc,
            compartment=pc1,
            min_qty=1,
        )

    # ── Admin Counter — SUPPLY + DOCUMENT ──────────────────────────────────────
    admin_counter = make_compartment(
        db,
        location=loc,
        name="Admin Counter",
        sort_order=3,
        location_descriptor="Interior, admin counter near driver",
    )
    for name, cat, ct in [
        ("iPad & Charger", ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY),
        ("Hand Sanitizer", ItemCategory.CONSUMABLE, ItemCheckType.SUPPLY),
        ("Trauma Shears", ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY),
        ("O2 Wrench", ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY),
        ("PCR or HERN PCR", ItemCategory.DOCUMENT, ItemCheckType.DOCUMENT),
        ("Billing Form", ItemCategory.DOCUMENT, ItemCheckType.DOCUMENT),
        ("Updated Radio Channel List", ItemCategory.DOCUMENT, ItemCheckType.DOCUMENT),
    ]:
        uom = "N/A" if ct == ItemCheckType.DOCUMENT else "each"
        add_par(
            db,
            item=get_or_create_item(
                db, name=name, category=cat, check_type=ct, unit_of_measure=uom
            ),
            location=loc,
            compartment=admin_counter,
            min_qty=1,
        )

    # ── PC 5 (PPE) — SUPPLY consumables ───────────────────────────────────────
    pc5 = make_compartment(
        db,
        location=loc,
        name="PC 5 (PPE)",
        sort_order=4,
        location_descriptor="Interior, PPE compartment",
    )
    for name in [
        "Glove Boxes Medium",
        "Glove Boxes Large",
        "Gowns",
        "N-95 Masks",
        "Goggles",
    ]:
        add_par(
            db,
            item=get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE),
            location=loc,
            compartment=pc5,
            min_qty=1,
        )

    # ── PC 13 (Trauma) — SUPPLY consumables, ~1/3 quantities ──────────────────
    pc13 = make_compartment(
        db,
        location=loc,
        name="PC 13 (Trauma)",
        sort_order=5,
        location_descriptor="Interior, trauma supplies",
    )
    for name, qty in [
        ("ABD Pad 8x10", 2),
        ("Gauze Bandage Various Sizes", 3),
        ("KERLIX PC13", 3),
        ("Tape Various Sizes", 3),
        ("CAT Tourniquet", 1),
        ("Gauze Sponges 4x4", 8),
        ("Triangle Bandages", 1),
        ("Sterile Saline Solution", 1),
    ]:
        add_par(
            db,
            item=get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE),
            location=loc,
            compartment=pc13,
            min_qty=qty,
        )

    # ── Stretcher — MEASUREMENT (O2 PSI priority) + FUNCTIONAL ────────────────
    stretcher = make_compartment(
        db,
        location=loc,
        name="Stretcher",
        sort_order=6,
        location_descriptor="Patient stretcher / cot",
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="Stretcher O2 PSI",
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.MEASUREMENT,
            unit_of_measure="PSI",
            measurement_minimum=500.0,
            measurement_maximum=2200.0,
        ),
        location=loc,
        compartment=stretcher,
        min_qty=1,
        priority_check=True,
        priority_question="Stretcher O2 above 500 PSI?",
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="Stretcher Battery Charged",
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.FUNCTIONAL,
            unit_of_measure="N/A",
        ),
        location=loc,
        compartment=stretcher,
        min_qty=1,
    )

    # ── Driver Side EC 1 — MEASUREMENT (on-board O2 PSI) + SUPPLY ─────────────
    ds_ec1 = make_compartment(
        db,
        location=loc,
        name="Driver Side EC 1",
        sort_order=7,
        location_descriptor="Exterior, driver side, forward bay",
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="On-Board O2 PSI",
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.MEASUREMENT,
            unit_of_measure="PSI",
            measurement_minimum=500.0,
            measurement_maximum=2200.0,
        ),
        location=loc,
        compartment=ds_ec1,
        min_qty=1,
    )
    for name in ["Long-board Splints", "Fire Extinguisher"]:
        add_par(
            db,
            item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
            location=loc,
            compartment=ds_ec1,
            min_qty=1,
        )

    # ── Truck Operations — FUNCTIONAL + DOCUMENT, requires_full_check ──────────
    truck_ops = make_compartment(
        db,
        location=loc,
        name="Truck Operations",
        sort_order=8,
        location_descriptor="Operational vehicle systems check",
        requires_full_check=True,
    )
    for name in [
        "Runs and Starts",
        "External Warning Systems (Lights & Sirens)",
        "Ambulance Cot and Straps Secured",
        "Communication Medcom Compliant",
        "Fire Extinguisher UL Listed",
        "Portable Two-Way Radio",
        "Mileage Sheet",
        "Insurance Information",
    ]:
        cat = (
            ItemCategory.DOCUMENT
            if any(x in name for x in ["Sheet", "Information"])
            else ItemCategory.EQUIPMENT
        )
        ct = (
            ItemCheckType.DOCUMENT
            if cat == ItemCategory.DOCUMENT
            else ItemCheckType.FUNCTIONAL
        )
        add_par(
            db,
            item=get_or_create_item(
                db, name=name, category=cat, check_type=ct, unit_of_measure="N/A"
            ),
            location=loc,
            compartment=truck_ops,
            min_qty=1,
        )
    for size in ["Small", "Medium", "Large"]:
        add_par(
            db,
            item=get_or_create_item(
                db, name=f"Cab Gloves {size}", category=ItemCategory.CONSUMABLE
            ),
            location=loc,
            compartment=truck_ops,
            min_qty=1,
        )

    # ── Under Hood — FUNCTIONAL, requires_full_check ───────────────────────────
    under_hood = make_compartment(
        db,
        location=loc,
        name="Under Hood",
        sort_order=9,
        location_descriptor="Engine compartment",
        requires_full_check=True,
    )
    for name in ["Hoses", "Belts", "Oil Level", "Radiator", "Battery"]:
        add_par(
            db,
            item=get_or_create_item(
                db,
                name=f"Hood {name}",
                category=ItemCategory.EQUIPMENT,
                check_type=ItemCheckType.FUNCTIONAL,
                unit_of_measure="N/A",
            ),
            location=loc,
            compartment=under_hood,
            min_qty=1,
        )


# ---------------------------------------------------------------------------
# Training jump bag inventory
# ---------------------------------------------------------------------------


def build_training_jump_bag(db: Session, jb: InventoryLocation) -> None:
    """2 compartments. Idempotent."""

    # ── Main Pocket — O2 PSI priority + SUPPLY ────────────────────────────────
    jb_main = make_compartment(
        db,
        location=jb,
        name="Main Pocket",
        sort_order=1,
        location_descriptor="Main compartment of jump bag",
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="Jump Bag O2 PSI",
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.MEASUREMENT,
            unit_of_measure="PSI",
            measurement_minimum=500.0,
            measurement_maximum=2200.0,
        ),
        location=jb,
        compartment=jb_main,
        min_qty=1,
        priority_check=True,
        priority_question="Jump Bag O2 above 500 PSI?",
    )
    add_par(
        db,
        item=get_or_create_item(
            db,
            name="Jump Bag O2 Tank w/ Regulator 15LPM",
            category=ItemCategory.EQUIPMENT,
        ),
        location=jb,
        compartment=jb_main,
        min_qty=1,
    )
    for name, qty in [
        ("Kerlix Large JB", 1),
        ("Stethoscope JB", 1),
        ("BP Cuff JB", 1),
        ("Clipboard w/ Paperwork JB", 1),
        ("Tourniquet JB", 1),
        ("BVM Adult JB", 1),
    ]:
        cat = ItemCategory.DOCUMENT if "Paperwork" in name else ItemCategory.EQUIPMENT
        ct = (
            ItemCheckType.DOCUMENT
            if cat == ItemCategory.DOCUMENT
            else ItemCheckType.SUPPLY
        )
        uom = "N/A" if ct == ItemCheckType.DOCUMENT else "each"
        add_par(
            db,
            item=get_or_create_item(
                db, name=name, category=cat, check_type=ct, unit_of_measure=uom
            ),
            location=jb,
            compartment=jb_main,
            min_qty=qty,
        )

    # ── Front Pocket — consumable SUPPLY ──────────────────────────────────────
    jb_front = make_compartment(
        db,
        location=jb,
        name="Front Pocket",
        sort_order=2,
        location_descriptor="Front pocket of jump bag",
    )
    for name, qty in [
        ("C-Collar Adult JB", 1),
        ("Overdose Rescue Kit NARCAN", 1),
        ("Glucometer Lancets JB", 2),
        ("Alcohol Prep JB", 2),
        ("Bandaids JB", 2),
        ("Gauze 3x3 JB", 1),
        ("Glucometer Test Strips JB", 2),
        ("Thermometer JB", 1),
        ("Trauma Shears JB", 1),
        ("Occlusive Dressing JB", 1),
    ]:
        cat = (
            ItemCategory.MEDICATION
            if "NARCAN" in name
            else (
                ItemCategory.CONSUMABLE
                if any(x in name for x in ["Gauze", "Bandaid", "Prep", "Strips"])
                else ItemCategory.EQUIPMENT
            )
        )
        add_par(
            db,
            item=get_or_create_item(db, name=name, category=cat),
            location=jb,
            compartment=jb_front,
            min_qty=qty,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def seed_training(db: Session) -> None:
    print("Ensuring Newberg Training Station exists...")

    BOOTSTRAP_ADMIN = "jinniyah@gmail.com"
    BOOTSTRAP_NAME = "Jinni Allen"
    SEED_USER = "seed_training.py"

    # ── Station ────────────────────────────────────────────────────────────────
    training = (
        db.query(Station).filter(Station.name == "Newberg Training Station").first()
    )
    if not training:
        training = Station(
            name="Newberg Training Station",
            address="Newberg Township, Michigan",
            region="Cass County — Training",
            active=True,
            primary_color="#e65100",
        )
        db.add(training)
        db.flush()
        print("  Created Newberg Training Station")
    else:
        if training.primary_color != "#e65100":
            training.primary_color = "#e65100"
            print("  Updated training station color to #e65100 (orange)")
        else:
            print("  Training station already exists — checking vehicles...")

    # ── Supply room (required by app — created but not featured in training) ───
    training_supply = (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.station_id == training.station_id,
            InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
        )
        .first()
    )
    if not training_supply:
        training_supply = InventoryLocation(
            location_type=LocationType.STATION_SUPPLY_ROOM,
            station_id=training.station_id,
            label="Training Supply Room",
        )
        db.add(training_supply)
        db.flush()
        print("  Created Training Supply Room")

    # ── Training Unit A ────────────────────────────────────────────────────────
    v_train_a = (
        db.query(Vehicle)
        .filter(
            Vehicle.vehicle_number == "TRAIN-A",
            Vehicle.station_id == training.station_id,
        )
        .first()
    )
    if not v_train_a:
        v_train_a = Vehicle(
            station_id=training.station_id,
            vehicle_number="TRAIN-A",
            vehicle_type=VehicleType.BLS,
            active=True,
        )
        db.add(v_train_a)
        db.flush()
        loc_train_a = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=training.station_id,
            vehicle_id=v_train_a.vehicle_id,
            label="Training Unit A",
        )
        db.add(loc_train_a)
        db.flush()
        print("  Created Training Unit A (BLS)")
    else:
        loc_train_a = (
            db.query(InventoryLocation)
            .filter(InventoryLocation.vehicle_id == v_train_a.vehicle_id)
            .first()
        )

    # ── Training Unit B ────────────────────────────────────────────────────────
    v_train_b = (
        db.query(Vehicle)
        .filter(
            Vehicle.vehicle_number == "TRAIN-B",
            Vehicle.station_id == training.station_id,
        )
        .first()
    )
    if not v_train_b:
        v_train_b = Vehicle(
            station_id=training.station_id,
            vehicle_number="TRAIN-B",
            vehicle_type=VehicleType.BLS,
            active=True,
        )
        db.add(v_train_b)
        db.flush()
        loc_train_b = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=training.station_id,
            vehicle_id=v_train_b.vehicle_id,
            label="Training Unit B",
        )
        db.add(loc_train_b)
        db.flush()
        print("  Created Training Unit B (BLS)")
    else:
        loc_train_b = (
            db.query(InventoryLocation)
            .filter(InventoryLocation.vehicle_id == v_train_b.vehicle_id)
            .first()
        )

    # ── Jump bags ──────────────────────────────────────────────────────────────
    def get_or_create_jb(label: str) -> tuple[InventoryLocation, bool]:
        loc = (
            db.query(InventoryLocation)
            .filter(
                InventoryLocation.station_id == training.station_id,
                InventoryLocation.location_type == LocationType.JUMP_BAG,
                InventoryLocation.label == label,
            )
            .first()
        )
        if loc:
            return loc, False
        loc = InventoryLocation(
            location_type=LocationType.JUMP_BAG,
            station_id=training.station_id,
            label=label,
        )
        db.add(loc)
        db.flush()
        return loc, True

    jb_train_a, created_a = get_or_create_jb("Training Jump Bag A")
    if created_a:
        print("  Created Training Jump Bag A")

    jb_train_b, created_b = get_or_create_jb("Training Jump Bag B")
    if created_b:
        print("  Created Training Jump Bag B")

    # ── Inventory ──────────────────────────────────────────────────────────────
    build_training_ambulance(db, loc_train_a)
    build_training_ambulance(db, loc_train_b)
    build_training_jump_bag(db, jb_train_a)
    build_training_jump_bag(db, jb_train_b)

    # ── Bootstrap admin membership ─────────────────────────────────────────────
    existing = (
        db.query(StationMember)
        .filter(
            StationMember.station_id == training.station_id,
            StationMember.user_id == BOOTSTRAP_ADMIN,
        )
        .first()
    )
    if not existing:
        db.add(
            StationMember(
                station_id=training.station_id,
                user_id=BOOTSTRAP_ADMIN,
                preferred_name=BOOTSTRAP_NAME,
                role="Administrator",
                assigned_by=SEED_USER,
                active=True,
            )
        )
        print(f"  Assigned {BOOTSTRAP_ADMIN} as Administrator")
    elif not existing.active:
        existing.active = True
        print(f"  Re-activated {BOOTSTRAP_ADMIN}")

    # ── Flag non-supply items (belt-and-suspenders, safe to re-run) ───────────
    _non_supply = [
        "AED Battery",
        "AED Pads Adult",
        "AED Pads Pediatric",
        "AED Date of Last Charge",
        "LUCAS Device",
        "LUCAS Date of Last Charge",
    ]
    for _name in _non_supply:
        _item = db.query(Item).filter(Item.name == _name).first()
        if _item and _item.station_supply:
            _item.station_supply = False

    db.commit()

    # ── Summary ────────────────────────────────────────────────────────────────
    loc_ids = [
        loc_train_a.location_id,
        loc_train_b.location_id,
        jb_train_a.location_id,
        jb_train_b.location_id,
    ]
    comp_count = (
        db.query(Compartment).filter(Compartment.location_id.in_(loc_ids)).count()
    )
    par_count = db.query(ParLevel).filter(ParLevel.location_id.in_(loc_ids)).count()

    print(f"""
  ✓ Training station ready.

  Newberg Training Station (orange — #e65100):
    Station ID:           {training.station_id}
    Training Unit A:      location_id={loc_train_a.location_id}
    Training Unit B:      location_id={loc_train_b.location_id}
    Training Jump Bag A:  location_id={jb_train_a.location_id}
    Training Jump Bag B:  location_id={jb_train_b.location_id}
    Compartments (all):   {comp_count}
    Par levels (all):     {par_count}

  Training walkthrough (~5 min):
    Step 1 — Select "Newberg Training Station" → "Training Unit A"
    Step 2 — Confirm priority items: AED READY, LUCAS READY, Stretcher O2 PSI
    Step 3 — 9 compartments. Count trauma supplies, check AED pads expiry
              dates, enter O2 PSI readings, confirm Truck Operations items.
    Step 4 — Reconcile any flagged items
    Step 5 — Submit — try adding notes, see the confirmation screen
""")


if __name__ == "__main__":
    print("Running training station seed...")
    db: Session = SessionLocal()
    try:
        seed_training(db)
    except Exception as e:
        db.rollback()
        print(f"\n  ERROR: {e}")
        raise
    finally:
        db.close()
    print("Done.")
