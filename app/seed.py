"""
seed.py
Seed data for EMS ReadyKit development database.

Stations seeded:
    1. Newberg Township Station — Ambulance 712 (BLS) + Unit 712 Jump Bag
       Full par levels from real inventory forms (ITM-2/ITM-4).
    2. Marcellus Township Station — Unit 612 (BLS ambulance) + Unit 632 (QRV fire
       engine) + Unit 621 (QRV fire engine)
       Full par levels from real inventory forms (ONBOARD-1).
    3. Newberg Training Station (orange) — Training Unit A + B, Jump Bag A + B
       Item catalog seeded; par levels assigned via admin UI.
    4. ⚠ TEST STATION — Dev Only — Unit TEST (QRV)
       Item catalog seeded; par levels assigned via admin UI.

Items are station-scoped (items.station_id FK, migration 0028). Each station gets its
own copy of BASE_ITEM_SEED items — one canonical item per real-world thing, reused
across compartments via separate ParLevel rows (e.g. "Gauze, 3x3" → ambulance PC18 +
jump bag Front Pocket + supply room shelf, all pointing at the same item_id).

Newberg gets full par levels from the real 712/jump bag inventory forms. Other stations
start with the catalog populated but par levels empty — a supervisor creates compartments
and assigns items via Station Administration once available (ITM-6).

Usage:
    cd app
    python seed.py

Prerequisites:
    alembic upgrade head must have been run first.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

# ── Production guard ───────────────────────────────────────────────────────────
if os.environ.get("APP_ENV", "").lower() == "production":
    print("Seed skipped in production.")
    sys.exit(0)

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

from sqlalchemy.orm import Session  # noqa: E402

sys.path.insert(0, ".")

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
from ems_readykit.models.stock_lot import StockLot  # noqa: E402

# Short aliases to keep BASE_ITEM_SEED readable
_E = ItemCategory.EQUIPMENT
_C = ItemCategory.CONSUMABLE
_M = ItemCategory.MEDICATION
_D = ItemCategory.DOCUMENT
_SUP = ItemCheckType.SUPPLY
_MEAS = ItemCheckType.MEASUREMENT
_FUNC = ItemCheckType.FUNCTIONAL
_DATE = ItemCheckType.DATE_RECORD
_DOC = ItemCheckType.DOCUMENT
_EXP = ItemCheckType.EXPIRY_DATE

# ---------------------------------------------------------------------------
# BASE_ITEM_SEED
# One entry per canonical real-world item.  Keys match get_or_create_item()
# kwargs.  station_supply defaults to True; set False for equipment checks,
# medications, and controlled-substance items that are not stocked in the
# supply room.
# ---------------------------------------------------------------------------

BASE_ITEM_SEED = [
    # ── Airway & Respiratory ─────────────────────────────────────────────────
    {
        "name": "Adult BVM",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "S/M CPAP",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "L CPAP",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Combi-Tube 37F & 41F",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Thomas Tube Holders",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "set",
    },
    {
        "name": "Adult NAS",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Adult NRB",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "OPAs/NPAs",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Adult Nebulizers",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "O2 O-Rings",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "SpO2 Monitor",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Colorimetric CO2 Detector",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Infant NRB",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Infant NAS",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Infant BVM",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pediatric NRB",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pediatric NAS",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pediatric BVM",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pediatric Nebulizer",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Portable Suction Unit",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Soft Suction Tips 6F",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Soft Suction Tips 10F",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Soft Suction Tips 16F",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "6ft Suction Hose",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Rigid Yankauer",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Extra Suction Canister",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Jump Bag O2 Tank w/ Regulator 15LPM",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # O2 PSI readings — station_supply=False (equipment checks, not stockroom items)
    # On-Board: large tank, 500-2200 PSI.  Stretcher/Jump Bag: small tanks, 200-500 PSI.
    {
        "name": "On-Board O2 PSI",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "measurement_minimum": 500.0,
        "measurement_maximum": 2200.0,
        "station_supply": False,
    },
    {
        "name": "Stretcher O2 PSI",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "measurement_minimum": 200.0,
        "measurement_maximum": 500.0,
        "station_supply": False,
    },
    {
        "name": "Jump Bag O2 PSI",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "measurement_minimum": 200.0,
        "measurement_maximum": 500.0,
        "station_supply": False,
    },
    # ── Wound Care & Trauma Supplies ─────────────────────────────────────────
    {
        "name": "Gauze, 3x3",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "CAT Tourniquet",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "ABD Pad 5x9",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "ABD Pad 8x10",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Tape Various Sizes",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Triangle Bandage",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "ACE Wrap Various Sizes",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Occlusive Dressing",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Bite Stick",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Traction Splint = PS EC2 item (distinct from Adult/Peds Traction Splints in DS EC1)
    {
        "name": "Traction Splint",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # C-Collar, Adult merges C-Collars PC7 + C-Collar Adult JB + C-Collars Adult PS
    {
        "name": "C-Collar, Adult",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "C-Collar Bag",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Mega-Movers merges Mega-Movers PC14 + Mega-Movers DS3
    {
        "name": "Mega-Movers",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Emesis Container merges Emesis Containers (ambulance) + Emesis Container JB
    {
        "name": "Emesis Container",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Gauze Bandage Various Sizes",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Gauze Sponges 4x4",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Kerlix (Various Sizes)",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Kerlix, Large",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Kerlix, Medium",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Kerlix, Small",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Burn Sheets",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Trauma Dressings",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Hot Packs",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Cold Packs",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "TPOD Pelvic Splint",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Sam Splints",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Long-board Splints",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "K.E.D. Board",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Adult Traction Splint",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Peds Traction Splint",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Sterile Saline Solution",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Long Board",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Short Board",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Board Straps",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "set",
    },
    {
        "name": "Head Blocks",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "set",
    },
    {
        "name": "BleedStop",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Stair Chair",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # ── PPE & Cleaning ────────────────────────────────────────────────────────
    # Gloves merge Glove Boxes S/M/L/XL + Gloves S/M/L/XL + Cab Gloves S/M/L
    {
        "name": "Gloves, Small",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Gloves, Medium",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Gloves, Large",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Gloves, X-Large",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Antimicrobial Hand Wipes merges Admin Counter + PC5 items
    {
        "name": "Antimicrobial Hand Wipes",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Infection Control Kit merges PC5 + PC14 items
    {
        "name": "Infection Control Kit",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # BioHazard Bags merges Bio-Hazard Bags (ambulance) + BioHazard Bags JB
    {
        "name": "BioHazard Bags",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Gowns",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Goggles",
        "category": _E,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "N-95 Masks",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Fluid Control Solidifier",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Paper Towels",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "E.S.P. Kit",
        "category": _E,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "DECON/HAZMAT Suits XL",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Evidence Bags",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "HEPA Masks",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Hand Sanitizer",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # ── Diagnostic & Monitoring Equipment ────────────────────────────────────
    # Stethoscope merges Stethoscope + Stethoscope PC18 + Stethoscope JB + Stethoscope Flap JB
    {
        "name": "Stethoscope",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Thermometer merges Thermometer PC18 Unit + Thermometer JB + Thermometer EP
    {
        "name": "Thermometer",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Thermometer Probe Covers",
        "category": _C,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Glucometer Lancets merges Glucometer Lancets + Restock Lancets + Glucometer Lancets JB
    {
        "name": "Glucometer Lancets",
        "category": _C,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Glucometer Test Strips",
        "category": _C,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Alcohol Prep Pads merges Alcohol Prep PC18 + Restock Alcohol Prep + Alcohol Preps BLS + Alcohol Prep JB
    {
        "name": "Alcohol Prep Pads",
        "category": _C,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Bandaids merges Bandaids PC18 + Restock Bandaids + Bandaids JB
    {
        "name": "Bandaids",
        "category": _C,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Oral Glucose Tablets merges Oral Glucose + Oral Glucose Tablets (JB)
    {
        "name": "Oral Glucose Tablets",
        "category": _M,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Oral Glucose Gel",
        "category": _M,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Trauma Shears merges Trauma Shears + Trauma Shears PC18 + Trauma Shears JB
    {
        "name": "Trauma Shears",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Ring Cutter",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Replacement Stethoscope Parts",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Wrist BP Monitor",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Multi-Cuff BP Cuff System",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "BP Cuff",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Extra O2 Tank (no regulator)",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pen Light",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pocket Mask",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pediatric First-In Bag",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "MI-Medic Cards",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # AED / LUCAS — equipment checks, station_supply=False (not stocked in supply room)
    {
        "name": "AED Battery",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "AED Date of Last Charge",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _DATE,
        "unit_of_measure": "N/A",
        "recurrence_days": 90,
        "station_supply": False,
    },
    {
        "name": "AED Pads Adult",
        "category": _C,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _EXP,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "AED Pads Pediatric",
        "category": _C,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _EXP,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    # LUCAS Device merges LUCAS Device + LUCAS Device Ready Check into one FUNCTIONAL priority item
    {
        "name": "LUCAS Device",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "LUCAS Date of Last Charge",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _DATE,
        "unit_of_measure": "N/A",
        "recurrence_days": 30,
        "station_supply": False,
    },
    {
        "name": "Stretcher Battery Charged",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Stretcher Battery Date of Last Charge",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _DATE,
        "unit_of_measure": "N/A",
        "recurrence_days": 90,
        "station_supply": False,
    },
    # ── Medications & Controlled Substances ──────────────────────────────────
    # All station_supply=False — managed via drug cabinet, not supply room
    # Syringes merges Extra Syringes + Syringes BLS
    {
        "name": "Syringes",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Needles BLS",
        "category": _C,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    # Overdose Rescue Kit (NARCAN) and Intranasal Naloxone are confirmed separate items
    {
        "name": "Overdose Rescue Kit (NARCAN)",
        "category": _E,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Intranasal Naloxone",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Albuterol Inhalation",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Low Dose Aspirin",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Epinephrine IM",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Nitroglycerin SL",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "BLS Drug Bag (stocked)",
        "category": _E,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "BLS Drug Use Sheets",
        "category": _D,
        "category_group": "Medications & Controlled Substances",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "ALS Drug Bag (stocked)",
        "category": _E,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "ALS Drug Use Sheets",
        "category": _D,
        "category_group": "Medications & Controlled Substances",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "PT Personal Item Lock-Up",
        "category": _E,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Morphine",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "controlled_substance": True,
        "station_supply": False,
    },
    {
        "name": "Fentanyl",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "controlled_substance": True,
        "station_supply": False,
    },
    {
        "name": "Midazolam",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "controlled_substance": True,
        "station_supply": False,
    },
    {
        "name": "Diazepam",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "controlled_substance": True,
        "station_supply": False,
    },
    {
        "name": "Adenosine",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Amiodarone",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Atropine",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Dopamine",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Sodium Bicarbonate",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Dextrose 50%",
        "category": _M,
        "category_group": "Medications & Controlled Substances",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    # ── Documents, Linens & Patient Comfort ──────────────────────────────────
    # Clipboard w/ Paperwork merges Clipboard (ambulance Admin Counter) + Clipboard w/ Paperwork JB
    {
        "name": "Clipboard w/ Paperwork",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    # Blankets merges Blankets (PC10) + Extra Blankets (Bench)
    {
        "name": "Blankets",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Towels merges Towels PC11 + Towels PC14
    {
        "name": "Towels",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Empty Sharps Container merges Empty Sharps Container Bench + Empty Sharps Container JB
    {
        "name": "Empty Sharps Container",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Writing Utensils merges Writing Utensils (Admin Counter) + Writing Utensils JB
    {
        "name": "Writing Utensils",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Water Bottle merges Water Bottles (DS EC2) + Water Bottle JB
    {
        "name": "Water Bottle",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # Fire Extinguisher merges PS EC2 physical item + Truck Ops FUNCTIONAL check
    # check_type=SUPPLY confirmed by Admin; still appears in Truck Ops as a presence check
    {
        "name": "Fire Extinguisher",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Sheets",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pillow Cases",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Blanket Roll",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Absorbent Pads",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Emergency Blankets",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Survival Wrap Foil Blanket",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Triage Tags",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "OB Kit",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "OB Hat",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "OB Warmers",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Bedpan",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "ACR Child Harness",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Extra Pillows",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "iPad & Charger",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "O2 Wrench",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Duct Tape",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Styro-foam Cups",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Glo-Sticks",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "PCR or HERN PCR",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Billing Form",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "AMA Form",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "AMA C-Spine Precautions Form",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Transfer Form",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Claim Submission Form",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Ambulance Transport Cert",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Updated Radio Channel List",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Cass County Protocol Book",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    # ── Vehicle Operations ────────────────────────────────────────────────────
    # FUNCTIONAL and DOCUMENT vehicle-system checks.  station_supply=False — these
    # are operational checks, not supply room items.
    {
        "name": "Runs and Starts",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "External Warning Systems (Lights & Sirens)",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Loading & Unloading Access",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Ambulance Cot and Straps Secured",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Patient Compartment Climate Control",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Communication Medcom Compliant",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Flares or Equivalent Device",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Portable Two-Way Radio",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Window Punch Available",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Mileage Sheet",
        "category": _D,
        "category_group": "Vehicle Operations",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Insurance Information",
        "category": _D,
        "category_group": "Vehicle Operations",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Hood Hoses",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Hood Belts",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Hood Oil Level",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Hood Steering/Brakes",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Hood Radiator",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Hood Windshield",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Hood Battery",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Broom",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Jumper Cables",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Scene Light",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Peds Jump Bag",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Patient Restraints",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Cot Battery Charger",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Cot Spare Battery",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    # =========================================================================
    # ── Marcellus Onboarding (ONBOARD-1) ─────────────────────────────────────
    # Fire-truck items (Units 632/621) live in this SHARED catalog — not a
    # Marcellus-only list — so Newberg's/Training's fire trucks pick them up
    # automatically once those are onboarded (unused, no par levels, until
    # then). category_group="Vehicle Operations" for all of them, matching
    # the existing convention for FUNCTIONAL vehicle-system checks; every
    # item in that group is station_supply=False. Unit 612 ambulance-specific
    # new items follow the same "add to BASE_ITEM_SEED even if only one
    # station currently uses it" convention already established for
    # "Stretcher Battery Date of Last Charge" above.
    # =========================================================================

    # ── Fire Truck: Tire Pressure & Tread — Unit 632, 8 positions ────────────
    # Confirmed (Jennifer): a PSI gauge, same pattern as On-Board O2 PSI.
    # OPEN ITEM (ONBOARD-1): no confirmed min/max PSI threshold yet — left
    # null; a supervisor sets real thresholds later via the admin UI.
    {
        "name": "Tire Pressure — LF",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "station_supply": False,
    },
    {
        "name": "Tire Pressure — RF",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "station_supply": False,
    },
    {
        "name": "Tire Pressure — FLR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "station_supply": False,
    },
    {
        "name": "Tire Pressure — FRR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "station_supply": False,
    },
    {
        "name": "Tire Pressure — IFLR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "station_supply": False,
    },
    {
        "name": "Tire Pressure — IFRR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "station_supply": False,
    },
    {
        "name": "Tire Pressure — OBLR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "station_supply": False,
    },
    {
        "name": "Tire Pressure — IBLR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "station_supply": False,
    },
    {
        "name": "Tire Tread Depth — LF",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "32nds in",
        "measurement_minimum": 4.0,
        "station_supply": False,
    },
    {
        "name": "Tire Tread Depth — RF",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "32nds in",
        "measurement_minimum": 4.0,
        "station_supply": False,
    },
    {
        "name": "Tire Tread Depth — FLR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "32nds in",
        "measurement_minimum": 4.0,
        "station_supply": False,
    },
    {
        "name": "Tire Tread Depth — FRR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "32nds in",
        "measurement_minimum": 4.0,
        "station_supply": False,
    },
    {
        "name": "Tire Tread Depth — IFLR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "32nds in",
        "measurement_minimum": 4.0,
        "station_supply": False,
    },
    {
        "name": "Tire Tread Depth — IFRR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "32nds in",
        "measurement_minimum": 4.0,
        "station_supply": False,
    },
    {
        "name": "Tire Tread Depth — OBLR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "32nds in",
        "measurement_minimum": 4.0,
        "station_supply": False,
    },
    {
        "name": "Tire Tread Depth — IBLR",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "32nds in",
        "measurement_minimum": 4.0,
        "station_supply": False,
    },
    # ── Fire Truck: Portable Pump — Unit 632 ──────────────────────────────────
    {
        "name": "Portable Pump Gas",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Portable Pump Plugs",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Portable Pump 5-Minute Run",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    # ── Fire Truck: SCBA / Voice Amplifier — Unit 621 ─────────────────────────
    {
        "name": "SCBA",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "SCBA Mask, Large",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "SCBA Mask, Medium",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "SCBA Mask, Small",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Old Voice Amplifier",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "SCBA Battery",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "SCBA Battery Date Changed",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _DATE,
        "unit_of_measure": "N/A",
        "recurrence_days": 90,
        "station_supply": False,
    },
    {
        "name": "Old Voice Amplifier Battery",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Old Voice Amplifier Battery Date Changed",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _DATE,
        "unit_of_measure": "N/A",
        "recurrence_days": 90,
        "station_supply": False,
    },
    # ── Fire Truck: Generators — Unit 621 ─────────────────────────────────────
    {
        "name": "Generator Gas",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Generator Oil",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Generator Plugs",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Generator 5-Minute Run",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    # ── Fire Truck: Gas Meter — Unit 621 ──────────────────────────────────────
    # Confirmed (Jennifer): this is a compressed-gas bottle gauge, same as
    # On-Board O2 PSI — unit_of_measure="PSI". OPEN ITEM (ONBOARD-1): the safe
    # min/max range is still unconfirmed; left null until Jennifer provides it.
    {
        "name": "Gas Meter Reading",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _MEAS,
        "unit_of_measure": "PSI",
        "station_supply": False,
    },
    # ── Fire Truck: Run Sheets — Units 632 + 621 ──────────────────────────────
    {
        "name": "Run Sheets",
        "category": _C,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    # ── Fire Truck: Interior gauges/controls — Units 632 + 621 (shared subset) ─
    {
        "name": "Interior Lights",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Radio",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Fuel Gauge",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Temperature Gauge",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Voltage Gauge",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Oil Pressure",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Air Pressure",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "RPM Gauge",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Transmission Temp Gauge",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Air Horn",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Electric Horn",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Siren",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Heater",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Flash Light",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Accountability Tags",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Defroster",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Air Compressor",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Transmission Oil",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "MABAS Board",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    # ── Fire Truck: Exterior lighting/camera — Units 632 + 621 (shared subset) ─
    {
        "name": "Head Lights",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Tail Lights",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Turn Signals",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Backup Lights/Alarm",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Overheads",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Scene Lights — Driver Side",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Scene Lights — Passenger Side",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Scene Lights — Back",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Camera System — Monitor in Cab",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Camera System — Passenger Side",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Camera System — Back",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Cross Lay #1",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Cross Lay #2",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    # ── Fire Truck: Under Hood additions — Units 632 + 621 (identical) ────────
    {
        "name": "Anti-Freeze",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Transmission Fluid",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Power Steering",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Battery Cables",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Windshield Wiper Fluid",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    # ── Fire Truck: Exterior supply exceptions — Unit 621 ─────────────────────
    # Counted/present items, not pass/fail checks — SUPPLY instead of
    # FUNCTIONAL. No confirmed quantity, so min_qty=1 default at par-level.
    {
        "name": "Shovels",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Brooms",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Chemflex",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Road Flares",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    # ── Unit 612 Ambulance — Airway & Respiratory additions ───────────────────
    {
        "name": "Oxygen Tubing",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Peds EtCO2",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _EXP,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Ridge Tip",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Soft Cath Tip",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Spoon",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Bulb Syringes",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "La Combi-Tube",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _EXP,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Sa Combi-Tube",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _EXP,
        "unit_of_measure": "N/A",
    },
    {
        "name": "I-Gel, Size 3",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "I-Gel, Size 4",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "I-Gel, Size 5",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Lube Tube",
        "category": _C,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pet Oxygen Masks",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Manual Suction",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Spare Oxygen Bottles",
        "category": _E,
        "category_group": "Airway & Respiratory",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # ── Unit 612 Ambulance — Wound Care & Trauma Supplies additions ──────────
    {
        "name": "Padded Board Splints",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Peds Board Splints",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pelvic Sling, Standard",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pelvic Sling, Large",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pro-Splints",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Vac Splints",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Sager Splint (primary unit only)",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Life Jackets",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Body Bags",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Lift Tarp",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Peds Cot Harness",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Sponges",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Gauze Sponges 2x2",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Pressure Dressings",
        "category": _C,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Peds Board",
        "category": _E,
        "category_group": "Wound Care & Trauma Supplies",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # ── Unit 612 Ambulance — PPE & Cleaning additions ─────────────────────────
    {
        "name": "Bug Spray",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Red Bags, Small",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Red Bags, Medium",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Red Bags, Large",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Level B Suit",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Biocide Spray",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _EXP,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Surgical Masks",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Caviwipes",
        "category": _C,
        "category_group": "PPE & Cleaning",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # ── Unit 612 Ambulance — Diagnostic & Monitoring Equipment additions ─────
    {
        "name": "Glucometer Kit",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Monitor is Charged",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Lucas 3 Spare Battery",
        "category": _E,
        "category_group": "Diagnostic & Monitoring Equipment",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    # ── Unit 612 Ambulance — Medications & Controlled Substances additions ───
    # station_supply=False — matches the rest of this group (managed via drug
    # cabinet, not supply room).
    {
        "name": "White Drug Bag",
        "category": _E,
        "category_group": "Medications & Controlled Substances",
        "check_type": _EXP,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    # ── Unit 612 Ambulance — Documents, Linens & Patient Comfort additions ───
    {
        "name": "Pg 1 Medical",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Pg 2 Medical",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Pg 1 Trauma",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Pg 2 Trauma",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Private Policy/Signature Forms",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Run Box",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Towel Rolls",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Rescue Blanket",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Sharps Box (spare)",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Spare Run Forms",
        "category": _C,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "DNRs on File",
        "category": _D,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
    },
    {
        "name": "Pillow",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    {
        "name": "Urinal",
        "category": _E,
        "category_group": "Documents, Linens & Patient Comfort",
        "check_type": _SUP,
        "unit_of_measure": "each",
    },
    # ── Unit 612 Ambulance — Vehicle Operations additions ─────────────────────
    # station_supply=False — matches the rest of this group (operational
    # checks, not supply room items).
    {
        "name": "Unit Starts",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    # Fuel Level: no percentage/gauge field exists in the schema, and no
    # threshold was ever specified for one — modeled as a pass/fail presence
    # check (adequate for the shift vs. not), matching the rest of this
    # compartment's daily FUNCTIONAL checks (Unit Starts, Radio Check, etc.).
    {
        "name": "Fuel Level",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Headlights — Low Beam",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Headlights — High Beam",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Turn Signals — Left",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Turn Signals — Right",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Scene Lights Working (doors open & reverse)",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Emergency Lights (front & rear)",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Siren (Phases)",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "HAZMAT Book",
        "category": _D,
        "category_group": "Vehicle Operations",
        "check_type": _DOC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Binoculars",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Seatbelt Tool",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Radio Check",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Map Books",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Mileage Pads & Ink Pens",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Clock Working",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Jump Bag Present",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Steering Wheel Cover",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Flares",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "Spare Batteries",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
    {
        "name": "800 Radio",
        "category": _E,
        "category_group": "Vehicle Operations",
        "check_type": _FUNC,
        "unit_of_measure": "N/A",
        "station_supply": False,
    },
    {
        "name": "Salt & Sand (winter only)",
        "category": _C,
        "category_group": "Vehicle Operations",
        "check_type": _SUP,
        "unit_of_measure": "each",
        "station_supply": False,
    },
]

# Lookup of every canonical BASE_ITEM_SEED entry by name, used by _seeded_item()
# below so builder functions that reuse a canonical item across many
# compartments (Marcellus's fire trucks + Unit 612, ONBOARD-1) don't have to
# hand-repeat its exact category/check_type/unit_of_measure/station_supply at
# every call site — get_or_create_item() overwrites those fields on every call,
# so a call site that forgets one would silently drift the item away from its
# BASE_ITEM_SEED definition (e.g. station_supply flipping back to the True
# default).
_BASE_ITEM_SEED_BY_NAME: dict[str, dict] = {entry["name"]: entry for entry in BASE_ITEM_SEED}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_or_create_item(
    db: Session,
    *,
    name: str,
    station_id: int,
    category: ItemCategory,
    category_group: Optional[str] = None,
    check_type: ItemCheckType = ItemCheckType.SUPPLY,
    controlled_substance: bool = False,
    unit_of_measure: str = "each",
    measurement_minimum: Optional[float] = None,
    measurement_maximum: Optional[float] = None,
    recurrence_days: Optional[int] = None,
    station_supply: bool = True,
) -> Item:
    item = (
        db.query(Item).filter(Item.station_id == station_id, Item.name == name).first()
    )
    if item:
        item.check_type = check_type
        item.recurrence_days = recurrence_days
        item.unit_of_measure = unit_of_measure
        item.station_supply = station_supply
        if category_group is not None:
            item.category_group = category_group
        if measurement_minimum is not None:
            item.measurement_minimum = measurement_minimum
        if measurement_maximum is not None:
            item.measurement_maximum = measurement_maximum
        return item
    item = Item(
        name=name,
        station_id=station_id,
        category=category,
        category_group=category_group,
        check_type=check_type,
        controlled_substance=controlled_substance,
        unit_of_measure=unit_of_measure,
        measurement_minimum=measurement_minimum,
        measurement_maximum=measurement_maximum,
        recurrence_days=recurrence_days,
        station_supply=station_supply,
        active=True,
    )
    db.add(item)
    db.flush()
    return item


def _seeded_item(db: Session, *, station_id: int, name: str) -> Item:
    """Fetch/create a station's copy of a canonical BASE_ITEM_SEED item, re-applying
    its exact BASE_ITEM_SEED kwargs every time. Used by the Marcellus fire-truck and
    Unit 612 builders (ONBOARD-1) instead of hand-repeating kwargs at each call site.
    """
    entry = _BASE_ITEM_SEED_BY_NAME[name]
    kwargs = {k: v for k, v in entry.items() if k != "name"}
    return get_or_create_item(db, name=name, station_id=station_id, **kwargs)


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
    restriction_note: Optional[str] = None,
    parent: Optional[Compartment] = None,
    als_only: bool = False,
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
        comp.restriction_note = restriction_note
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
# Catalog seeder — creates BASE_ITEM_SEED items for any station
# ---------------------------------------------------------------------------


def seed_station_catalog(db: Session, station_id: int) -> int:
    """Create BASE_ITEM_SEED items for a station. Returns count of new items created."""
    created = 0
    for entry in BASE_ITEM_SEED:
        exists = (
            db.query(Item.item_id)
            .filter(Item.station_id == station_id, Item.name == entry["name"])
            .first()
        )
        if not exists:
            get_or_create_item(db, station_id=station_id, **entry)
            created += 1
        else:
            # Update mutable fields on re-seed
            get_or_create_item(db, station_id=station_id, **entry)
    db.flush()
    return created


# ---------------------------------------------------------------------------
# Supply room builder — compartments + test stock lots
# ---------------------------------------------------------------------------


def build_supply_room(db: Session, loc: InventoryLocation, station_id: int) -> None:
    """Create 4 default shelf compartments and seed test stock lots. Idempotent."""
    from datetime import date as _date

    default_compartments = [
        ("Cab 1 - Shelf 1", "Cabinet 1, top shelf — airway & PPE supplies", 1),
        ("Cab 1 - Shelf 2", "Cabinet 1, bottom shelf — dressings & bandages", 2),
        ("Cab 2 - Shelf 1", "Cabinet 2, top shelf — medications & controlled items", 3),
        ("Cab 2 - Shelf 2", "Cabinet 2, bottom shelf — equipment & restock items", 4),
    ]
    for name, descriptor, sort_order in default_compartments:
        make_compartment(
            db,
            location=loc,
            name=name,
            location_descriptor=descriptor,
            sort_order=sort_order,
        )

    test_stock = [
        ("Gauze Bandage Various Sizes", "LOT-G2026-001", _date(2027, 6, 30), 24),
        ("Sterile Saline Solution", "LOT-S2026-001", _date(2027, 3, 15), 12),
        ("Gloves, Medium", None, None, 50),
        ("ABD Pad 8x10", "LOT-A2026-001", _date(2027, 9, 15), 18),
        ("N-95 Masks", "LOT-N2026-001", _date(2027, 12, 31), 40),
        ("Kerlix (Various Sizes)", "LOT-K2026-001", _date(2027, 8, 31), 16),
        ("Gloves, Large", None, None, 30),
        ("Tape Various Sizes", "LOT-T2026-001", _date(2027, 6, 30), 20),
        ("Triangle Bandage", "LOT-TB2026-001", _date(2027, 9, 30), 10),
        ("CAT Tourniquet", "LOT-C2026-001", _date(2028, 1, 31), 6),
    ]
    for item_name, lot_number, expiry, qty in test_stock:
        item = (
            db.query(Item)
            .filter(Item.name == item_name, Item.station_id == station_id)
            .first()
        )
        if not item:
            continue
        existing = (
            db.query(StockLot)
            .filter(
                StockLot.location_id == loc.location_id,
                StockLot.item_id == item.item_id,
            )
            .first()
        )
        if not existing:
            db.add(
                StockLot(
                    item_id=item.item_id,
                    location_id=loc.location_id,
                    quantity=qty,
                    lot_number=lot_number,
                    expiration_date=expiry,
                )
            )
    db.flush()


# ---------------------------------------------------------------------------
# Ambulance inventory builder (Newberg — full par levels from real forms)
# ---------------------------------------------------------------------------


def build_ambulance_inventory(
    db: Session, loc: InventoryLocation, station_id: int, is_als: bool
) -> None:
    """Create all compartments and par levels for a standard ambulance location."""

    def item(name: str, **kw) -> Item:
        return get_or_create_item(db, name=name, station_id=station_id, **kw)

    # ── PC 1 (Airway) ─────────────────────────────────────────────────────────
    pc1 = make_compartment(
        db,
        location=loc,
        name="PC 1 (Airway)",
        sort_order=1,
        location_descriptor="Interior, left side, forward",
    )
    for name, qty in [("Adult BVM", 1), ("S/M CPAP", 1), ("L CPAP", 1)]:
        add_par(
            db, item=item(name, category=_E), location=loc, compartment=pc1, min_qty=qty
        )

    # ── PC 2 (Airway) ─────────────────────────────────────────────────────────
    pc2 = make_compartment(
        db,
        location=loc,
        name="PC 2 (Airway)",
        sort_order=2,
        location_descriptor="Interior, left side",
    )
    for name, uom in [
        ("Combi-Tube 37F & 41F", "each"),
        ("Syringes", "each"),  # was: Extra Syringes
        ("Thomas Tube Holders", "set"),
    ]:
        add_par(
            db,
            item=item(name, category=_E, unit_of_measure=uom),
            location=loc,
            compartment=pc2,
            min_qty=1,
        )

    # ── PC 3 (Airway) ─────────────────────────────────────────────────────────
    pc3 = make_compartment(
        db,
        location=loc,
        name="PC 3 (Airway)",
        sort_order=3,
        location_descriptor="Interior, left side",
    )
    for name in ["Adult NAS", "Adult NRB", "Stethoscope"]:
        add_par(
            db, item=item(name, category=_E), location=loc, compartment=pc3, min_qty=1
        )

    # ── PC 4 (Airway) ─────────────────────────────────────────────────────────
    pc4 = make_compartment(
        db,
        location=loc,
        name="PC 4 (Airway)",
        sort_order=4,
        location_descriptor="Interior, left side",
    )
    for name, cat in [
        ("OPAs/NPAs", _C),
        ("Adult Nebulizers", _E),
        ("O2 O-Rings", _E),
    ]:
        add_par(
            db, item=item(name, category=cat), location=loc, compartment=pc4, min_qty=1
        )

    # ── Admin Counter ──────────────────────────────────────────────────────────
    admin_counter = make_compartment(
        db,
        location=loc,
        name="Admin Counter",
        sort_order=5,
        location_descriptor="Interior, admin counter near driver",
    )
    for name, cat, ct, qty in [
        ("iPad & Charger", _E, _SUP, 1),
        ("Clipboard w/ Paperwork", _D, _DOC, 1),  # was: Clipboard
        ("Hand Sanitizer", _C, _SUP, 1),
        ("Antimicrobial Hand Wipes", _C, _SUP, 1),
        ("Writing Utensils", _E, _SUP, 1),
        ("Trauma Shears", _E, _SUP, 1),
        ("Duct Tape", _C, _SUP, 1),
        ("O2 Wrench", _E, _SUP, 1),
        ("PCR or HERN PCR", _D, _DOC, 1),
        ("Billing Form", _D, _DOC, 1),
        ("AMA Form", _D, _DOC, 1),
        ("AMA C-Spine Precautions Form", _D, _DOC, 1),
        ("Transfer Form", _D, _DOC, 1),
        ("Claim Submission Form", _D, _DOC, 1),
        ("Ambulance Transport Cert", _D, _DOC, 1),
        ("Updated Radio Channel List", _D, _DOC, 1),
    ]:
        uom = "N/A" if ct == _DOC else "each"
        add_par(
            db,
            item=item(name, category=cat, check_type=ct, unit_of_measure=uom),
            location=loc,
            compartment=admin_counter,
            min_qty=qty,
        )

    # ── Suction Drawer ─────────────────────────────────────────────────────────
    suction = make_compartment(
        db,
        location=loc,
        name="Suction Drawer",
        sort_order=6,
        location_descriptor="Interior, suction drawer",
    )
    for name, qty in [
        ("Soft Suction Tips 6F", 3),
        ("Soft Suction Tips 10F", 3),
        ("Soft Suction Tips 16F", 3),
        ("6ft Suction Hose", 1),
        ("Rigid Yankauer", 3),
    ]:
        add_par(
            db,
            item=item(name, category=_C),
            location=loc,
            compartment=suction,
            min_qty=qty,
        )

    # ── Admin Cabinet ──────────────────────────────────────────────────────────
    admin_cab = make_compartment(
        db,
        location=loc,
        name="Admin Cabinet",
        sort_order=7,
        location_descriptor="Interior, behind airway seat",
    )
    for name, cat, ct in [
        ("Evidence Bags", _C, _SUP),
        ("HEPA Masks", _C, _SUP),
        ("Cass County Protocol Book", _D, _DOC),
        ("ACR Child Harness", _E, _SUP),
    ]:
        uom = "N/A" if ct == _DOC else "each"
        add_par(
            db,
            item=item(name, category=cat, check_type=ct, unit_of_measure=uom),
            location=loc,
            compartment=admin_cab,
            min_qty=1,
        )

    # ── PC 5 (PPE) ────────────────────────────────────────────────────────────
    pc5 = make_compartment(
        db,
        location=loc,
        name="PC 5 (PPE)",
        sort_order=8,
        location_descriptor="Interior, PPE compartment",
    )
    for name in [
        "Gloves, Small",
        "Gloves, Medium",
        "Gloves, Large",
        "Gloves, X-Large",
        "Gowns",
        "Goggles",
        "N-95 Masks",
        "Fluid Control Solidifier",
        "Paper Towels",
        "Antimicrobial Hand Wipes",  # was: Antimicrobial Hand Wipes PC5
        "E.S.P. Kit",
        "Infection Control Kit",  # was: Infection Control Kits PC5
    ]:
        cat = _E if name in ("Goggles", "E.S.P. Kit") else _C
        add_par(
            db, item=item(name, category=cat), location=loc, compartment=pc5, min_qty=1
        )

    # ── PC 6 ──────────────────────────────────────────────────────────────────
    pc6 = make_compartment(
        db, location=loc, name="PC 6", sort_order=9, location_descriptor="Interior"
    )
    for name, cat in [
        ("Wrist BP Monitor", _E),
        ("Pocket Mask", _E),
        ("OB Kit", _E),
        ("OB Hat", _C),
        ("OB Warmers", _E),
    ]:
        add_par(
            db, item=item(name, category=cat), location=loc, compartment=pc6, min_qty=1
        )

    # ── PC 7 ──────────────────────────────────────────────────────────────────
    pc7 = make_compartment(
        db,
        location=loc,
        name="PC 7",
        sort_order=10,
        location_descriptor="Interior, patient compartment",
    )
    for name, qty in [
        ("Emesis Container", 20),  # was: Emesis Containers
        ("Bedpan", 1),
        ("C-Collar, Adult", 1),  # was: C-Collars PC7
        ("Extra Suction Canister", 1),
        ("C-Collar Bag", 1),
    ]:
        cat = _C if name == "Emesis Container" else _E
        add_par(
            db,
            item=item(name, category=cat),
            location=loc,
            compartment=pc7,
            min_qty=qty,
        )

    # ── PC 8 — AED + LUCAS priority items ─────────────────────────────────────
    pc8 = make_compartment(
        db,
        location=loc,
        name="PC 8",
        sort_order=11,
        location_descriptor="Interior, driver side",
    )
    add_par(
        db,
        item=item("Portable Suction Unit", category=_E),
        location=loc,
        compartment=pc8,
        min_qty=1,
    )
    add_par(
        db,
        item=item(
            "AED Battery",
            category=_E,
            check_type=_FUNC,
            unit_of_measure="N/A",
            station_supply=False,
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
        priority_check=True,
        priority_question="AED shows READY?",
    )
    add_par(
        db,
        item=item(
            "AED Date of Last Charge",
            category=_E,
            check_type=_DATE,
            unit_of_measure="N/A",
            recurrence_days=90,
            station_supply=False,
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
    )
    add_par(
        db,
        item=item(
            "AED Pads Adult",
            category=_C,
            check_type=_EXP,
            unit_of_measure="N/A",
            station_supply=False,
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
    )
    add_par(
        db,
        item=item(
            "AED Pads Pediatric",
            category=_C,
            check_type=_EXP,
            unit_of_measure="N/A",
            station_supply=False,
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
    )
    # LUCAS Device: one canonical FUNCTIONAL priority item (merges former "LUCAS Device Ready Check")
    add_par(
        db,
        item=item(
            "LUCAS Device",
            category=_E,
            check_type=_FUNC,
            unit_of_measure="N/A",
            station_supply=False,
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
        priority_check=True,
        priority_question="LUCAS shows READY?",
    )
    add_par(
        db,
        item=item(
            "LUCAS Date of Last Charge",
            category=_E,
            check_type=_DATE,
            unit_of_measure="N/A",
            recurrence_days=30,
            station_supply=False,
        ),
        location=loc,
        compartment=pc8,
        min_qty=1,
    )

    # ── PC 9 — Drug Cabinet (BLS or ALS) ──────────────────────────────────────
    if is_als:
        pc9 = make_compartment(
            db,
            location=loc,
            name="PC 9 ALS Drug Cabinet",
            sort_order=12,
            location_descriptor="Interior, ALS drug cabinet",
            restriction_note="Dual signature required — ALS personnel only",
            als_only=True,
        )
        for name, cat, controlled in [
            ("ALS Drug Bag (stocked)", _E, False),
            ("ALS Drug Use Sheets", _D, False),
            ("PT Personal Item Lock-Up", _E, False),
            ("Morphine", _M, True),
            ("Fentanyl", _M, True),
            ("Midazolam", _M, True),
            ("Diazepam", _M, True),
        ]:
            ct = _DOC if "Sheets" in name else _SUP
            uom = "N/A" if ct == _DOC else "each"
            add_par(
                db,
                item=item(
                    name,
                    category=cat,
                    check_type=ct,
                    unit_of_measure=uom,
                    controlled_substance=controlled,
                    station_supply=False,
                ),
                location=loc,
                compartment=pc9,
                min_qty=1,
            )

        als_drug = make_compartment(
            db,
            location=loc,
            name="ALS Drug Bag",
            sort_order=13,
            location_descriptor="Interior, PC 9 ALS drug cabinet",
            als_only=True,
        )
        for name in [
            "Intranasal Naloxone",
            "Albuterol Inhalation",
            "Low Dose Aspirin",
            "Epinephrine IM",
            "Adenosine",
            "Amiodarone",
            "Atropine",
            "Dopamine",
            "Sodium Bicarbonate",
            "Dextrose 50%",
            "Nitroglycerin SL",
            "Syringes",
            "Needles BLS",
            "Alcohol Prep Pads",
        ]:
            add_par(
                db,
                item=item(name, category=_M, station_supply=False),
                location=loc,
                compartment=als_drug,
                min_qty=1,
            )
    else:
        pc9 = make_compartment(
            db,
            location=loc,
            name="PC 9 BLS Drug Cabinet",
            sort_order=12,
            location_descriptor="Interior, BLS drug cabinet",
        )
        for name, cat, ct in [
            ("BLS Drug Bag (stocked)", _E, _SUP),
            ("BLS Drug Use Sheets", _D, _DOC),
            ("PT Personal Item Lock-Up", _E, _SUP),
        ]:
            uom = "N/A" if ct == _DOC else "each"
            add_par(
                db,
                item=item(
                    name,
                    category=cat,
                    check_type=ct,
                    unit_of_measure=uom,
                    station_supply=False,
                ),
                location=loc,
                compartment=pc9,
                min_qty=1,
            )

        bls_drug = make_compartment(
            db,
            location=loc,
            name="BLS Drug Bag",
            sort_order=13,
            location_descriptor="Interior, PC 9 BLS drug cabinet",
        )
        for name in [
            "Intranasal Naloxone",
            "Albuterol Inhalation",
            "Low Dose Aspirin",
            "Epinephrine IM",
            "Syringes",
            "Needles BLS",
            "Alcohol Prep Pads",
            "Nitroglycerin SL",
        ]:
            add_par(
                db,
                item=item(name, category=_M, station_supply=False),
                location=loc,
                compartment=bls_drug,
                min_qty=1,
            )

    # ── PC 10 (Linens) ─────────────────────────────────────────────────────────
    pc10 = make_compartment(
        db,
        location=loc,
        name="PC 10 (Linens)",
        sort_order=14,
        location_descriptor="Interior, linen storage",
    )
    for name in ["Sheets", "Blankets"]:
        add_par(
            db, item=item(name, category=_E), location=loc, compartment=pc10, min_qty=1
        )

    # ── PC 11 (Linens) ─────────────────────────────────────────────────────────
    pc11 = make_compartment(
        db,
        location=loc,
        name="PC 11 (Linens)",
        sort_order=15,
        location_descriptor="Interior, linen storage",
    )
    for name in ["Pillow Cases", "Towels"]:  # Towels merges Towels PC11 + Towels PC14
        add_par(
            db, item=item(name, category=_E), location=loc, compartment=pc11, min_qty=1
        )

    # ── Bench ──────────────────────────────────────────────────────────────────
    bench = make_compartment(
        db,
        location=loc,
        name="Bench",
        sort_order=16,
        location_descriptor="Interior, squad bench",
    )
    for name, qty in [
        ("Multi-Cuff BP Cuff System", 1),
        ("SpO2 Monitor", 1),
        ("Extra Pillows", 1),
        ("Extra O2 Tank (no regulator)", 1),
        ("Empty Sharps Container", 1),  # was: Empty Sharps Container Bench
        ("Blanket Roll", 1),
        ("Blankets", 2),  # was: Extra Blankets (same item)
    ]:
        add_par(
            db,
            item=item(name, category=_E),
            location=loc,
            compartment=bench,
            min_qty=qty,
        )

    # ── Glove Compartment ──────────────────────────────────────────────────────
    glove_comp = make_compartment(
        db,
        location=loc,
        name="Glove Compartment",
        sort_order=17,
        location_descriptor="Interior, glove storage",
    )
    for size in ["Small", "Medium", "Large", "X-Large"]:
        add_par(
            db,
            item=item(f"Gloves, {size}", category=_C),
            location=loc,
            compartment=glove_comp,
            min_qty=1,
        )

    # ── PC 12 (Trauma) ─────────────────────────────────────────────────────────
    pc12 = make_compartment(
        db,
        location=loc,
        name="PC 12 (Trauma)",
        sort_order=18,
        location_descriptor="Interior, trauma supplies",
    )
    for name, qty in [
        ("Burn Sheets", 1),
        ("Trauma Dressings", 1),
        ("Hot Packs", 1),
        ("Cold Packs", 1),
        ("TPOD Pelvic Splint", 1),
        ("Sam Splints", 4),
    ]:
        cat = _C if any(x in name for x in ["Pack", "Sheet", "Dress"]) else _E
        add_par(
            db,
            item=item(name, category=cat),
            location=loc,
            compartment=pc12,
            min_qty=qty,
        )

    # ── PC 13 (Trauma) ─────────────────────────────────────────────────────────
    pc13 = make_compartment(
        db,
        location=loc,
        name="PC 13 (Trauma)",
        sort_order=19,
        location_descriptor="Interior, trauma supplies",
    )
    for name, qty in [
        ("ABD Pad 8x10", 6),
        ("ABD Pad 5x9", 8),
        ("Gauze Bandage Various Sizes", 10),
        ("Kerlix (Various Sizes)", 8),  # was: KERLIX PC13
        ("Tape Various Sizes", 10),
        ("CAT Tourniquet", 2),
        ("Gauze Sponges 4x4", 25),
        ("Triangle Bandage", 2),  # was: Triangle Bandages
        ("ACE Wrap Various Sizes", 6),  # was: ACE Wraps Various Sizes
        ("Occlusive Dressing", 3),
        ("Sterile Saline Solution", 4),
    ]:
        add_par(
            db,
            item=item(name, category=_C),
            location=loc,
            compartment=pc13,
            min_qty=qty,
        )

    # ── PC 14 ──────────────────────────────────────────────────────────────────
    pc14 = make_compartment(
        db,
        location=loc,
        name="PC 14",
        sort_order=20,
        location_descriptor="Interior, rear",
    )
    for name, qty in [
        ("Mega-Movers", 1),  # was: Mega-Movers PC14
        ("Towels", 1),  # was: Towels PC14
        ("Absorbent Pads", 1),
        ("Emergency Blankets", 3),
        ("DECON/HAZMAT Suits XL", 3),
        ("Infection Control Kit", 4),  # was: Infection Control Kits PC14
        ("Triage Tags", 1),
        ("Survival Wrap Foil Blanket", 1),
    ]:
        cat = (
            _C
            if any(x in name for x in ["Blanket", "Wrap", "Pad"])
            else (
                _C
                if name
                in (
                    "DECON/HAZMAT Suits XL",
                    "Triage Tags",
                    "Infection Control Kit",
                    "Towels",
                )
                else _E
            )
        )
        add_par(
            db,
            item=item(name, category=cat),
            location=loc,
            compartment=pc14,
            min_qty=qty,
        )

    # ── PC 15 (Infant Airway) ──────────────────────────────────────────────────
    pc15 = make_compartment(
        db,
        location=loc,
        name="PC 15 (Infant Airway)",
        sort_order=21,
        location_descriptor="Interior",
    )
    for name in ["Infant NRB", "Infant NAS", "Infant BVM"]:
        add_par(
            db, item=item(name, category=_E), location=loc, compartment=pc15, min_qty=1
        )

    # ── PC 16 (Pediatric Airway) ───────────────────────────────────────────────
    pc16 = make_compartment(
        db,
        location=loc,
        name="PC 16 (Pediatric Airway)",
        sort_order=22,
        location_descriptor="Interior",
    )
    for name in [
        "Pediatric NRB",
        "Pediatric NAS",
        "Pediatric BVM",
        "Pediatric Nebulizer",
    ]:
        add_par(
            db, item=item(name, category=_E), location=loc, compartment=pc16, min_qty=1
        )

    # ── Charger Counter ────────────────────────────────────────────────────────
    charger = make_compartment(
        db,
        location=loc,
        name="Charger Counter",
        sort_order=23,
        location_descriptor="Interior, charger counter",
    )
    for name in [
        "Pediatric First-In Bag",
        "Cot Battery Charger",
        "Cot Spare Battery",
        "MI-Medic Cards",
    ]:
        add_par(
            db,
            item=item(name, category=_E),
            location=loc,
            compartment=charger,
            min_qty=1,
        )

    # ── PC 17 ──────────────────────────────────────────────────────────────────
    pc17 = make_compartment(
        db, location=loc, name="PC 17", sort_order=24, location_descriptor="Interior"
    )
    add_par(
        db,
        item=item("Patient Restraints", category=_E),
        location=loc,
        compartment=pc17,
        min_qty=1,
    )

    # ── PC 18 (Tools) ──────────────────────────────────────────────────────────
    # Stethoscope, Thermometer, Trauma Shears use canonical names shared with other compartments.
    # Alcohol Prep Pads, Bandaids, Glucometer Lancets replace the PC18-specific + Restock items.
    pc18 = make_compartment(
        db,
        location=loc,
        name="PC 18 (Tools)",
        sort_order=25,
        location_descriptor="Interior",
    )
    for name in [
        "Stethoscope",
        "Ring Cutter",
        "Trauma Shears",
        "Replacement Stethoscope Parts",
    ]:
        add_par(
            db, item=item(name, category=_E), location=loc, compartment=pc18, min_qty=1
        )
    for name, qty in [
        ("Glucometer Lancets", 6),  # merges Glucometer Lancets + Restock Lancets
        ("Alcohol Prep Pads", 6),  # merges Alcohol Prep PC18 + Restock Alcohol Prep
        ("Bandaids", 6),  # merges Bandaids PC18 + Restock Bandaids
        ("Gauze, 3x3", 3),  # was: Gauze 3x3 PC18
        ("Glucometer Test Strips", 6),
        ("Bite Stick", 2),
        ("Oral Glucose Tablets", 2),  # was: Oral Glucose
        ("Thermometer", 1),  # was: Thermometer PC18 Unit
    ]:
        cat = _C if name not in ("Thermometer",) else _E
        add_par(
            db,
            item=item(name, category=cat),
            location=loc,
            compartment=pc18,
            min_qty=qty,
        )

    # ── Stretcher ──────────────────────────────────────────────────────────────
    stretcher = make_compartment(
        db,
        location=loc,
        name="Stretcher",
        sort_order=26,
        location_descriptor="Patient stretcher / cot",
    )
    # Stretcher O2 PSI: small tank — corrected thresholds 200-500 PSI (was 500-2200)
    add_par(
        db,
        item=item(
            "Stretcher O2 PSI",
            category=_E,
            check_type=_MEAS,
            unit_of_measure="PSI",
            measurement_minimum=200.0,
            measurement_maximum=500.0,
            station_supply=False,
        ),
        location=loc,
        compartment=stretcher,
        min_qty=1,
        priority_check=True,
        priority_question="Stretcher O2 above 200 PSI?",
    )
    add_par(
        db,
        item=item(
            "Stretcher Battery Charged",
            category=_E,
            check_type=_FUNC,
            unit_of_measure="N/A",
            station_supply=False,
        ),
        location=loc,
        compartment=stretcher,
        min_qty=1,
    )
    add_par(
        db,
        item=item(
            "Stretcher Battery Date of Last Charge",
            category=_E,
            check_type=_DATE,
            unit_of_measure="N/A",
            recurrence_days=90,
            station_supply=False,
        ),
        location=loc,
        compartment=stretcher,
        min_qty=1,
    )

    # ── Driver Side EC 1 ───────────────────────────────────────────────────────
    ds_ec1 = make_compartment(
        db,
        location=loc,
        name="Driver Side EC 1",
        sort_order=30,
        location_descriptor="Exterior, driver side, forward bay",
    )
    for name in [
        "Long-board Splints",
        "K.E.D. Board",
        "Adult Traction Splint",
        "Peds Traction Splint",
        "Broom",
    ]:
        add_par(
            db,
            item=item(name, category=_E),
            location=loc,
            compartment=ds_ec1,
            min_qty=1,
        )
    # On-Board O2: large tank — thresholds 500-2200 PSI (unchanged)
    add_par(
        db,
        item=item(
            "On-Board O2 PSI",
            category=_E,
            check_type=_MEAS,
            unit_of_measure="PSI",
            measurement_minimum=500.0,
            measurement_maximum=2200.0,
            station_supply=False,
        ),
        location=loc,
        compartment=ds_ec1,
        min_qty=1,
    )

    # ── Driverside EC 2 ────────────────────────────────────────────────────────
    ds_ec2 = make_compartment(
        db,
        location=loc,
        name="Driverside EC 2",
        sort_order=31,
        location_descriptor="Exterior, driver side, middle bay",
    )
    for name, qty in [
        ("Scene Light", 1),
        ("Water Bottle", 10),  # was: Water Bottles
        ("BioHazard Bags", 1),  # was: Bio-Hazard Bags
        ("Styro-foam Cups", 1),
        ("Glo-Sticks", 1),
        ("Peds Jump Bag", 1),
    ]:
        cat = _E if name in ("Scene Light", "Peds Jump Bag") else _C
        add_par(
            db,
            item=item(name, category=cat),
            location=loc,
            compartment=ds_ec2,
            min_qty=qty,
        )

    # ── Driver Side EC 3 ───────────────────────────────────────────────────────
    ds_ec3 = make_compartment(
        db,
        location=loc,
        name="Driver Side EC 3",
        sort_order=32,
        location_descriptor="Exterior, driver side, rear bay",
    )
    for name in ["Mega-Movers", "Stair Chair"]:  # Mega-Movers was: Mega-Movers DS3
        add_par(
            db,
            item=item(name, category=_E),
            location=loc,
            compartment=ds_ec3,
            min_qty=1,
        )

    # ── Passenger Side EC 2 ────────────────────────────────────────────────────
    ps_ec2 = make_compartment(
        db,
        location=loc,
        name="Passenger Side EC 2",
        sort_order=34,
        location_descriptor="Exterior, passenger side, middle bay",
    )
    for name in ["Fire Extinguisher", "Jumper Cables", "Traction Splint"]:
        # Fire Extinguisher: SUPPLY (not FUNCTIONAL) — confirmed by Admin
        # Traction Splint: distinct from Adult/Peds Traction Splints in DS EC1
        add_par(
            db,
            item=item(name, category=_E),
            location=loc,
            compartment=ps_ec2,
            min_qty=1,
        )

    # ── Passenger Side EC 3 ────────────────────────────────────────────────────
    ps_ec3 = make_compartment(
        db,
        location=loc,
        name="Passenger Side EC 3",
        sort_order=35,
        location_descriptor="Exterior, passenger side, rear bay",
    )
    for name, qty in [
        ("Long Board", 2),
        ("Short Board", 2),
        ("Board Straps", 2),
        ("Head Blocks", 2),
        ("C-Collar, Adult", 2),  # was: C-Collars Adult PS
    ]:
        uom = "set" if name in ("Board Straps", "Head Blocks") else "each"
        add_par(
            db,
            item=item(name, category=_E, unit_of_measure=uom),
            location=loc,
            compartment=ps_ec3,
            min_qty=qty,
        )

    # ── Truck Operations ───────────────────────────────────────────────────────
    # requires_full_check=True blocks No Change for this compartment.
    # Fire Extinguisher UL Listed (old FUNCTIONAL) → Fire Extinguisher (SUPPLY, canonical).
    truck_ops = make_compartment(
        db,
        location=loc,
        name="Truck Operations",
        sort_order=40,
        location_descriptor="Operational vehicle systems check",
        requires_full_check=True,
    )
    for name in [
        "Runs and Starts",
        "External Warning Systems (Lights & Sirens)",
        "Loading & Unloading Access",
        "Ambulance Cot and Straps Secured",
        "Patient Compartment Climate Control",
        "Communication Medcom Compliant",
        "Flares or Equivalent Device",
        "Portable Two-Way Radio",
        "Window Punch Available",
    ]:
        add_par(
            db,
            item=item(
                name,
                category=_E,
                check_type=_FUNC,
                unit_of_measure="N/A",
                station_supply=False,
            ),
            location=loc,
            compartment=truck_ops,
            min_qty=1,
        )
    for name in ["Mileage Sheet", "Insurance Information"]:
        add_par(
            db,
            item=item(
                name,
                category=_D,
                check_type=_DOC,
                unit_of_measure="N/A",
                station_supply=False,
            ),
            location=loc,
            compartment=truck_ops,
            min_qty=1,
        )
    # Fire Extinguisher: SUPPLY presence check (merged from "Fire Extinguisher UL Listed" FUNCTIONAL)
    add_par(
        db,
        item=item(
            "Fire Extinguisher", category=_E, check_type=_SUP, unit_of_measure="each"
        ),
        location=loc,
        compartment=truck_ops,
        min_qty=1,
    )
    # Gloves in cab — Gloves, Small/Medium/Large (canonical, same item as PC5 + Glove Compartment)
    for size in ["Small", "Medium", "Large"]:
        add_par(
            db,
            item=item(f"Gloves, {size}", category=_C),
            location=loc,
            compartment=truck_ops,
            min_qty=1,
        )

    # ── Under Hood ─────────────────────────────────────────────────────────────
    under_hood = make_compartment(
        db,
        location=loc,
        name="Under Hood",
        sort_order=99,
        location_descriptor="Engine compartment",
        restriction_note=None,
        requires_full_check=True,
    )
    for name in [
        "Hoses",
        "Belts",
        "Oil Level",
        "Steering/Brakes",
        "Radiator",
        "Windshield",
        "Battery",
    ]:
        add_par(
            db,
            item=item(
                f"Hood {name}",
                category=_E,
                check_type=_FUNC,
                unit_of_measure="N/A",
                station_supply=False,
            ),
            location=loc,
            compartment=under_hood,
            min_qty=1,
        )


# ---------------------------------------------------------------------------
# Jump bag inventory builder (Newberg — full par levels from real forms)
# ---------------------------------------------------------------------------


def build_jump_bag(db: Session, jb: InventoryLocation, station_id: int) -> None:
    """Build the standard jump bag compartments and par levels."""

    def item(name: str, **kw) -> Item:
        return get_or_create_item(db, name=name, station_id=station_id, **kw)

    # ── Left Pocket ────────────────────────────────────────────────────────────
    jb_left = make_compartment(
        db,
        location=jb,
        name="Left Pocket",
        sort_order=1,
        location_descriptor="Left exterior pocket of jump bag",
    )
    add_par(
        db,
        item=item(
            "Empty Sharps Container", category=_E
        ),  # was: Empty Sharps Container JB
        location=jb,
        compartment=jb_left,
        min_qty=1,
    )

    # ── Back Pocket ────────────────────────────────────────────────────────────
    jb_back = make_compartment(
        db,
        location=jb,
        name="Back Pocket",
        sort_order=2,
        location_descriptor="Rear pocket of jump bag",
    )
    for name, qty in [
        ("OPAs/NPAs", 1),  # was: OPAs/NPAs JB
        ("Water Bottle", 1),  # was: Water Bottle JB
        ("Colorimetric CO2 Detector", 1),
        ("Combi-Tube 37F & 41F", 2),  # was: Combi-Tube JB
        ("Thomas Tube Holders", 2),  # was: Thomas Tube Holders JB
    ]:
        cat = (
            _E
            if name
            in (
                "OPAs/NPAs",
                "Thomas Tube Holders",
                "Colorimetric CO2 Detector",
                "Water Bottle",
            )
            else _C
        )
        add_par(
            db,
            item=item(name, category=cat),
            location=jb,
            compartment=jb_back,
            min_qty=qty,
        )

    # ── Front Pocket ───────────────────────────────────────────────────────────
    jb_front = make_compartment(
        db,
        location=jb,
        name="Front Pocket",
        sort_order=3,
        location_descriptor="Front pocket of jump bag",
    )
    for name, qty in [
        ("C-Collar, Adult", 1),  # was: C-Collar Adult JB
        ("Overdose Rescue Kit (NARCAN)", 1),
        ("SpO2 Monitor", 1),  # was: SPo2 Monitor JB
        ("Glucometer Lancets", 6),  # was: Glucometer Lancets JB
        ("Alcohol Prep Pads", 6),  # was: Alcohol Prep JB
        ("Bandaids", 6),  # was: Bandaids JB
        ("Gauze, 3x3", 3),  # was: Gauze 3x3 JB
        ("Glucometer Test Strips", 6),  # was: Glucometer Test Strips JB
        ("Thermometer", 1),  # was: Thermometer JB
        ("Thermometer Probe Covers", 1),
        ("BioHazard Bags", 1),  # was: BioHazard Bags JB
    ]:
        cat = (
            _E
            if name
            in (
                "C-Collar, Adult",
                "SpO2 Monitor",
                "Thermometer",
                "Thermometer Probe Covers",
                "Overdose Rescue Kit (NARCAN)",
            )
            else _C
        )
        if "NARCAN" in name:
            cat = _E
        add_par(
            db,
            item=item(name, category=cat),
            location=jb,
            compartment=jb_front,
            min_qty=qty,
        )

    # ── Main Pocket ────────────────────────────────────────────────────────────
    jb_main = make_compartment(
        db,
        location=jb,
        name="Main Pocket",
        sort_order=10,
        location_descriptor="Main compartment of jump bag",
    )
    add_par(
        db,
        item=item("Jump Bag O2 Tank w/ Regulator 15LPM", category=_E),
        location=jb,
        compartment=jb_main,
        min_qty=1,
    )
    # Jump Bag O2 PSI: small tank — corrected thresholds 200-500 PSI (was 500-2200)
    add_par(
        db,
        item=item(
            "Jump Bag O2 PSI",
            category=_E,
            check_type=_MEAS,
            unit_of_measure="PSI",
            measurement_minimum=200.0,
            measurement_maximum=500.0,
            station_supply=False,
        ),
        location=jb,
        compartment=jb_main,
        min_qty=1,
        priority_check=True,
        priority_question="Jump Bag O2 above 200 PSI?",
    )
    for name, qty in [
        ("Kerlix, Large", 3),  # was: Kerlix Large JB
        ("Kerlix, Medium", 3),  # was: Kerlix Medium JB
        ("Stethoscope", 1),  # was: Stethoscope JB
        ("BP Cuff", 1),  # was: BP Cuff JB
        ("Clipboard w/ Paperwork", 1),  # was: Clipboard w/ Paperwork JB
    ]:
        cat = _D if name == "Clipboard w/ Paperwork" else _E
        ct = _DOC if cat == _D else _SUP
        uom = "N/A" if ct == _DOC else "each"
        add_par(
            db,
            item=item(name, category=cat, check_type=ct, unit_of_measure=uom),
            location=jb,
            compartment=jb_main,
            min_qty=qty,
        )

    # ── Main Pocket — Elastic Pouches Back ─────────────────────────────────────
    jb_ep_back = make_compartment(
        db,
        location=jb,
        name="Main Pocket — Elastic Pouches Back",
        sort_order=11,
        parent=jb_main,
        location_descriptor="Elastic pouches, rear of main pocket",
    )
    for name, qty in [
        ("CAT Tourniquet", 2),  # was: Tourniquet JB
        ("Kerlix, Small", 4),  # was: Kerlix Small JB
        ("Emesis Container", 2),  # was: Emesis Container JB
    ]:
        cat = _C if name in ("Kerlix, Small", "Emesis Container") else _E
        add_par(
            db,
            item=item(name, category=cat),
            location=jb,
            compartment=jb_ep_back,
            min_qty=qty,
        )

    # ── Main Pocket — Elastic Pouches Front ────────────────────────────────────
    jb_ep_front = make_compartment(
        db,
        location=jb,
        name="Main Pocket — Elastic Pouches Front",
        sort_order=12,
        parent=jb_main,
        location_descriptor="Elastic pouches, front of main pocket",
    )
    for name, qty in [
        ("Writing Utensils", 1),  # was: Writing Utensils JB
        ("Pen Light", 2),  # was: Pen Light JB
        ("Occlusive Dressing", 2),  # was: Occlusive Dressing JB
        ("Bite Stick", 1),  # was: Bite Stick JB
        ("Oral Glucose Gel", 2),
        ("Oral Glucose Tablets", 1),
        ("BleedStop", 1),
        ("Thermometer", 1),  # was: Thermometer EP
        ("Tape Various Sizes", 3),  # was: Tape Various Sizes JB
        ("Trauma Shears", 2),  # was: Trauma Shears JB
        ("Triangle Bandage", 2),  # was: Triangle Bandage JB
        ("ABD Pad 5x9", 2),  # was: ABD Pads 5x9 JB
        ("Gauze, 3x3", 6),  # was: Gauze Pads 3x3 JB
        ("ACE Wrap Various Sizes", 2),  # was: ACE Wrap JB
    ]:
        cat = (
            _M
            if "Glucose" in name
            else (_E if name in ("Trauma Shears", "Pen Light") else _C)
        )
        add_par(
            db,
            item=item(name, category=cat),
            location=jb,
            compartment=jb_ep_front,
            min_qty=qty,
        )

    # ── Main Pocket — Flap Left ────────────────────────────────────────────────
    jb_flap_left = make_compartment(
        db,
        location=jb,
        name="Main Pocket — Flap Left",
        sort_order=13,
        parent=jb_main,
        location_descriptor="Left flap of main pocket",
    )
    for name, qty in [
        ("Adult NRB", 3),  # was: NRB Adult JB
        ("Adult NAS", 5),  # was: NAS Adult JB
        ("Stethoscope", 1),  # was: Stethoscope Flap JB
    ]:
        add_par(
            db,
            item=item(name, category=_E),
            location=jb,
            compartment=jb_flap_left,
            min_qty=qty,
        )

    # ── Main Pocket — Flap Right ───────────────────────────────────────────────
    jb_flap_right = make_compartment(
        db,
        location=jb,
        name="Main Pocket — Flap Right",
        sort_order=14,
        parent=jb_main,
        location_descriptor="Right flap of main pocket",
    )
    add_par(
        db,
        item=item("Adult BVM", category=_E),  # was: BVM Adult JB
        location=jb,
        compartment=jb_flap_right,
        min_qty=1,
    )


# ---------------------------------------------------------------------------
# Marcellus Township builders (ONBOARD-1)
#
# Unit 612's compartment layout and Units 632/621's fire-truck layouts are all
# structurally unrelated to Newberg's 712 PC1-PC18 ambulance layout, so each
# gets its own builder here rather than reusing build_ambulance_inventory().
# All three use _seeded_item() (not the local item()-closure pattern the
# builders above use) since so many of their items are reused across many
# compartments — see _seeded_item's docstring for why.
# ---------------------------------------------------------------------------

# 8 tire positions on Unit 632 (dual rear axle): Left Front, Right Front,
# Front Left Rear, Front Right Rear, Inner Front Left Rear, Inner Front Right
# Rear, Outer Back Left Rear, Inner Back Left Rear.
FIRE_TRUCK_TIRE_POSITIONS = ["LF", "RF", "FLR", "FRR", "IFLR", "IFRR", "OBLR", "IBLR"]

# Under Hood is identical on both 632 and 621 — shared list + helper rather
# than repeating the same 10 items in both builders.
FIRE_TRUCK_UNDER_HOOD_ITEMS = [
    "Hood Oil Level",
    "Hood Radiator",
    "Anti-Freeze",
    "Hood Belts",
    "Hood Hoses",
    "Transmission Fluid",
    "Power Steering",
    "Battery Cables",
    "Hood Battery",
    "Windshield Wiper Fluid",
]


def _build_fire_truck_under_hood(
    db: Session,
    *,
    loc: InventoryLocation,
    station_id: int,
    compartment: Compartment,
) -> None:
    for name in FIRE_TRUCK_UNDER_HOOD_ITEMS:
        add_par(
            db,
            item=_seeded_item(db, station_id=station_id, name=name),
            location=loc,
            compartment=compartment,
            min_qty=1,
        )


def build_fire_truck_632_inventory(
    db: Session, loc: InventoryLocation, station_id: int
) -> None:
    """Unit 632 — Fire Engine Truck. Compartments: Under Hood, Interior, Exterior,
    Tire Pressure & Depth, Portable Pump."""

    def par(name: str, compartment: Compartment, qty: int = 1) -> None:
        add_par(
            db,
            item=_seeded_item(db, station_id=station_id, name=name),
            location=loc,
            compartment=compartment,
            min_qty=qty,
        )

    under_hood = make_compartment(db, location=loc, name="Under Hood", sort_order=1)
    _build_fire_truck_under_hood(
        db, loc=loc, station_id=station_id, compartment=under_hood
    )

    interior = make_compartment(db, location=loc, name="Interior", sort_order=2)
    for name in [
        "Interior Lights",
        "Radio",
        "Fuel Gauge",
        "Temperature Gauge",
        "Voltage Gauge",
        "Oil Pressure",
        "Air Pressure",
        "RPM Gauge",
        "Transmission Temp Gauge",
        "Air Horn",
        "Electric Horn",
        "Siren",
        "Heater",
        "Flash Light",
        "Accountability Tags",
    ]:
        par(name, interior)
    par("Run Sheets", interior, qty=10)

    exterior = make_compartment(db, location=loc, name="Exterior", sort_order=3)
    for name in [
        "Head Lights",
        "Tail Lights",
        "Turn Signals",
        "Backup Lights/Alarm",
        "Overheads",
        "Scene Lights — Driver Side",
        "Scene Lights — Passenger Side",
        "Scene Lights — Back",
        "Camera System — Monitor in Cab",
        "Camera System — Passenger Side",
        "Camera System — Back",
    ]:
        par(name, exterior)

    tire = make_compartment(
        db, location=loc, name="Tire Pressure & Depth", sort_order=4
    )
    for pos in FIRE_TRUCK_TIRE_POSITIONS:
        par(f"Tire Pressure — {pos}", tire)
        par(f"Tire Tread Depth — {pos}", tire)

    pump = make_compartment(db, location=loc, name="Portable Pump", sort_order=5)
    for name in [
        "Portable Pump Gas",
        "Portable Pump Plugs",
        "Portable Pump 5-Minute Run",
    ]:
        par(name, pump)


def build_fire_truck_621_inventory(
    db: Session, loc: InventoryLocation, station_id: int
) -> None:
    """Unit 621 — Fire Engine Truck. Compartments: Under Hood, Interior, Exterior,
    SCBA's, SCBA Masks, Old Voice Amplifiers, Generators."""

    def par(name: str, compartment: Compartment, qty: int = 1) -> None:
        add_par(
            db,
            item=_seeded_item(db, station_id=station_id, name=name),
            location=loc,
            compartment=compartment,
            min_qty=qty,
        )

    under_hood = make_compartment(db, location=loc, name="Under Hood", sort_order=1)
    _build_fire_truck_under_hood(
        db, loc=loc, station_id=station_id, compartment=under_hood
    )

    interior = make_compartment(db, location=loc, name="Interior", sort_order=2)
    for name in [
        "Interior Lights",
        "Radio",
        "Fuel Gauge",
        "Temperature Gauge",
        "Voltage Gauge",
        "RPM Gauge",
        "Oil Pressure",
        "Air Pressure",
        "Transmission Temp Gauge",
        "Siren",
        "Air Horn",
        "Electric Horn",
        "Heater",
        "Defroster",
        "Flash Light",
        "Air Compressor",
        "Transmission Oil",
        "MABAS Board",
        "Accountability Tags",
    ]:
        par(name, interior)
    par("Run Sheets", interior, qty=10)

    exterior = make_compartment(db, location=loc, name="Exterior", sort_order=3)
    for name in [
        "Head Lights",
        "Turn Signals",  # "Turn Lights" on the 621 sheet — same canonical item
        "Tail Lights",
        "Backup Lights/Alarm",
        "Overheads",
    ]:
        par(name, exterior)
    for name in ["Shovels", "Brooms", "Chemflex", "Road Flares"]:
        par(name, exterior)
    for name in ["Cross Lay #1", "Cross Lay #2"]:
        par(name, exterior)

    scbas = make_compartment(db, location=loc, name="SCBA's", sort_order=4)
    par("SCBA", scbas, qty=4)
    par("SCBA Battery", scbas, qty=4)
    par("SCBA Battery Date Changed", scbas, qty=1)

    scba_masks = make_compartment(db, location=loc, name="SCBA Masks", sort_order=5)
    for name in ["SCBA Mask, Large", "SCBA Mask, Medium", "SCBA Mask, Small"]:
        par(name, scba_masks)

    voice_amps = make_compartment(
        db, location=loc, name="Old Voice Amplifiers", sort_order=6
    )
    par("Old Voice Amplifier", voice_amps, qty=4)
    par("Old Voice Amplifier Battery", voice_amps, qty=4)
    par("Old Voice Amplifier Battery Date Changed", voice_amps, qty=1)

    generators = make_compartment(db, location=loc, name="Generators", sort_order=7)
    for name in [
        "Generator Gas",
        "Generator Oil",
        "Generator Plugs",
        "Generator 5-Minute Run",
    ]:
        par(name, generators)
    par("Gas Meter Reading", generators, qty=1)


def build_marcellus_ambulance_inventory(
    db: Session, loc: InventoryLocation, station_id: int
) -> None:
    """Unit 612 — Marcellus Township BLS ambulance. Own compartment layout, built
    from Marcellus's real paper inventory forms — distinct from Newberg's 712
    PC1-PC18 layout, so this does not call build_ambulance_inventory()."""

    def par(
        name: str,
        compartment: Compartment,
        qty: int = 1,
        priority_check: bool = False,
        priority_question: Optional[str] = None,
    ) -> None:
        add_par(
            db,
            item=_seeded_item(db, station_id=station_id, name=name),
            location=loc,
            compartment=compartment,
            min_qty=qty,
            priority_check=priority_check,
            priority_question=priority_question,
        )

    # ── Vehicle Operations / Daily Checks ────────────────────────────────────
    # requires_full_check=True blocks No Change here, mirroring Truck
    # Operations on Unit 712 — responders must physically verify every item.
    daily = make_compartment(
        db,
        location=loc,
        name="Vehicle Operations / Daily Checks",
        sort_order=1,
        requires_full_check=True,
    )
    for name in [
        "Unit Starts",
        "Fuel Level",  # pass/fail presence check — no gauge field in the schema
        "Headlights — Low Beam",
        "Headlights — High Beam",
        "Turn Signals — Left",
        "Turn Signals — Right",
        "Scene Lights Working (doors open & reverse)",
        "Emergency Lights (front & rear)",
        "Siren (Phases)",
        "Patient Compartment Climate Control",  # Climate Control (front & rear)
        "Interior Lights",  # Interior Lights (cab & P.T. comp)
        "Window Punch Available",
        "Cass County Protocol Book",  # Protocols
        "HAZMAT Book",
        "Binoculars",
        "Seatbelt Tool",
        "Radio Check",
        "Map Books",
        "Mileage Pads & Ink Pens",
        "Insurance Information",  # Registration & Insurance (current)
    ]:
        par(name, daily)
    par("On-Board O2 PSI", daily)  # Main On-Board O2 Tank Secured

    # ── Run Box ───────────────────────────────────────────────────────────────
    run_box = make_compartment(db, location=loc, name="Run Box", sort_order=2)
    for name in [
        "Pg 1 Medical",
        "Pg 2 Medical",
        "Pg 1 Trauma",
        "Pg 2 Trauma",
        "Private Policy/Signature Forms",
        "Run Box",  # the box itself — distinct from the "Run Box" item drawer par below
    ]:
        par(name, run_box)

    # ── Drivers Side Front Comp #1 ───────────────────────────────────────────
    ds1 = make_compartment(
        db, location=loc, name="Drivers Side Front Comp #1", sort_order=3
    )
    for name in ["Fire Extinguisher", "Padded Board Splints", "Peds Board Splints"]:
        par(name, ds1)

    # ── Drivers Side Compartment #2 ──────────────────────────────────────────
    ds2 = make_compartment(
        db, location=loc, name="Drivers Side Compartment #2", sort_order=4
    )
    for name in [
        "Head Blocks",  # Headblocks
        "Towel Rolls",
        "TPOD Pelvic Splint",  # T-pod
        "Pelvic Sling, Standard",
        "Pelvic Sling, Large",
        "Rescue Blanket",
        "Water Bottle",  # Drinking Water
        "Bug Spray",
        "Pro-Splints",
        "Duct Tape",  # par #1 of 2 — second row lives in Drivers Side Supply Comp
        "Vac Splints",
        "Red Bags, Small",
        "Red Bags, Medium",
        "Red Bags, Large",
        "Sharps Box (spare)",
    ]:
        par(name, ds2)

    # ── Drivers Side Rear Comp #3 ────────────────────────────────────────────
    ds3 = make_compartment(
        db, location=loc, name="Drivers Side Rear Comp #3", sort_order=5
    )
    par("Flares", ds3)
    par("Peds Traction Splint", ds3)
    par("Adult Traction Splint", ds3)
    par("Sager Splint (primary unit only)", ds3)
    par("K.E.D. Board", ds3, qty=2)  # K.E.D.
    par("Level B Suit", ds3)
    par("Life Jackets", ds3, qty=2)

    # ── Linen Cabinet ─────────────────────────────────────────────────────────
    linen = make_compartment(db, location=loc, name="Linen Cabinet", sort_order=6)
    par("Blankets", linen)  # Heavy Blankets + Light Blankets — one canonical item
    par("Sheets", linen, qty=6)

    # ── Medication Cabinet ────────────────────────────────────────────────────
    med_cab = make_compartment(db, location=loc, name="Medication Cabinet", sort_order=7)
    par("White Drug Bag", med_cab)
    par("Adult Nebulizers", med_cab, qty=6)  # NEB Kits

    # ── Airway Seat Rear Cabinets (top) ──────────────────────────────────────
    airway_top = make_compartment(
        db, location=loc, name="Airway Seat Rear Cabinets (top)", sort_order=8
    )
    par("Biocide Spray", airway_top)
    par("Gowns", airway_top, qty=2)  # Isolation Gowns
    par("Goggles", airway_top, qty=2)  # Safety Glasses
    par("N-95 Masks", airway_top)  # covers Large/Medium/Small form lines — one item
    par("Surgical Masks", airway_top)
    par("Caviwipes", airway_top)

    # ── Airway Seat Rear Cabinets (bottom) ───────────────────────────────────
    airway_bottom = make_compartment(
        db, location=loc, name="Airway Seat Rear Cabinets (bottom)", sort_order=9
    )
    par("Cass County Protocol Book", airway_bottom)  # Protocols — 2nd par row
    par("Spare Run Forms", airway_bottom)
    par("DNRs on File", airway_bottom)

    # ── Airway Seat Drawer ────────────────────────────────────────────────────
    airway_drawer = make_compartment(
        db, location=loc, name="Airway Seat Drawer", sort_order=10
    )
    for name in ["Ridge Tip", "Soft Cath Tip", "Spoon", "Bulb Syringes"]:
        par(name, airway_drawer)
    par("Run Box", airway_drawer)  # 2nd, distinct-compartment par row, same item
    par("Clock Working", airway_drawer)

    # ── Airway Cabinet: Left ──────────────────────────────────────────────────
    airway_left = make_compartment(
        db, location=loc, name="Airway Cabinet: Left", sort_order=11
    )
    par("La Combi-Tube", airway_left)
    par("Sa Combi-Tube", airway_left)
    par("Syringes", airway_left)  # Spare Syringes
    for name in ["I-Gel, Size 3", "I-Gel, Size 4", "I-Gel, Size 5"]:
        par(name, airway_left)
    par("Pocket Mask", airway_left)

    # ── Airway Cabinet: Right ─────────────────────────────────────────────────
    airway_right = make_compartment(
        db, location=loc, name="Airway Cabinet: Right", sort_order=12
    )
    par("OPAs/NPAs", airway_right)  # covers both OPA's and NPA's form lines
    par("Stethoscope", airway_right)  # Spare Stethoscope
    par("Lube Tube", airway_right)
    par("Monitor is Charged", airway_right)

    # ── Pass. Side Front Comp #1 (top) ───────────────────────────────────────
    ps1_top = make_compartment(
        db, location=loc, name="Pass. Side Front Comp #1 (top)", sort_order=13
    )
    par("Jump Bag Present", ps1_top)  # Jump Bag
    par(
        "AED Battery",
        ps1_top,
        priority_check=True,
        priority_question="AED shows READY?",
    )  # AED (turn on and test)
    par("AED Pads Adult", ps1_top)
    par("AED Pads Pediatric", ps1_top)
    par("Portable Suction Unit", ps1_top)  # Portable Suction
    par(
        "LUCAS Device",
        ps1_top,
        priority_check=True,
        priority_question="LUCAS shows READY?",
    )  # Lucas 3
    par("Lucas 3 Spare Battery", ps1_top)
    par("Steering Wheel Cover", ps1_top)

    # ── Pass. Side Comp #1 (bottom) ──────────────────────────────────────────
    ps1_bottom = make_compartment(
        db, location=loc, name="Pass. Side Comp #1 (bottom)", sort_order=14
    )
    par("Body Bags", ps1_bottom)
    par("Lift Tarp", ps1_bottom)
    par("Triage Tags", ps1_bottom)
    par("Pet Oxygen Masks", ps1_bottom)
    par("Manual Suction", ps1_bottom)
    par("Salt & Sand (winter only)", ps1_bottom)

    # ── Pass. Rear Comp #2 ───────────────────────────────────────────────────
    ps_rear = make_compartment(db, location=loc, name="Pass. Rear Comp #2", sort_order=15)
    par("Stair Chair", ps_rear)
    par("Long Board", ps_rear)  # Long Boards
    par("C-Collar Bag", ps_rear)  # C-Collar Bags
    par("Pillow", ps_rear)
    par("Peds Board", ps_rear)

    # ── Oxygen Delivery Cabinet ───────────────────────────────────────────────
    o2_cab = make_compartment(
        db, location=loc, name="Oxygen Delivery Cabinet", sort_order=16
    )
    par("Adult NRB", o2_cab, qty=6)
    par("Adult NAS", o2_cab, qty=6)  # Adult Nasal Cannula
    par("Oxygen Tubing", o2_cab, qty=6)
    par("Adult BVM", o2_cab)  # Adult BVM with Mask
    par("Colorimetric CO2 Detector", o2_cab)  # Adult CO2 Detector (already SUPPLY)
    par("Pediatric NRB", o2_cab, qty=6)  # Peds Non-Rebreather
    par("Pediatric NAS", o2_cab, qty=6)  # Peds Nasal Cannula
    par("Pediatric BVM", o2_cab)  # Peds BVM
    par("S/M CPAP", o2_cab)  # C-PAP, Small/Medium
    par("L CPAP", o2_cab)  # C-PAP, Large
    par("Peds EtCO2", o2_cab)
    par("Infant NAS", o2_cab, qty=6)  # Infant Nasal Cannula
    par("Infant NRB", o2_cab, qty=6)

    # ── Curb Side Seat Comp ───────────────────────────────────────────────────
    curb_seat = make_compartment(db, location=loc, name="Curb Side Seat Comp", sort_order=17)
    par("Blankets", curb_seat)  # Heavy Blankets + Light Blankets — one canonical item
    par("Broom", curb_seat)  # Hand Broom

    # ── Drivers Side Squad Seat ───────────────────────────────────────────────
    squad_seat = make_compartment(
        db, location=loc, name="Drivers Side Squad Seat", sort_order=18
    )
    par("Spare Oxygen Bottles", squad_seat, qty=2)
    par("Peds Cot Harness", squad_seat)

    # ── Passenger Side Lower Drawer ───────────────────────────────────────────
    ps_lower = make_compartment(
        db, location=loc, name="Passenger Side Lower Drawer", sort_order=19
    )
    par("Trauma Shears", ps_lower)  # Scissors, Clamps, Att.
    par("Glucometer Kit", ps_lower)
    par("Glucometer Test Strips", ps_lower)  # Test Strips
    par("Thermometer Probe Covers", ps_lower)  # Probe Covers
    par("Bandaids", ps_lower)  # Band Aids — par #1 of 2
    par("Alcohol Prep Pads", ps_lower)  # Alcohol Pads
    par("Bite Stick", ps_lower)  # Bite Sticks
    par("Glucometer Lancets", ps_lower)  # Lancets
    par("Thermometer", ps_lower)

    # ── Curb Side Bench Drawer ────────────────────────────────────────────────
    bench_drawer = make_compartment(
        db, location=loc, name="Curb Side Bench Drawer", sort_order=20
    )
    par("Patient Restraints", bench_drawer, qty=4)  # Restraints (all)
    par("Spare Batteries", bench_drawer)
    par("800 Radio", bench_drawer)

    # ── Drivers Side Supply Comp ──────────────────────────────────────────────
    ds_supply = make_compartment(
        db, location=loc, name="Drivers Side Supply Comp", sort_order=21
    )
    par("Gauze Sponges 4x4", ds_supply)  # 4x4's
    par("ABD Pad 8x10", ds_supply)  # Abdominal Pads
    par("Gauze, 3x3", ds_supply)  # 3x3's
    par("Trauma Dressings", ds_supply)
    par("ABD Pad 5x9", ds_supply)  # 5x9's
    par("Sponges", ds_supply)
    par("Gauze Sponges 2x2", ds_supply)  # 2x2's
    par("Burn Sheets", ds_supply)  # Burn Sheet
    par("Kerlix (Various Sizes)", ds_supply)  # Kurlex
    par("OB Kit", ds_supply)  # OB Kits
    par("Bandaids", ds_supply)  # Band Aids — par #2 of 2, different compartment
    par("CAT Tourniquet", ds_supply)  # Tourniquet, 2 Types
    par("Occlusive Dressing", ds_supply)
    par("Pressure Dressings", ds_supply)
    par("Triangle Bandage", ds_supply)  # Triangle Bandage (safety pins)
    par("Emergency Blankets", ds_supply)  # Thermal Blanket
    par("Emesis Container", ds_supply)  # Emesis Pans
    par("Urinal", ds_supply)
    par("Cold Packs", ds_supply)
    par("Hot Packs", ds_supply)
    par("Sam Splints", ds_supply)  # SAM Splints
    par("Absorbent Pads", ds_supply)
    par("Duct Tape", ds_supply)  # Duct Tape — par #2 of 2, different compartment


# ---------------------------------------------------------------------------
# Main seed
# ---------------------------------------------------------------------------


def seed(db: Session) -> None:

    # =========================================================================
    # STATION 1 — Newberg Township
    # Ambulance 712 (BLS) + Unit 712 Jump Bag
    # Full par levels from real inventory forms.
    # =========================================================================
    print("Seeding Newberg Township Station...")

    newberg = (
        db.query(Station).filter(Station.name == "Newberg Township Station").first()
    )
    if not newberg:
        newberg = Station(
            name="Newberg Township Station",
            address="Newberg Township, Michigan",
            region="Cass County",
            active=True,
        )
        db.add(newberg)
        db.flush()
        print(f"  Created station: {newberg.name}")

    newberg_supply = (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.station_id == newberg.station_id,
            InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
        )
        .first()
    )
    if not newberg_supply:
        newberg_supply = InventoryLocation(
            location_type=LocationType.STATION_SUPPLY_ROOM,
            station_id=newberg.station_id,
            label="Newberg Station 1 Supply Room",
        )
        db.add(newberg_supply)
        db.flush()
        print("  Created Newberg supply room")

    print("  Seeding Newberg item catalog...")
    catalog_count = seed_station_catalog(db, newberg.station_id)
    print(f"    {catalog_count} new items created")

    build_supply_room(db, newberg_supply, newberg.station_id)

    v712 = db.query(Vehicle).filter(Vehicle.vehicle_number == "712").first()
    if not v712:
        v712 = Vehicle(
            station_id=newberg.station_id,
            vehicle_number="712",
            vehicle_type=VehicleType.BLS,
            active=True,
        )
        db.add(v712)
        db.flush()
        loc712 = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=newberg.station_id,
            vehicle_id=v712.vehicle_id,
            label="Unit 712 BLS",
        )
        db.add(loc712)
        db.flush()
        print("  Created vehicle 712 (BLS)")
    else:
        if v712.vehicle_type != VehicleType.BLS:
            print(f"  Correcting Vehicle 712: {v712.vehicle_type} → BLS")
            v712.vehicle_type = VehicleType.BLS
            db.flush()
        loc712 = (
            db.query(InventoryLocation)
            .filter(InventoryLocation.vehicle_id == v712.vehicle_id)
            .first()
        )
        if loc712 and loc712.label != "Unit 712 BLS":
            print(f"  Renaming 712 location: '{loc712.label}' → 'Unit 712 BLS'")
            loc712.label = "Unit 712 BLS"
            db.flush()

    # Rename legacy shared jump bag if it exists
    old_shared_jb = (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.station_id == newberg.station_id,
            InventoryLocation.location_type == LocationType.JUMP_BAG,
            InventoryLocation.label == "Jump Bag (Units 710/712)",
        )
        .first()
    )
    if old_shared_jb:
        old_shared_jb.label = "Unit 712 Jump Bag"
        db.flush()
        print("  Renamed legacy jump bag → 'Unit 712 Jump Bag'")

    jb_712, created_712 = get_or_create_jump_bag_location(
        db, station_id=newberg.station_id, label="Unit 712 Jump Bag"
    )
    if created_712:
        print("  Created Unit 712 Jump Bag location")

    print("  Building Unit 712 ambulance inventory...")
    build_ambulance_inventory(db, loc712, station_id=newberg.station_id, is_als=False)
    print("  Building Unit 712 Jump Bag inventory...")
    build_jump_bag(db, jb_712, station_id=newberg.station_id)

    newberg_comp_count = (
        db.query(Compartment)
        .filter(Compartment.location_id.in_([loc712.location_id, jb_712.location_id]))
        .count()
    )
    newberg_par_count = (
        db.query(ParLevel)
        .filter(ParLevel.location_id.in_([loc712.location_id, jb_712.location_id]))
        .count()
    )

    # =========================================================================
    # STATION 2 — Marcellus Township
    # Unit 612 (BLS ambulance) + Unit 632 (QRV fire engine) + Unit 621 (QRV fire
    # engine) — full par levels from real inventory forms (ONBOARD-1).
    # =========================================================================
    print("\nSeeding Marcellus Township Station...")

    MARCELLUS_ADDRESS = "177 E Main St, Marcellus, MI 49067"

    marcellus = (
        db.query(Station).filter(Station.name == "Marcellus Township Station").first()
    )
    if not marcellus:
        marcellus = Station(
            name="Marcellus Township Station",
            address=MARCELLUS_ADDRESS,
            region="Cass County",
            active=True,
        )
        db.add(marcellus)
        db.flush()
        print(f"  Created station: {marcellus.name}")
    elif marcellus.address != MARCELLUS_ADDRESS:
        print(f"  Correcting Marcellus address: '{marcellus.address}' → '{MARCELLUS_ADDRESS}'")
        marcellus.address = MARCELLUS_ADDRESS
        db.flush()

    marcellus_supply = (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.station_id == marcellus.station_id,
            InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
        )
        .first()
    )
    if not marcellus_supply:
        marcellus_supply = InventoryLocation(
            location_type=LocationType.STATION_SUPPLY_ROOM,
            station_id=marcellus.station_id,
            label="Marcellus Station 1 Supply Room",
        )
        db.add(marcellus_supply)
        db.flush()
        print("  Created Marcellus supply room")

    print("  Seeding Marcellus item catalog...")
    marc_cat = seed_station_catalog(db, marcellus.station_id)
    print(f"    {marc_cat} new items created")

    build_supply_room(db, marcellus_supply, marcellus.station_id)

    # Unit 612 (BLS ambulance) — was seeded as "540" (ALS) before Marcellus's real
    # inventory forms were ingested. Rename in place rather than creating a second
    # vehicle record (ONBOARD-1 decision #2): same vehicle, corrected number+type.
    v612 = db.query(Vehicle).filter(Vehicle.vehicle_number == "612").first()
    if not v612:
        # Scoped to this station specifically -- vehicle_number is globally unique,
        # and an unscoped lookup here could find a same-numbered vehicle belonging
        # to an unrelated station in a dev DB with stale/duplicate station rows.
        v540 = (
            db.query(Vehicle)
            .filter(
                Vehicle.vehicle_number == "540",
                Vehicle.station_id == marcellus.station_id,
            )
            .first()
        )
        if v540:
            print("  Renaming vehicle 540 (ALS) → 612 (BLS)")
            v540.vehicle_number = "612"
            v540.vehicle_type = VehicleType.BLS
            db.flush()
            v612 = v540
            loc612 = (
                db.query(InventoryLocation)
                .filter(InventoryLocation.vehicle_id == v612.vehicle_id)
                .first()
            )
            if loc612 and loc612.label != "Unit 612 BLS":
                print(f"  Renaming 612 location: '{loc612.label}' → 'Unit 612 BLS'")
                loc612.label = "Unit 612 BLS"
                db.flush()
        else:
            v612 = Vehicle(
                station_id=marcellus.station_id,
                vehicle_number="612",
                vehicle_type=VehicleType.BLS,
                active=True,
            )
            db.add(v612)
            db.flush()
            loc612 = InventoryLocation(
                location_type=LocationType.VEHICLE,
                station_id=marcellus.station_id,
                vehicle_id=v612.vehicle_id,
                label="Unit 612 BLS",
            )
            db.add(loc612)
            db.flush()
            print("  Created vehicle 612 (BLS)")
    else:
        if v612.vehicle_type != VehicleType.BLS:
            print(f"  Correcting Vehicle 612: {v612.vehicle_type} → BLS")
            v612.vehicle_type = VehicleType.BLS
            db.flush()
        loc612 = (
            db.query(InventoryLocation)
            .filter(InventoryLocation.vehicle_id == v612.vehicle_id)
            .first()
        )
        if loc612 and loc612.label != "Unit 612 BLS":
            print(f"  Renaming 612 location: '{loc612.label}' → 'Unit 612 BLS'")
            loc612.label = "Unit 612 BLS"
            db.flush()

    print("  Building Unit 612 ambulance inventory...")
    build_marcellus_ambulance_inventory(db, loc612, station_id=marcellus.station_id)

    # Unit 632 — Fire Engine Truck (QRV)
    v632 = db.query(Vehicle).filter(Vehicle.vehicle_number == "632").first()
    if not v632:
        v632 = Vehicle(
            station_id=marcellus.station_id,
            vehicle_number="632",
            vehicle_type=VehicleType.QRV,
            active=True,
        )
        db.add(v632)
        db.flush()
        loc632 = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=marcellus.station_id,
            vehicle_id=v632.vehicle_id,
            label="Unit 632 QRV",
        )
        db.add(loc632)
        db.flush()
        print("  Created vehicle 632 (QRV — fire engine)")
    else:
        loc632 = (
            db.query(InventoryLocation)
            .filter(InventoryLocation.vehicle_id == v632.vehicle_id)
            .first()
        )

    print("  Building Unit 632 fire engine inventory...")
    build_fire_truck_632_inventory(db, loc632, station_id=marcellus.station_id)

    # Unit 621 — Fire Engine Truck (QRV)
    v621 = db.query(Vehicle).filter(Vehicle.vehicle_number == "621").first()
    if not v621:
        v621 = Vehicle(
            station_id=marcellus.station_id,
            vehicle_number="621",
            vehicle_type=VehicleType.QRV,
            active=True,
        )
        db.add(v621)
        db.flush()
        loc621 = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=marcellus.station_id,
            vehicle_id=v621.vehicle_id,
            label="Unit 621 QRV",
        )
        db.add(loc621)
        db.flush()
        print("  Created vehicle 621 (QRV — fire engine)")
    else:
        loc621 = (
            db.query(InventoryLocation)
            .filter(InventoryLocation.vehicle_id == v621.vehicle_id)
            .first()
        )

    print("  Building Unit 621 fire engine inventory...")
    build_fire_truck_621_inventory(db, loc621, station_id=marcellus.station_id)

    marcellus_comp_count = (
        db.query(Compartment)
        .filter(
            Compartment.location_id.in_(
                [loc612.location_id, loc632.location_id, loc621.location_id]
            )
        )
        .count()
    )
    marcellus_par_count = (
        db.query(ParLevel)
        .filter(
            ParLevel.location_id.in_(
                [loc612.location_id, loc632.location_id, loc621.location_id]
            )
        )
        .count()
    )

    # =========================================================================
    # STATION 3 — Newberg Training Station
    # Training Unit A + B, Jump Bag A + B
    # Item catalog only; par levels assigned via admin UI
    # =========================================================================
    print("\nSeeding Newberg Training Station...")

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
        print(f"  Created station: {training.name}")
    else:
        if training.primary_color != "#e65100":
            training.primary_color = "#e65100"
            print("  Updated training station color to #e65100 (orange)")

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
        print("  Created Training supply room")

    print("  Seeding Training item catalog...")
    train_cat = seed_station_catalog(db, training.station_id)
    print(f"    {train_cat} new items created")

    build_supply_room(db, training_supply, training.station_id)

    # Training Unit A
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
        db.add(
            InventoryLocation(
                location_type=LocationType.VEHICLE,
                station_id=training.station_id,
                vehicle_id=v_train_a.vehicle_id,
                label="Training Unit A",
            )
        )
        db.flush()
        print("  Created Training Unit A (BLS)")

    # Training Unit B
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
        db.add(
            InventoryLocation(
                location_type=LocationType.VEHICLE,
                station_id=training.station_id,
                vehicle_id=v_train_b.vehicle_id,
                label="Training Unit B",
            )
        )
        db.flush()
        print("  Created Training Unit B (BLS)")

    _jb_train_a, cja = get_or_create_jump_bag_location(
        db, station_id=training.station_id, label="Training Jump Bag A"
    )
    if cja:
        print("  Created Training Jump Bag A")
    _jb_train_b, cjb = get_or_create_jump_bag_location(
        db, station_id=training.station_id, label="Training Jump Bag B"
    )
    if cjb:
        print("  Created Training Jump Bag B")

    print(
        "  (Training units — catalog seeded; supervisor assigns par levels via admin UI)"
    )

    # =========================================================================
    # STATION 4 — ⚠ TEST STATION (Dev Only)
    # Unit TEST (QRV) — catalog + [TEST] items seeded
    # Par levels assigned via admin UI
    # =========================================================================
    print("\nSeeding ⚠ TEST STATION — Dev Only...")

    test_station = (
        db.query(Station).filter(Station.name == "⚠ TEST STATION — Dev Only").first()
    )
    if not test_station:
        test_station = Station(
            name="⚠ TEST STATION — Dev Only",
            address="Dev Environment",
            region="⚠ Not a real station",
            active=True,
        )
        db.add(test_station)
        db.flush()
        print("  Created test station")

    test_supply = (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.station_id == test_station.station_id,
            InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
        )
        .first()
    )
    if not test_supply:
        test_supply = InventoryLocation(
            location_type=LocationType.STATION_SUPPLY_ROOM,
            station_id=test_station.station_id,
            label="⚠ TEST Supply Room — Dev Only",
        )
        db.add(test_supply)
        db.flush()
        print("  Created TEST supply room")

    print("  Seeding TEST item catalog...")
    test_cat = seed_station_catalog(db, test_station.station_id)
    print(f"    {test_cat} new items created")

    build_supply_room(db, test_supply, test_station.station_id)

    # [TEST]-prefixed items for dev wizard testing — test station only
    test_items = [
        {
            "name": "[TEST] Supply Item",
            "category": _C,
            "check_type": _SUP,
            "unit_of_measure": "each",
        },
        {
            "name": "[TEST] O2 PSI Reading",
            "category": _E,
            "check_type": _MEAS,
            "unit_of_measure": "PSI",
            "measurement_minimum": 500.0,
            "measurement_maximum": 2200.0,
        },
        {
            "name": "[TEST] Equipment Battery",
            "category": _E,
            "check_type": _FUNC,
            "unit_of_measure": "N/A",
        },
        {
            "name": "[TEST] Last Service Date",
            "category": _E,
            "check_type": _DATE,
            "unit_of_measure": "N/A",
            "recurrence_days": 30,
        },
        {
            "name": "[TEST] Protocol Document",
            "category": _D,
            "check_type": _DOC,
            "unit_of_measure": "N/A",
        },
        {
            "name": "[TEST] Short Supply",
            "category": _C,
            "check_type": _SUP,
            "unit_of_measure": "each",
        },
        {
            "name": "[TEST] Broken Equipment",
            "category": _E,
            "check_type": _FUNC,
            "unit_of_measure": "N/A",
        },
    ]
    for entry in test_items:
        get_or_create_item(
            db, station_id=test_station.station_id, category_group=None, **entry
        )
    db.flush()

    v_test = db.query(Vehicle).filter(Vehicle.vehicle_number == "TEST").first()
    if not v_test:
        v_test = Vehicle(
            station_id=test_station.station_id,
            vehicle_number="TEST",
            vehicle_type=VehicleType.QRV,
            active=True,
        )
        db.add(v_test)
        db.flush()
        db.add(
            InventoryLocation(
                location_type=LocationType.VEHICLE,
                station_id=test_station.station_id,
                vehicle_id=v_test.vehicle_id,
                label="Unit TEST ⚠ Dev Only",
            )
        )
        db.flush()
        print("  Created Unit TEST (QRV)")

    print("  (Unit TEST — catalog seeded; supervisor assigns par levels via admin UI)")

    # =========================================================================
    # STATION MEMBERSHIP — Bootstrap admin user
    # =========================================================================
    print("\nSeeding station memberships...")

    BOOTSTRAP_ADMIN = "jinniyah@gmail.com"
    BOOTSTRAP_NAME = "Jinni Allen"
    SEED_USER = "seed.py"

    DEV_MEMBERS = [
        ("test-administrator@ems.local", "Test Administrator", "Administrator"),
        ("test-supervisor@ems.local", "Test Supervisor", "Supervisor"),
        ("test-responder@ems.local", "Test Responder", "Responder"),
    ]

    for station in [newberg, marcellus, training, test_station]:
        existing = (
            db.query(StationMember)
            .filter(
                StationMember.station_id == station.station_id,
                StationMember.user_id == BOOTSTRAP_ADMIN,
            )
            .first()
        )
        if not existing:
            db.add(
                StationMember(
                    station_id=station.station_id,
                    user_id=BOOTSTRAP_ADMIN,
                    preferred_name=BOOTSTRAP_NAME,
                    role="Administrator",
                    assigned_by=SEED_USER,
                    active=True,
                )
            )
            print(f"  Assigned {BOOTSTRAP_ADMIN} → {station.name}")
        elif not existing.active:
            existing.active = True
            print(f"  Re-activated {BOOTSTRAP_ADMIN} → {station.name}")
        else:
            print(f"  {BOOTSTRAP_ADMIN} already member of {station.name} — skipping")

        for uid, name, role in DEV_MEMBERS:
            existing_dev = (
                db.query(StationMember)
                .filter(
                    StationMember.station_id == station.station_id,
                    StationMember.user_id == uid,
                )
                .first()
            )
            if not existing_dev:
                db.add(
                    StationMember(
                        station_id=station.station_id,
                        user_id=uid,
                        preferred_name=name,
                        role=role,
                        assigned_by=SEED_USER,
                        active=True,
                    )
                )
                print(f"  Assigned {uid} → {station.name}")
            elif not existing_dev.active:
                existing_dev.active = True
                print(f"  Re-activated {uid} → {station.name}")
            else:
                print(f"  {uid} already member of {station.name} — skipping")

    db.flush()

    # =========================================================================
    # Commit and report
    # =========================================================================
    db.commit()

    total_items_newberg = (
        db.query(Item).filter(Item.station_id == newberg.station_id).count()
    )
    total_items_marcellus = (
        db.query(Item).filter(Item.station_id == marcellus.station_id).count()
    )

    print(f"""
  ✓ Seed complete.

  Newberg Township Station:
    Station ID:           {newberg.station_id}
    Unit 712 BLS:         location_id={loc712.location_id}
    Unit 712 Jump Bag:    location_id={jb_712.location_id}
    Compartments (712+JB):{newberg_comp_count}
    Par levels (712+JB):  {newberg_par_count}
    Items in catalog:     {total_items_newberg}

  Marcellus Township Station:
    Station ID:           {marcellus.station_id}
    Unit 612 BLS:         location_id={loc612.location_id}
    Unit 632 QRV:         location_id={loc632.location_id}
    Unit 621 QRV:         location_id={loc621.location_id}
    Compartments (612+632+621): {marcellus_comp_count}
    Par levels (612+632+621):   {marcellus_par_count}
    Items in catalog:     {total_items_marcellus}

  Newberg Training Station (orange — #e65100):
    Station ID:           {training.station_id}
    Training Unit A/B + Jump Bag A/B: catalog seeded, no par levels

  ⚠ TEST STATION — Dev Only:
    Station ID:           {test_station.station_id}
    Unit TEST (QRV):      catalog + [TEST] items seeded, no par levels

  Next steps for Training, Test stations:
    1. Admin creates compartments via Station Administration → Vehicles
    2. Admin assigns par levels via Station Administration → Items
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
