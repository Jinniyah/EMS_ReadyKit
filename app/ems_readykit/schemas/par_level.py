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
    max_quantity: int = Field(..., gt=0, description="Maximum stocking quantity")

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
