"""
models/compartment.py
Compartment — a named physical storage area within a vehicle, supply room,
or portable bag.

## Physical layout — Ambulance 712

Interior patient compartments (PC):
    PC 1 through PC 18 — numbered compartments inside the ambulance
    Named bags: First Out Bag, Drug Bag, Narcotic Lock Bag, BLS Drug Bag, Jump Bag

Exterior compartments (EC):
    Driver Side EC 1, 2, 3     — exterior storage bays on driver side
    Passenger Side EC 1, 2, 3  — exterior storage bays on passenger side

Special areas:
    Admin Counter, Bench, Suction Drawer, Glove Compartment
    Charger Counter, Stretcher, Under Hood

## Sub-compartments (Jump Bag)

The Jump Bag has pockets within pockets:
    Main Pocket
    Main Pocket — Elastic Pouches Back
    Main Pocket — Elastic Pouches Front
    Main Pocket — Flap Left
    Main Pocket — Flap Right

These are modeled as separate Compartments with parent_compartment_id pointing
to "Main Pocket". sort_order keeps them visually grouped in the UI.

## Access restrictions

The paper form marks:
    "ALS Only" items        → als_only flag is true (Drug Bag, Narcotic Lock Bag)
    "Under Hood, Approved Personnel Only" → restriction_note set

Rather than multiple boolean flags, restriction_note is a free-text field
that surfaces in the UI. This handles any future restriction type without
a schema change.

Examples:
    restriction_note = "ALS crews only"
    restriction_note = "Approved personnel only — mechanical authorization required"
    restriction_note = "Supervisor access only"

## Location descriptor

location_descriptor gives the physical position on the truck or bag —
essential for medics who work on multiple vehicle configurations.

Examples:
    "Left side, rear — driver side"
    "Exterior, driver side, front"
    "Behind airway seat"
    "Under attendant seat"
    "Front pocket"
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.check_line_item import CheckLineItem
    from ems_readykit.models.inventory_location import InventoryLocation
    from ems_readykit.models.par_level import ParLevel


class Compartment(TimestampMixin, Base):
    __tablename__ = "compartments"
    __table_args__ = (
        UniqueConstraint("location_id", "name", name="uq_compartment_location_name"),
    )

    compartment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    location_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_locations.location_id"), nullable=False
    )

    # Human-readable name matching the physical label on the vehicle or bag.
    # e.g. "PC 1 (Airway)", "Drug Bag", "Driver Side EC 1",
    #      "Main Pocket — Flap Left", "Truck Operations"
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional physical location description — helps medics navigate the truck.
    # e.g. "Interior, left side behind driver seat"
    # e.g. "Exterior, driver side, forward bay"
    # e.g. "Front pocket of jump bag"
    location_descriptor: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Display order matching physical walk-around sequence.
    # Interior PCs → Exterior ECs → Bags → Equipment
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Optional parent for sub-compartments (e.g. Jump Bag pocket-within-pocket).
    # "Main Pocket — Flap Left" → parent = "Main Pocket"
    parent_compartment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("compartments.compartment_id"), nullable=True
    )

    # Free-text access restriction note shown prominently in the UI.
    # None = accessible to all authenticated crew.
    # e.g. "ALS crews only", "Approved personnel only"
    restriction_note: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Legacy boolean kept for backward compatibility with existing API consumers.
    # New code should use restriction_note = "ALS crews only" instead.
    # Will be removed in a future migration once all clients use restriction_note.
    als_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # When True, No Change is blocked for this compartment — responder must open every item.
    # Used for Truck Operations (FUNCTIONAL checks require physically starting the truck).
    requires_full_check: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.false()
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    location: Mapped["InventoryLocation"] = relationship(
        "InventoryLocation", back_populates="compartments"
    )
    parent: Mapped[Optional["Compartment"]] = relationship(
        "Compartment",
        remote_side="Compartment.compartment_id",
        back_populates="children",
    )
    children: Mapped[List["Compartment"]] = relationship(
        "Compartment",
        back_populates="parent",
        order_by="Compartment.sort_order",
    )
    par_levels: Mapped[List["ParLevel"]] = relationship(
        "ParLevel", back_populates="compartment", cascade="all, delete-orphan"
    )
    check_line_items: Mapped[List["CheckLineItem"]] = relationship(
        "CheckLineItem", back_populates="compartment"
    )

    def __repr__(self) -> str:
        return (
            f"<Compartment id={self.compartment_id} "
            f"location_id={self.location_id} name={self.name!r}>"
        )
