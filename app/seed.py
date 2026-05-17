"""
seed.py
Seed data for EMS ReadyKit development database.

Stations seeded:
    1. Newberg Township Station 1 — Ambulance 712 (BLS) + Jump Bag
    2. Marcellus Township Station 1 — Ambulance 540 (ALS)

The item catalog is SHARED across all stations. The same item (e.g. "Adult BVM")
appears in both trucks — but each truck has its own compartments and its own
par levels. This mirrors real EMS operations: the same supply list, different
physical locations on different vehicles.

Usage:
    cd app
    python seed.py

Prerequisites:
    alembic upgrade head must have been run first.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

from sqlalchemy.orm import Session

sys.path.insert(0, ".")

from ems_readykit.core.database import SessionLocal
from ems_readykit.models import (
    Station, Vehicle, VehicleType,
    InventoryLocation, LocationType,
    Compartment,
    Item, ItemCategory, ItemCheckType,
    ParLevel,
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
    item = db.query(Item).filter(Item.name == name).first()
    if item:
        return item
    item = Item(
        name=name, category=category, check_type=check_type,
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
    db: Session, *, item: Item, location: InventoryLocation,
    compartment: Compartment, min_qty: int, max_qty: Optional[int] = None,
) -> None:
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
    db: Session, *, location: InventoryLocation, name: str, sort_order: int,
    location_descriptor: Optional[str] = None,
    restriction_note: Optional[str] = None,
    parent: Optional[Compartment] = None,
    als_only: bool = False,
) -> Compartment:
    comp = db.query(Compartment).filter(
        Compartment.location_id == location.location_id,
        Compartment.name == name,
    ).first()
    if comp:
        return comp
    comp = Compartment(
        location_id=location.location_id, name=name, sort_order=sort_order,
        location_descriptor=location_descriptor, restriction_note=restriction_note,
        parent_compartment_id=parent.compartment_id if parent else None,
        als_only=als_only, active=True,
    )
    db.add(comp)
    db.flush()
    return comp


# ---------------------------------------------------------------------------
# Shared compartment builder
# Builds the standard Ambulance 712 inventory layout on ANY location.
# Called for both 712 (BLS) and 540 (ALS) so they share the same structure.
# ALS-specific compartments (PC 9 ALS Drug Cabinet) are only added when
# is_als=True; BLS drug bag is only added when is_als=False.
# ---------------------------------------------------------------------------

def build_ambulance_inventory(db: Session, loc: InventoryLocation, is_als: bool) -> None:
    """Create all compartments and par levels for a standard ambulance location."""

    # ── PC 1 (Airway) ─────────────────────────────────────────────────────────
    pc1 = make_compartment(db, location=loc, name="PC 1 (Airway)", sort_order=1,
                           location_descriptor="Interior, left side, forward")
    for name, qty in [("Adult BVM", 1), ("S/M CPAP", 1), ("L CPAP", 1)]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=pc1, min_qty=qty)

    # ── PC 2 (Airway) ─────────────────────────────────────────────────────────
    pc2 = make_compartment(db, location=loc, name="PC 2 (Airway)", sort_order=2,
                           location_descriptor="Interior, left side")
    for name, uom in [("Combi-Tubes 37F & 41F", "each"), ("Extra Syringes", "each"),
                      ("Thomas-Tube Holders", "set")]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT,
                                            unit_of_measure=uom),
                location=loc, compartment=pc2, min_qty=1)

    # ── PC 3 (Airway) ─────────────────────────────────────────────────────────
    pc3 = make_compartment(db, location=loc, name="PC 3 (Airway)", sort_order=3,
                           location_descriptor="Interior, left side")
    for name in ["Adult NAS", "Adult NRB", "Stethoscope"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=pc3, min_qty=1)

    # ── PC 4 (Airway) ─────────────────────────────────────────────────────────
    pc4 = make_compartment(db, location=loc, name="PC 4 (Airway)", sort_order=4,
                           location_descriptor="Interior, left side")
    for name, cat in [("OPAs/NPAs", ItemCategory.CONSUMABLE),
                      ("Adult Nebulizers", ItemCategory.EQUIPMENT),
                      ("O2 O-Rings", ItemCategory.EQUIPMENT)]:
        add_par(db, item=get_or_create_item(db, name=name, category=cat),
                location=loc, compartment=pc4, min_qty=1)

    # ── Admin Counter ─────────────────────────────────────────────────────────
    admin_counter = make_compartment(db, location=loc, name="Admin Counter", sort_order=5,
                                     location_descriptor="Interior, admin counter near driver")
    for name, cat, ct, qty in [
        ("iPad & Charger",               ItemCategory.EQUIPMENT,  ItemCheckType.SUPPLY,   1),
        ("Clipboard",                    ItemCategory.EQUIPMENT,  ItemCheckType.SUPPLY,   1),
        ("Hand Sanitizer",               ItemCategory.CONSUMABLE, ItemCheckType.SUPPLY,   1),
        ("Antimicrobial Hand Wipes",     ItemCategory.CONSUMABLE, ItemCheckType.SUPPLY,   1),
        ("Writing Utensils",             ItemCategory.EQUIPMENT,  ItemCheckType.SUPPLY,   1),
        ("Trauma Shears",                ItemCategory.EQUIPMENT,  ItemCheckType.SUPPLY,   1),
        ("Duct Tape",                    ItemCategory.CONSUMABLE, ItemCheckType.SUPPLY,   1),
        ("O2 Wrench",                    ItemCategory.EQUIPMENT,  ItemCheckType.SUPPLY,   1),
        ("PCR or HERN PCR",              ItemCategory.DOCUMENT,   ItemCheckType.DOCUMENT, 1),
        ("Billing Form",                 ItemCategory.DOCUMENT,   ItemCheckType.DOCUMENT, 1),
        ("AMA Form",                     ItemCategory.DOCUMENT,   ItemCheckType.DOCUMENT, 1),
        ("AMA C-Spine Precautions Form", ItemCategory.DOCUMENT,   ItemCheckType.DOCUMENT, 1),
        ("Transfer Form",                ItemCategory.DOCUMENT,   ItemCheckType.DOCUMENT, 1),
        ("Claim Submission Form",        ItemCategory.DOCUMENT,   ItemCheckType.DOCUMENT, 1),
        ("Ambulance Transport Cert",     ItemCategory.DOCUMENT,   ItemCheckType.DOCUMENT, 1),
        ("Updated Radio Channel List",   ItemCategory.DOCUMENT,   ItemCheckType.DOCUMENT, 1),
    ]:
        uom = "N/A" if ct == ItemCheckType.DOCUMENT else "each"
        add_par(db, item=get_or_create_item(db, name=name, category=cat, check_type=ct,
                                            unit_of_measure=uom),
                location=loc, compartment=admin_counter, min_qty=qty)

    # ── Suction Drawer ────────────────────────────────────────────────────────
    suction = make_compartment(db, location=loc, name="Suction Drawer", sort_order=6,
                               location_descriptor="Interior, suction drawer")
    for name, qty in [("Soft Suction Tips 6F", 3), ("Soft Suction Tips 10F", 3),
                      ("Soft Suction Tips 16F", 3), ("6ft Suction Hose", 1), ("Rigid Yankauer", 3)]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE),
                location=loc, compartment=suction, min_qty=qty)

    # ── Admin Cabinet ─────────────────────────────────────────────────────────
    admin_cab = make_compartment(db, location=loc, name="Admin Cabinet", sort_order=7,
                                 location_descriptor="Interior, behind airway seat")
    for name, cat, ct in [
        ("Evidence Bags",             ItemCategory.CONSUMABLE, ItemCheckType.SUPPLY),
        ("HEPA Masks",                ItemCategory.CONSUMABLE, ItemCheckType.SUPPLY),
        ("Cass County Protocol Book", ItemCategory.DOCUMENT,   ItemCheckType.DOCUMENT),
        ("ACR Child Harness",         ItemCategory.EQUIPMENT,  ItemCheckType.SUPPLY),
    ]:
        uom = "N/A" if ct == ItemCheckType.DOCUMENT else "each"
        add_par(db, item=get_or_create_item(db, name=name, category=cat, check_type=ct,
                                            unit_of_measure=uom),
                location=loc, compartment=admin_cab, min_qty=1)

    # ── PC 5 (PPE) ────────────────────────────────────────────────────────────
    pc5 = make_compartment(db, location=loc, name="PC 5 (PPE)", sort_order=8,
                           location_descriptor="Interior, PPE compartment")
    for name in ["Glove Boxes Small", "Glove Boxes Medium", "Glove Boxes Large",
                 "Glove Boxes X-Large", "Gowns", "Goggles", "N-95 Masks",
                 "Fluid Control Solidifier", "Paper Towels", "Antimicrobial Hand Wipes PC5",
                 "E.S.P. Kit", "Infection Control Kits PC5"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE),
                location=loc, compartment=pc5, min_qty=1)

    # ── PC 6 ──────────────────────────────────────────────────────────────────
    pc6 = make_compartment(db, location=loc, name="PC 6", sort_order=9,
                           location_descriptor="Interior")
    for name, cat in [("Wrist BP Monitor", ItemCategory.EQUIPMENT),
                      ("Pocket Mask", ItemCategory.EQUIPMENT),
                      ("OB Kit", ItemCategory.EQUIPMENT),
                      ("OB Hat", ItemCategory.CONSUMABLE),
                      ("OB Warmers", ItemCategory.EQUIPMENT)]:
        add_par(db, item=get_or_create_item(db, name=name, category=cat),
                location=loc, compartment=pc6, min_qty=1)

    # ── PC 7 ──────────────────────────────────────────────────────────────────
    pc7 = make_compartment(db, location=loc, name="PC 7", sort_order=10,
                           location_descriptor="Interior, patient compartment")
    for name, qty in [("Emesis Containers", 20), ("Bedpan", 1), ("C-Collars PC7", 1),
                      ("Extra Suction Canister", 1), ("C-Collar Bag", 1)]:
        cat = ItemCategory.CONSUMABLE if "Emesis" in name else ItemCategory.EQUIPMENT
        add_par(db, item=get_or_create_item(db, name=name, category=cat),
                location=loc, compartment=pc7, min_qty=qty)

    # ── PC 8 — AED, LUCAS, Portable Suction ───────────────────────────────────
    pc8 = make_compartment(db, location=loc, name="PC 8", sort_order=11,
                           location_descriptor="Interior, driver side")
    add_par(db, item=get_or_create_item(db, name="Portable Suction Unit",
                                        category=ItemCategory.EQUIPMENT),
            location=loc, compartment=pc8, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="AED Battery",
                                        category=ItemCategory.EQUIPMENT,
                                        check_type=ItemCheckType.FUNCTIONAL, unit_of_measure="N/A"),
            location=loc, compartment=pc8, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="AED Date of Last Charge",
                                        category=ItemCategory.EQUIPMENT,
                                        check_type=ItemCheckType.DATE_RECORD,
                                        unit_of_measure="N/A", recurrence_days=90),
            location=loc, compartment=pc8, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="AED Pads Adult",
                                        category=ItemCategory.CONSUMABLE),
            location=loc, compartment=pc8, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="AED Pads Pediatric",
                                        category=ItemCategory.CONSUMABLE),
            location=loc, compartment=pc8, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="LUCAS Device",
                                        category=ItemCategory.EQUIPMENT),
            location=loc, compartment=pc8, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="LUCAS Date of Last Charge",
                                        category=ItemCategory.EQUIPMENT,
                                        check_type=ItemCheckType.DATE_RECORD,
                                        unit_of_measure="N/A", recurrence_days=30),
            location=loc, compartment=pc8, min_qty=1)

    # ── PC 9 — Drug Cabinet (BLS or ALS depending on unit type) ──────────────
    if is_als:
        # ALS Drug Cabinet — controlled substances, dual-signature required
        pc9 = make_compartment(db, location=loc, name="PC 9 ALS Drug Cabinet",
                               sort_order=12,
                               location_descriptor="Interior, ALS drug cabinet",
                               restriction_note="Dual signature required — ALS personnel only",
                               als_only=True)
        for name, cat, controlled in [
            ("ALS Drug Bag (stocked)",    ItemCategory.EQUIPMENT,  False),
            ("ALS Drug Use Sheets",       ItemCategory.DOCUMENT,   False),
            ("PT Personal Item Lock-Up",  ItemCategory.EQUIPMENT,  False),
            ("Morphine",                  ItemCategory.MEDICATION, True),
            ("Fentanyl",                  ItemCategory.MEDICATION, True),
            ("Midazolam",                 ItemCategory.MEDICATION, True),
            ("Diazepam",                  ItemCategory.MEDICATION, True),
        ]:
            ct = ItemCheckType.DOCUMENT if "Sheets" in name else ItemCheckType.SUPPLY
            uom = "N/A" if ct == ItemCheckType.DOCUMENT else "each"
            add_par(db, item=get_or_create_item(db, name=name, category=cat,
                                                check_type=ct, unit_of_measure=uom,
                                                controlled_substance=controlled),
                    location=loc, compartment=pc9, min_qty=1)

        # ALS Drug Bag contents
        als_drug = make_compartment(db, location=loc, name="ALS Drug Bag",
                                    sort_order=13,
                                    location_descriptor="Interior, PC 9 ALS drug cabinet",
                                    als_only=True)
        for name, controlled in [
            ("Intranasal Naloxone",   False),
            ("Albuterol Inhalation",  False),
            ("Low Dose Aspirin",      False),
            ("Epinephrine IM",        False),
            ("Adenosine",             False),
            ("Amiodarone",            False),
            ("Atropine",              False),
            ("Dopamine",              False),
            ("Sodium Bicarbonate",    False),
            ("Dextrose 50%",          False),
            ("Nitroglycerin SL",      False),
            ("Syringes BLS",          False),
            ("Needles BLS",           False),
            ("Alcohol Preps BLS",     False),
        ]:
            add_par(db, item=get_or_create_item(db, name=name,
                                                category=ItemCategory.MEDICATION,
                                                controlled_substance=controlled),
                    location=loc, compartment=als_drug, min_qty=1)
    else:
        # BLS Drug Cabinet — no controlled substances
        pc9 = make_compartment(db, location=loc, name="PC 9 BLS Drug Cabinet",
                               sort_order=12,
                               location_descriptor="Interior, BLS drug cabinet")
        for name, cat, ct in [
            ("BLS Drug Bag (stocked)",   ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY),
            ("BLS Drug Use Sheets",      ItemCategory.DOCUMENT,  ItemCheckType.DOCUMENT),
            ("PT Personal Item Lock-Up", ItemCategory.EQUIPMENT, ItemCheckType.SUPPLY),
        ]:
            uom = "N/A" if ct == ItemCheckType.DOCUMENT else "each"
            add_par(db, item=get_or_create_item(db, name=name, category=cat,
                                                check_type=ct, unit_of_measure=uom),
                    location=loc, compartment=pc9, min_qty=1)

        bls_drug = make_compartment(db, location=loc, name="BLS Drug Bag", sort_order=13,
                                    location_descriptor="Interior, PC 9 BLS drug cabinet")
        for name in ["Intranasal Naloxone", "Albuterol Inhalation", "Low Dose Aspirin",
                     "Epinephrine IM", "Syringes BLS", "Needles BLS",
                     "Alcohol Preps BLS", "Nitroglycerin SL"]:
            add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.MEDICATION),
                    location=loc, compartment=bls_drug, min_qty=1)

    # ── PC 10 (Linens) ───────────────────────────────────────────────────────
    pc10 = make_compartment(db, location=loc, name="PC 10 (Linens)", sort_order=14,
                            location_descriptor="Interior, linen storage")
    for name in ["Sheets", "Blankets"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=pc10, min_qty=1)

    # ── PC 11 (Linens) ───────────────────────────────────────────────────────
    pc11 = make_compartment(db, location=loc, name="PC 11 (Linens)", sort_order=15,
                            location_descriptor="Interior, linen storage")
    for name in ["Pillow Cases", "Towels PC11"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=pc11, min_qty=1)

    # ── Bench ─────────────────────────────────────────────────────────────────
    bench = make_compartment(db, location=loc, name="Bench", sort_order=16,
                             location_descriptor="Interior, squad bench")
    for name, qty in [("Multi-Cuff BP Cuff System", 1), ("SpO2 Monitor", 1),
                      ("Extra Pillows", 1), ("Extra O2 Tank (no regulator)", 1),
                      ("Empty Sharps Container Bench", 1), ("Blanket Roll", 1),
                      ("Extra Blankets", 2)]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=bench, min_qty=qty)

    # ── Glove Compartment ─────────────────────────────────────────────────────
    glove_comp = make_compartment(db, location=loc, name="Glove Compartment", sort_order=17,
                                  location_descriptor="Interior, glove storage")
    for size in ["Small", "Medium", "Large", "X-Large"]:
        add_par(db, item=get_or_create_item(db, name=f"Gloves {size}",
                                            category=ItemCategory.CONSUMABLE),
                location=loc, compartment=glove_comp, min_qty=1)

    # ── PC 12 (Trauma) ───────────────────────────────────────────────────────
    pc12 = make_compartment(db, location=loc, name="PC 12 (Trauma)", sort_order=18,
                            location_descriptor="Interior, trauma supplies")
    for name, qty in [("Burn Sheets", 1), ("Trauma Dressings", 1), ("Hot Packs", 1),
                      ("Cold Packs", 1), ("TPOD Pelvic Splint", 1), ("Sam Splints", 4)]:
        cat = (ItemCategory.CONSUMABLE if any(x in name for x in ["Pack", "Sheet", "Dress"])
               else ItemCategory.EQUIPMENT)
        add_par(db, item=get_or_create_item(db, name=name, category=cat),
                location=loc, compartment=pc12, min_qty=qty)

    # ── PC 13 (Trauma) ───────────────────────────────────────────────────────
    pc13 = make_compartment(db, location=loc, name="PC 13 (Trauma)", sort_order=19,
                            location_descriptor="Interior, trauma supplies")
    for name, qty in [
        ("ABD Pad 8x10", 6), ("ABD Pad 5x9", 8), ("Gauze Bandage Various Sizes", 10),
        ("KERLIX PC13", 8), ("Tape Various Sizes", 10), ("CAT Tourniquet", 2),
        ("Gauze Sponges 4x4", 25), ("Triangle Bandages", 2),
        ("ACE Wraps Various Sizes", 6), ("Occlusive Dressing", 3),
        ("Sterile Saline Solution", 4),
    ]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE),
                location=loc, compartment=pc13, min_qty=qty)

    # ── PC 14 ─────────────────────────────────────────────────────────────────
    pc14 = make_compartment(db, location=loc, name="PC 14", sort_order=20,
                            location_descriptor="Interior, rear")
    for name, qty in [
        ("Mega-Movers PC14", 1), ("Towels PC14", 1), ("Absorbent Pads", 1),
        ("Emergency Blankets", 3), ("DECON/HAZMAT Suits XL", 3),
        ("Infection Control Kits PC14", 4), ("Triage Tags", 1),
        ("Survival Wrap Foil Blanket", 1),
    ]:
        cat = (ItemCategory.CONSUMABLE if any(x in name for x in ["Blanket", "Wrap", "Pad"])
               else ItemCategory.EQUIPMENT)
        add_par(db, item=get_or_create_item(db, name=name, category=cat),
                location=loc, compartment=pc14, min_qty=qty)

    # ── PC 15 (Infant Airway) ─────────────────────────────────────────────────
    pc15 = make_compartment(db, location=loc, name="PC 15 (Infant Airway)", sort_order=21,
                            location_descriptor="Interior")
    for name in ["Infant NRB", "Infant NAS", "Infant BVM"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=pc15, min_qty=1)

    # ── PC 16 (Pediatric Airway) ──────────────────────────────────────────────
    pc16 = make_compartment(db, location=loc, name="PC 16 (Pediatric Airway)", sort_order=22,
                            location_descriptor="Interior")
    for name in ["Pediatric NRB", "Pediatric NAS", "Pediatric BVM", "Pediatric Nebulizer"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=pc16, min_qty=1)

    # ── Charger Counter ───────────────────────────────────────────────────────
    charger = make_compartment(db, location=loc, name="Charger Counter", sort_order=23,
                               location_descriptor="Interior, charger counter")
    for name in ["Pediatric First-In Bag", "Cot Battery Charger",
                 "Cot Spare Battery", "MI-Medic Cards"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=charger, min_qty=1)

    # ── PC 17 ─────────────────────────────────────────────────────────────────
    pc17 = make_compartment(db, location=loc, name="PC 17", sort_order=24,
                            location_descriptor="Interior")
    add_par(db, item=get_or_create_item(db, name="Patient Restraints",
                                        category=ItemCategory.EQUIPMENT),
            location=loc, compartment=pc17, min_qty=1)

    # ── PC 18 (Tools & Glucometer) ────────────────────────────────────────────
    pc18 = make_compartment(db, location=loc, name="PC 18 (Tools)", sort_order=25,
                            location_descriptor="Interior")
    for name in ["Stethoscope PC18", "Thermometer PC18", "Ring Cutter",
                 "Trauma Shears PC18", "Replacement Stethoscope Parts"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=pc18, min_qty=1)
    for name, qty in [("Glucometer Lancets", 6), ("Alcohol Prep PC18", 6),
                      ("Bandaids PC18", 6), ("Gauze 3x3 PC18", 3),
                      ("Glucometer Test Strips", 6), ("Restock Lancets", 20),
                      ("Bite Stick", 2), ("Restock Alcohol Prep", 20),
                      ("Restock Bandaids", 20), ("Oral Glucose", 2)]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.CONSUMABLE),
                location=loc, compartment=pc18, min_qty=qty)
    add_par(db, item=get_or_create_item(db, name="Thermometer PC18 Unit",
                                        category=ItemCategory.EQUIPMENT),
            location=loc, compartment=pc18, min_qty=1)

    # ── Stretcher ─────────────────────────────────────────────────────────────
    stretcher = make_compartment(db, location=loc, name="Stretcher", sort_order=26,
                                 location_descriptor="Patient stretcher / cot")
    add_par(db, item=get_or_create_item(db, name="Stretcher O2 Tank w/ Regulator",
                                        category=ItemCategory.EQUIPMENT),
            location=loc, compartment=stretcher, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="Stretcher O2 PSI",
                                        category=ItemCategory.EQUIPMENT,
                                        check_type=ItemCheckType.MEASUREMENT,
                                        unit_of_measure="PSI",
                                        measurement_minimum=500.0, measurement_maximum=2200.0),
            location=loc, compartment=stretcher, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="Stretcher Battery Charged",
                                        category=ItemCategory.EQUIPMENT,
                                        check_type=ItemCheckType.FUNCTIONAL, unit_of_measure="N/A"),
            location=loc, compartment=stretcher, min_qty=1)

    # ── Driver Side EC 1 ──────────────────────────────────────────────────────
    ds_ec1 = make_compartment(db, location=loc, name="Driver Side EC 1", sort_order=30,
                              location_descriptor="Exterior, driver side, forward bay")
    for name in ["Long-board Splints", "K.E.D. Board", "Adult Traction Splint",
                 "Peds Traction Splint", "Broom"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=ds_ec1, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="On-Board O2 Tank w/ Regulator 15LPM",
                                        category=ItemCategory.EQUIPMENT),
            location=loc, compartment=ds_ec1, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="On-Board O2 PSI",
                                        category=ItemCategory.EQUIPMENT,
                                        check_type=ItemCheckType.MEASUREMENT,
                                        unit_of_measure="PSI",
                                        measurement_minimum=500.0, measurement_maximum=2200.0),
            location=loc, compartment=ds_ec1, min_qty=1)

    # ── Driverside EC 2 ───────────────────────────────────────────────────────
    ds_ec2 = make_compartment(db, location=loc, name="Driverside EC 2", sort_order=31,
                              location_descriptor="Exterior, driver side, middle bay")
    for name, qty in [("Scene Light", 1), ("Water Bottles", 10), ("Bio-Hazard Bags", 1),
                      ("Styro-foam Cups", 1), ("Glo-Sticks", 1), ("Peds Jump Bag", 1)]:
        cat = (ItemCategory.EQUIPMENT if any(x in name for x in ["Light", "Bag"])
               else ItemCategory.CONSUMABLE)
        add_par(db, item=get_or_create_item(db, name=name, category=cat),
                location=loc, compartment=ds_ec2, min_qty=qty)

    # ── Driver Side EC 3 ──────────────────────────────────────────────────────
    ds_ec3 = make_compartment(db, location=loc, name="Driver Side EC 3", sort_order=32,
                              location_descriptor="Exterior, driver side, rear bay")
    for name in ["Mega-Movers DS3", "Stair Chair"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=ds_ec3, min_qty=1)

    # ── Passenger Side EC 1 ───────────────────────────────────────────────────
    make_compartment(db, location=loc, name="Passenger Side EC 1", sort_order=33,
                     location_descriptor="Exterior, passenger side, forward bay")

    # ── Passenger Side EC 2 ───────────────────────────────────────────────────
    ps_ec2 = make_compartment(db, location=loc, name="Passenger Side EC 2", sort_order=34,
                              location_descriptor="Exterior, passenger side, middle bay")
    for name in ["Fire Extinguisher", "Jumper Cables", "Traction Splint PS"]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=loc, compartment=ps_ec2, min_qty=1)

    # ── Passenger Side EC 3 ───────────────────────────────────────────────────
    ps_ec3 = make_compartment(db, location=loc, name="Passenger Side EC 3", sort_order=35,
                              location_descriptor="Exterior, passenger side, rear bay")
    for name, qty in [("Long Board", 2), ("Short Board", 2), ("Board Straps", 2),
                      ("Head Blocks", 2), ("C-Collars Adult PS", 2)]:
        uom = "set" if name in ("Board Straps", "Head Blocks") else "each"
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT,
                                            unit_of_measure=uom),
                location=loc, compartment=ps_ec3, min_qty=qty)

    # ── Truck Operations ──────────────────────────────────────────────────────
    truck_ops = make_compartment(db, location=loc, name="Truck Operations", sort_order=40,
                                 location_descriptor="Operational vehicle systems check")
    for name in [
        "Runs and Starts", "External Warning Systems (Lights & Sirens)",
        "Loading & Unloading Access", "Ambulance Cot and Straps Secured",
        "Patient Compartment Climate Control", "Communication Medcom Compliant",
        "Fire Extinguisher UL Listed", "Flares or Equivalent Device",
        "Portable Two-Way Radio", "Window Punch Available",
        "Mileage Sheet", "Insurance Information",
    ]:
        cat = (ItemCategory.DOCUMENT if any(x in name for x in ["Sheet", "Information"])
               else ItemCategory.EQUIPMENT)
        ct = ItemCheckType.DOCUMENT if cat == ItemCategory.DOCUMENT else ItemCheckType.FUNCTIONAL
        add_par(db, item=get_or_create_item(db, name=name, category=cat,
                                            check_type=ct, unit_of_measure="N/A"),
                location=loc, compartment=truck_ops, min_qty=1)
    for size in ["Small", "Medium", "Large"]:
        add_par(db, item=get_or_create_item(db, name=f"Cab Gloves {size}",
                                            category=ItemCategory.CONSUMABLE),
                location=loc, compartment=truck_ops, min_qty=1)

    # ── Under Hood (restricted) ───────────────────────────────────────────────
    under_hood = make_compartment(
        db, location=loc, name="Under Hood", sort_order=99,
        location_descriptor="Engine compartment",
        restriction_note="Approved personnel only — mechanical authorization required",
    )
    for name in ["Hoses", "Belts", "Oil Level", "Steering/Brakes",
                 "Radiator", "Windshield", "Battery"]:
        add_par(db, item=get_or_create_item(db, name=f"Hood {name}",
                                            category=ItemCategory.EQUIPMENT,
                                            check_type=ItemCheckType.FUNCTIONAL,
                                            unit_of_measure="N/A"),
                location=loc, compartment=under_hood, min_qty=1)


def build_jump_bag(db: Session, jb: InventoryLocation) -> None:
    """Build the standard jump bag compartments and par levels."""
    jb_left = make_compartment(db, location=jb, name="Left Pocket", sort_order=1,
                               location_descriptor="Left exterior pocket of jump bag")
    add_par(db, item=get_or_create_item(db, name="Empty Sharps Container JB",
                                        category=ItemCategory.EQUIPMENT),
            location=jb, compartment=jb_left, min_qty=1)

    jb_back = make_compartment(db, location=jb, name="Back Pocket", sort_order=2,
                               location_descriptor="Rear pocket of jump bag")
    for name, qty in [("OPAs/NPAs JB", 1), ("Water Bottle JB", 1),
                      ("Colorimetric CO2 Detector", 1), ("Combi-Tube JB", 1),
                      ("Thomas Tube Holders JB", 2)]:
        cat = (ItemCategory.EQUIPMENT if any(x in name for x in ["Holder", "OPA", "Bottle"])
               else ItemCategory.CONSUMABLE)
        add_par(db, item=get_or_create_item(db, name=name, category=cat),
                location=jb, compartment=jb_back, min_qty=qty)

    jb_front = make_compartment(db, location=jb, name="Front Pocket", sort_order=3,
                                location_descriptor="Front pocket of jump bag")
    for name, qty in [
        ("C-Collar Adult JB", 1), ("Overdose Rescue Kit NARCAN", 1),
        ("SPo2 Monitor JB", 1), ("Glucometer Lancets JB", 6),
        ("Alcohol Prep JB", 6), ("Bandaids JB", 6), ("Gauze 3x3 JB", 3),
        ("Glucometer Test Strips JB", 6), ("Thermometer JB", 1),
        ("Thermometer Probe Covers", 1), ("BioHazard Bags JB", 1),
    ]:
        cat = (ItemCategory.MEDICATION if "NARCAN" in name else
               ItemCategory.CONSUMABLE if any(x in name for x in
                                              ["Gauze", "Bandaid", "Prep", "Strips"])
               else ItemCategory.EQUIPMENT)
        add_par(db, item=get_or_create_item(db, name=name, category=cat),
                location=jb, compartment=jb_front, min_qty=qty)

    jb_main = make_compartment(db, location=jb, name="Main Pocket", sort_order=10,
                               location_descriptor="Main compartment of jump bag")
    add_par(db, item=get_or_create_item(db, name="Jump Bag O2 Tank w/ Regulator 15LPM",
                                        category=ItemCategory.EQUIPMENT),
            location=jb, compartment=jb_main, min_qty=1)
    add_par(db, item=get_or_create_item(db, name="Jump Bag O2 PSI",
                                        category=ItemCategory.EQUIPMENT,
                                        check_type=ItemCheckType.MEASUREMENT,
                                        unit_of_measure="PSI",
                                        measurement_minimum=500.0, measurement_maximum=2200.0),
            location=jb, compartment=jb_main, min_qty=1)
    for name, qty in [("Kerlix Large JB", 3), ("Kerlix Medium JB", 3),
                      ("Stethoscope JB", 1), ("BP Cuff JB", 1),
                      ("Clipboard w/ Paperwork JB", 1)]:
        cat = ItemCategory.DOCUMENT if "Paperwork" in name else ItemCategory.EQUIPMENT
        ct = ItemCheckType.DOCUMENT if cat == ItemCategory.DOCUMENT else ItemCheckType.SUPPLY
        uom = "N/A" if ct == ItemCheckType.DOCUMENT else "each"
        add_par(db, item=get_or_create_item(db, name=name, category=cat,
                                            check_type=ct, unit_of_measure=uom),
                location=jb, compartment=jb_main, min_qty=qty)

    jb_ep_back = make_compartment(db, location=jb, name="Main Pocket — Elastic Pouches Back",
                                  sort_order=11, parent=jb_main,
                                  location_descriptor="Elastic pouches, rear of main pocket")
    for name, qty in [("Tourniquet JB", 2), ("Kerlix Small JB", 4), ("Emesis Container JB", 2)]:
        cat = (ItemCategory.CONSUMABLE if any(x in name for x in ["Emesis", "Kerlix"])
               else ItemCategory.EQUIPMENT)
        add_par(db, item=get_or_create_item(db, name=name, category=cat),
                location=jb, compartment=jb_ep_back, min_qty=qty)

    jb_ep_front = make_compartment(db, location=jb, name="Main Pocket — Elastic Pouches Front",
                                   sort_order=12, parent=jb_main,
                                   location_descriptor="Elastic pouches, front of main pocket")
    for name, qty in [
        ("Writing Utensils JB", 1), ("Pen Light JB", 2), ("Occlusive Dressing JB", 2),
        ("Bite Stick JB", 1), ("Oral Glucose Gel", 2), ("Oral Glucose Tablets", 1),
        ("BleedStop", 1), ("Thermometer EP", 1), ("Tape Various Sizes JB", 3),
        ("Trauma Shears JB", 2), ("Triangle Bandage JB", 2),
        ("ABD Pads 5x9 JB", 2), ("Gauze Pads 3x3 JB", 6), ("ACE Wrap JB", 2),
    ]:
        cat = ItemCategory.MEDICATION if "Glucose" in name else ItemCategory.CONSUMABLE
        add_par(db, item=get_or_create_item(db, name=name, category=cat),
                location=jb, compartment=jb_ep_front, min_qty=qty)

    jb_flap_left = make_compartment(db, location=jb, name="Main Pocket — Flap Left",
                                    sort_order=13, parent=jb_main,
                                    location_descriptor="Left flap of main pocket")
    for name, qty in [("NRB Adult JB", 3), ("NAS Adult JB", 5), ("Stethoscope Flap JB", 1)]:
        add_par(db, item=get_or_create_item(db, name=name, category=ItemCategory.EQUIPMENT),
                location=jb, compartment=jb_flap_left, min_qty=qty)

    jb_flap_right = make_compartment(db, location=jb, name="Main Pocket — Flap Right",
                                     sort_order=14, parent=jb_main,
                                     location_descriptor="Right flap of main pocket")
    add_par(db, item=get_or_create_item(db, name="BVM Adult JB",
                                        category=ItemCategory.EQUIPMENT),
            location=jb, compartment=jb_flap_right, min_qty=1)


# ---------------------------------------------------------------------------
# Main seed
# ---------------------------------------------------------------------------

def seed(db: Session) -> None:

    # =========================================================================
    # STATION 1 — Newberg Township
    # Ambulance 712 (BLS) + Jump Bag shared with 710
    # =========================================================================
    print("Seeding Newberg Township Station 1...")

    newberg = db.query(Station).filter(Station.name == "Newberg Township Station 1").first()
    if not newberg:
        newberg = Station(name="Newberg Township Station 1",
                          address="Newberg Township, Michigan",
                          region="Cass County", active=True)
        db.add(newberg)
        db.flush()
        print(f"  Created station: {newberg.name}")

    # Supply room
    if not db.query(InventoryLocation).filter(
        InventoryLocation.station_id == newberg.station_id,
        InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
    ).first():
        db.add(InventoryLocation(location_type=LocationType.STATION_SUPPLY_ROOM,
                                 station_id=newberg.station_id,
                                 label="Newberg Station 1 Supply Room"))
        db.flush()

    # Vehicle 712 — BLS
    v712 = db.query(Vehicle).filter(Vehicle.vehicle_number == "712").first()
    if not v712:
        v712 = Vehicle(station_id=newberg.station_id, vehicle_number="712",
                       vehicle_type=VehicleType.BLS, active=True)
        db.add(v712)
        db.flush()
        loc712 = InventoryLocation(location_type=LocationType.VEHICLE,
                                   station_id=newberg.station_id,
                                   vehicle_id=v712.vehicle_id,
                                   label="Unit 712 — BLS Ambulance")
        db.add(loc712)
        db.flush()
        print(f"  Created vehicle 712 (BLS)")
    else:
        # Correct type if previously seeded as ALS
        if v712.vehicle_type != VehicleType.BLS:
            print(f"  Correcting Vehicle 712: {v712.vehicle_type} → BLS")
            v712.vehicle_type = VehicleType.BLS
            db.flush()
        loc712 = db.query(InventoryLocation).filter(
            InventoryLocation.vehicle_id == v712.vehicle_id).first()

    # Jump Bag (shared 710/712)
    jb_loc = db.query(InventoryLocation).filter(
        InventoryLocation.station_id == newberg.station_id,
        InventoryLocation.location_type == LocationType.JUMP_BAG,
    ).first()
    if not jb_loc:
        jb_loc = InventoryLocation(location_type=LocationType.JUMP_BAG,
                                   station_id=newberg.station_id,
                                   label="Jump Bag (Units 710/712)")
        db.add(jb_loc)
        db.flush()
        print("  Created jump bag location")

    print("  Building 712 inventory...")
    build_ambulance_inventory(db, loc712, is_als=False)
    build_jump_bag(db, jb_loc)

    newberg_comp_count = db.query(Compartment).filter(
        Compartment.location_id.in_([loc712.location_id, jb_loc.location_id])
    ).count()
    newberg_par_count = db.query(ParLevel).filter(
        ParLevel.location_id.in_([loc712.location_id, jb_loc.location_id])
    ).count()

    # =========================================================================
    # STATION 2 — Marcellus Township
    # Ambulance 540 (ALS)
    # Same inventory structure as 712 but with ALS drug cabinet.
    # Items are shared from the global catalog — only new compartments and
    # par levels are created for 540's own location.
    # =========================================================================
    print("\nSeeding Marcellus Township Station 1...")

    marcellus = db.query(Station).filter(Station.name == "Marcellus Township Station 1").first()
    if not marcellus:
        marcellus = Station(name="Marcellus Township Station 1",
                            address="Marcellus Township, Michigan",
                            region="Cass County", active=True)
        db.add(marcellus)
        db.flush()
        print(f"  Created station: {marcellus.name}")

    # Supply room
    if not db.query(InventoryLocation).filter(
        InventoryLocation.station_id == marcellus.station_id,
        InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
    ).first():
        db.add(InventoryLocation(location_type=LocationType.STATION_SUPPLY_ROOM,
                                 station_id=marcellus.station_id,
                                 label="Marcellus Station 1 Supply Room"))
        db.flush()

    # Vehicle 540 — ALS
    v540 = db.query(Vehicle).filter(Vehicle.vehicle_number == "540").first()
    if not v540:
        v540 = Vehicle(station_id=marcellus.station_id, vehicle_number="540",
                       vehicle_type=VehicleType.ALS, active=True)
        db.add(v540)
        db.flush()
        loc540 = InventoryLocation(location_type=LocationType.VEHICLE,
                                   station_id=marcellus.station_id,
                                   vehicle_id=v540.vehicle_id,
                                   label="Unit 540 — ALS Ambulance")
        db.add(loc540)
        db.flush()
        print(f"  Created vehicle 540 (ALS)")
    else:
        loc540 = db.query(InventoryLocation).filter(
            InventoryLocation.vehicle_id == v540.vehicle_id).first()

    print("  Building 540 inventory...")
    build_ambulance_inventory(db, loc540, is_als=True)

    marcellus_comp_count = db.query(Compartment).filter(
        Compartment.location_id == loc540.location_id
    ).count()
    marcellus_par_count = db.query(ParLevel).filter(
        ParLevel.location_id == loc540.location_id
    ).count()

    # =========================================================================
    # Commit and report
    # =========================================================================
    db.commit()

    total_items = db.query(Item).count()

    print(f"""
  ✓ Seed complete.

  Global item catalog:    {total_items} items

  Newberg Township Station 1 (Unit 712 — BLS):
    Compartments:         {newberg_comp_count}
    Par levels:           {newberg_par_count}
    Location ID (712):    {loc712.location_id}
    Location ID (JB):     {jb_loc.location_id}
    Station ID:           {newberg.station_id}

  Marcellus Township Station 1 (Unit 540 — ALS):
    Compartments:         {marcellus_comp_count}
    Par levels:           {marcellus_par_count}
    Location ID (540):    {loc540.location_id}
    Station ID:           {marcellus.station_id}
""")


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
    print("Done.")
