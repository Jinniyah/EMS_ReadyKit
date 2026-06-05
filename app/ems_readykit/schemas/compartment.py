"""
schemas/compartment.py
Pydantic schemas for Compartment request validation and response serialization.

## Fields added in Phase 4 / Migration 0003

    location_descriptor  — physical position shown in UI to help medics navigate
    parent_compartment_id — for sub-compartments (Jump Bag pocket-in-pocket)
    restriction_note      — replaces als_only boolean with flexible text restriction

## Real examples from Ambulance 712

    # Standard interior compartment
    CompartmentCreate(
        name="PC 1 (Airway)",
        location_descriptor="Interior, left side, behind driver seat",
        sort_order=1,
        location_id=1,
    )

    # ALS-only compartment
    CompartmentCreate(
        name="Drug Bag",
        location_descriptor="Interior, PC 9 Drug Cabinet",
        sort_order=9,
        restriction_note="ALS crews only",
        location_id=1,
    )

    # Exterior compartment
    CompartmentCreate(
        name="Driver Side EC 1",
        location_descriptor="Exterior, driver side, forward bay",
        sort_order=20,
        location_id=1,
    )

    # Restricted section
    CompartmentCreate(
        name="Under Hood",
        location_descriptor="Engine compartment",
        sort_order=99,
        restriction_note="Approved personnel only — mechanical authorization required",
        location_id=1,
    )

    # Jump Bag sub-compartment
    CompartmentCreate(
        name="Main Pocket — Flap Left",
        location_descriptor="Left flap of main pocket",
        sort_order=44,
        parent_compartment_id=40,  # "Main Pocket"
        location_id=5,  # Jump Bag location
    )
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CompartmentBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Physical compartment label matching the inventory form",
        examples=[
            "PC 1 (Airway)", "Drug Bag", "Driver Side EC 1",
            "Main Pocket — Flap Left", "Truck Operations"
        ],
    )
    location_descriptor: Optional[str] = Field(
        default=None,
        max_length=150,
        description=(
            "Physical position description shown in the UI to help medics navigate. "
            "e.g. 'Interior, left side behind driver seat' or "
            "'Exterior, driver side, forward bay'"
        ),
    )
    sort_order: int = Field(
        default=0,
        ge=0,
        description=(
            "Display order matching the physical walk-around sequence. "
            "Interior PCs first, then exterior ECs, then bags, then equipment."
        ),
    )
    parent_compartment_id: Optional[int] = Field(
        default=None,
        gt=0,
        description=(
            "For sub-compartments (e.g. Jump Bag pocket-within-pocket). "
            "Points to the parent compartment_id. "
            "e.g. 'Main Pocket — Flap Left' → parent = 'Main Pocket'"
        ),
    )
    restriction_note: Optional[str] = Field(
        default=None,
        max_length=100,
        description=(
            "Access restriction displayed prominently in the UI. "
            "None = accessible to all authenticated crew. "
            "e.g. 'ALS crews only', 'Approved personnel only'"
        ),
    )
    # Retained for backward compatibility — prefer restriction_note going forward
    als_only: bool = Field(
        default=False,
        description=(
            "Deprecated — use restriction_note='ALS crews only' instead. "
            "Retained for backward compatibility with existing API consumers."
        ),
    )
    active: bool = Field(default=True)
    requires_full_check: bool = Field(
        default=False,
        description=(
            "When True, No Change is blocked for this compartment — responder must review every item. "
            "Use for Truck Operations and any compartment requiring physical verification."
        ),
    )


class CompartmentCreate(CompartmentBase):
    """Request body for POST /inventory/locations/{id}/compartments."""
    location_id: int = Field(..., gt=0, description="Parent inventory location ID")


class CompartmentRead(CompartmentBase):
    """Response model for compartment endpoints."""
    model_config = ConfigDict(from_attributes=True)

    compartment_id: int
    location_id: int
    created_at: datetime
    updated_at: datetime
