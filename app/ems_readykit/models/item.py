"""
models/item.py
Item — defines what is tracked in inventory.

## Item check types — validated against Ambulance 712 inventory forms

The real inventory forms for Ambulance 712 reveal four fundamentally
different kinds of checks a crew member performs. The check_type field
drives which fields are used during a daily check and which UI controls
the frontend renders.

    SUPPLY (default)
        A counted or presence-verified supply item.
        Fields used: quantity_needed, quantity_found, lot_id (if expires)
        Examples: Kerlix (x3), Tourniquet (x2), OPAs/NPAs, Stethoscope

    MEASUREMENT
        A numeric reading taken from equipment — not a count.
        Fields used: measurement_value (float), measurement_unit
        Examples:
          - O2 tank PSI (on-board O2, portable O2, stretcher O2, jump bag O2)
          - Glucometer test strip expiry (date component only)
        The "need" for a measurement is a minimum threshold (e.g. PSI >= 500)
        stored in ParLevel.min_quantity cast as a float.

    FUNCTIONAL
        A pass/fail operational check — does the system work?
        Fields used: functional_pass (bool)
        Examples from Truck Operations section:
          - Runs and Starts
          - External Warning Systems (Lights & Sirens)
          - Patient compartment climate controlled
          - Communication - Medcom Compliant
          - Battery OK? (AED, LUCAS, stretcher)

    DATE_RECORD
        A date is recorded — not a count, not a measurement.
        Fields used: date_value (date)
        Examples:
          - AED Date of Last Charge
          - LUCAS Device Date of Last Charge
        These are maintenance records. A supervisor sets a required
        recurrence interval; the check records the actual date.

    DOCUMENT
        Presence-only check for required paperwork and reference materials.
        Fields used: quantity_found (0 = missing, 1 = present) — no lot tracking.
        Examples: PCR or HERN PCR, Billing Form, AMA, Protocol Book,
                  Clipboard w/ Paperwork, Insurance Information

## Category
    MEDICATION   — controlled or non-controlled drugs (always SUPPLY check_type)
    CONSUMABLE   — single-use supplies (SUPPLY check_type)
    EQUIPMENT    — reusable gear; may be SUPPLY, MEASUREMENT, FUNCTIONAL, or DATE_RECORD
    DOCUMENT     — paperwork; always DOCUMENT check_type

## AED example — one piece of equipment, multiple items
The LifePak AED is modeled as four separate Item records in the same compartment:
    Item: "AED Battery"              check_type=FUNCTIONAL  → Battery OK? yes/no
    Item: "AED Date of Last Charge"  check_type=DATE_RECORD → date recorded
    Item: "AED Pads Adult"           check_type=SUPPLY      → quantity + expiry date
    Item: "AED Pads Pediatric"       check_type=SUPPLY      → quantity + expiry date

## O2 tank example — presence + PSI reading
    Item: "On-Board O2 Tank"         check_type=SUPPLY      → present yes/no (qty=1)
    Item: "On-Board O2 PSI"          check_type=MEASUREMENT → PSI reading (e.g. 1800)
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.stock_lot import StockLot
    from ems_readykit.models.par_level import ParLevel
    from ems_readykit.models.check_line_item import CheckLineItem


class ItemCategory(str, enum.Enum):
    MEDICATION = "Medication"
    CONSUMABLE = "Consumable"
    EQUIPMENT  = "Equipment"
    DOCUMENT   = "Document"


class ItemCheckType(str, enum.Enum):
    SUPPLY      = "SUPPLY"       # counted / presence-verified supply (default)
    MEASUREMENT = "MEASUREMENT"  # numeric reading (PSI, temperature, glucose)
    FUNCTIONAL  = "FUNCTIONAL"   # pass/fail operational check (battery OK, runs & starts)
    DATE_RECORD = "DATE_RECORD"  # date recorded (last charge date, last service date)
    DOCUMENT    = "DOCUMENT"     # presence-only paperwork check


class Item(TimestampMixin, Base):
    __tablename__ = "items"

    item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Human-readable name matching the paper inventory form label
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)

    category: Mapped[ItemCategory] = mapped_column(
        SAEnum(ItemCategory, native_enum=False), nullable=False
    )

    # Drives which fields are used in CheckLineItem and which UI control to render.
    # See module docstring for full explanation and examples.
    check_type: Mapped[ItemCheckType] = mapped_column(
        SAEnum(ItemCheckType, native_enum=False),
        nullable=False,
        default=ItemCheckType.SUPPLY,
    )

    # Controlled substances require ALS vehicle + dual-witness count
    controlled_substance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Unit of measure for SUPPLY items (each, box, roll, mg, mL...)
    # For MEASUREMENT items this is the reading unit (PSI, °F, mg/dL...)
    # For FUNCTIONAL and DATE_RECORD items this can be left as "N/A"
    unit_of_measure: Mapped[str] = mapped_column(String(30), nullable=False)

    # For MEASUREMENT items: the minimum acceptable value
    # e.g. O2 tank PSI minimum threshold of 500
    # Stored here so supervisors can configure per item, not per par level
    measurement_minimum: Mapped[Optional[float]] = mapped_column(nullable=True)

    # For MEASUREMENT items: maximum acceptable value (optional)
    # e.g. blood glucose >400 mg/dL is critical high
    measurement_maximum: Mapped[Optional[float]] = mapped_column(nullable=True)

    # For DATE_RECORD items: maximum number of days between required events
    # e.g. AED must be charged at least every 90 days → recurrence_days = 90
    recurrence_days: Mapped[Optional[int]] = mapped_column(nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── AI identification fields (migration 0009) ─────────────────────────────
    # These columns are dormant until the AI image recognition module is built.
    # They are nullable and have zero impact on existing workflows.

    # Comma-separated keywords an AI classifier might return.
    # e.g. "tourniquet,CAT tourniquet,hemostatic"
    ai_tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Other names crews use for this item.
    # e.g. "cric kit,surgical airway,bougie"
    alternate_names: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # URL of a reference photo stored in Azure Blob Storage.
    # Used by the AI pipeline to verify a visual match.
    reference_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # UPC or GS1 barcode — unique across all items.
    # AI image pipeline can attempt to read barcodes from photos.
    barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)

    # Relationships
    stock_lots: Mapped[List["StockLot"]] = relationship("StockLot", back_populates="item")
    par_levels: Mapped[List["ParLevel"]] = relationship("ParLevel", back_populates="item")
    check_line_items: Mapped[List["CheckLineItem"]] = relationship(
        "CheckLineItem", back_populates="item"
    )

    def __repr__(self) -> str:
        return (
            f"<Item id={self.item_id} name={self.name!r} "
            f"category={self.category} check_type={self.check_type}>"
        )
