"""
schemas/par_level.py
Pydantic schemas for ParLevel request validation and response serialization.

Phase 4 change: compartment_id is now an optional field.
- compartment_id set   → compartment-scoped par (preferred, matches the form)
- compartment_id null  → vehicle-level par (legacy, backward compatible)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ParLevelBase(BaseModel):
    item_id: int = Field(..., gt=0, description="Item this par level applies to")
    location_id: int = Field(..., gt=0, description="Inventory location (vehicle or supply room)")
    compartment_id: Optional[int] = Field(
        default=None,
        gt=0,
        description=(
            "Compartment within the location this par level applies to. "
            "When set, scopes the par to a specific compartment (e.g. 'Drug Bag'). "
            "When null, applies to the whole location."
        ),
    )
    min_quantity: int = Field(..., gt=0, description="Minimum acceptable quantity (Need on form)")
    max_quantity: int = Field(..., gt=0, description="Maximum stocking quantity (Restock to)")
    active: bool = Field(default=True, description="Inactive par levels excluded from check wizard")
    priority_check: Optional[bool] = Field(
        default=False,
        description="When True, item is pulled above the compartment list in Step 2 for immediate confirmation",
    )
    priority_question: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Plain-English question shown to the responder (e.g. 'Is the ready light solid green?'). Falls back to item name if unset.",
    )
    is_damaged: bool = Field(
        default=False,
        description="When True, item is marked damaged/unavailable at this compartment.",
    )

    @model_validator(mode="after")
    def validate_min_max(self) -> "ParLevelBase":
        if self.max_quantity < self.min_quantity:
            raise ValueError(
                f"max_quantity ({self.max_quantity}) must be >= "
                f"min_quantity ({self.min_quantity})."
            )
        return self


class ParLevelCreate(ParLevelBase):
    """Request body for POST /inventory/par-levels."""
    pass


class ParLevelRead(ParLevelBase):
    """Response model for par level endpoints."""

    model_config = ConfigDict(from_attributes=True)

    par_id: int
    created_at: datetime
    updated_at: datetime


class AssignItemRequest(BaseModel):
    """
    Request body for POST /admin/items/{id}/assign.
    Frontend supplies vehicle_id + compartment_id; backend derives location_id.
    """
    vehicle_id:     int = Field(..., gt=0)
    compartment_id: int = Field(..., gt=0)
    min_quantity:   int = Field(..., gt=0, description="Minimum required quantity")
    max_quantity:   int = Field(..., gt=0, description="Restock-to quantity")

    @model_validator(mode="after")
    def validate_min_max(self) -> "AssignItemRequest":
        if self.max_quantity < self.min_quantity:
            raise ValueError(
                f"max_quantity ({self.max_quantity}) must be >= "
                f"min_quantity ({self.min_quantity})."
            )
        return self


class ParLevelAssignment(BaseModel):
    """
    Enriched par level read — includes vehicle and compartment names
    for the item assignments panel in the admin UI.
    """
    model_config = ConfigDict(from_attributes=True)

    par_id:          int
    item_id:         int
    location_id:     int
    compartment_id:  Optional[int]
    min_quantity:      int
    max_quantity:      int
    active:            bool
    priority_check:    Optional[bool] = False
    priority_question: Optional[str]  = None
    is_damaged:        bool = False
    created_at:        datetime
    updated_at:        datetime
    # Enriched fields — joined server-side
    vehicle_id:       Optional[int]  = None
    vehicle_number:   Optional[str]  = None
    vehicle_type:     Optional[str]  = None
    location_label:   Optional[str]  = None
    compartment_name: Optional[str]  = None
    # Populated by the compartment-centric endpoint only
    item_name:        Optional[str]  = None
    item_check_type:  Optional[str]  = None


class UpdateParLevelRequest(BaseModel):
    """Request body for PATCH /admin/par-levels/{id}."""
    min_quantity:      int = Field(..., gt=0)
    max_quantity:      int = Field(..., gt=0)
    priority_check:    Optional[bool] = Field(default=None)
    priority_question: Optional[str]  = Field(default=None, max_length=150)

    @model_validator(mode="after")
    def validate_min_max(self) -> "UpdateParLevelRequest":
        if self.max_quantity < self.min_quantity:
            raise ValueError("max_quantity must be >= min_quantity.")
        return self
