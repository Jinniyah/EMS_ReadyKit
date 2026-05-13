"""
schemas/compartment.py
Pydantic schemas for Compartment request validation and response serialization.
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
        description="Physical compartment label (e.g. 'Compartment #1', 'Drug Bag')",
        examples=["Compartment #1", "Drug Bag", "First Out Bag", "Narcotic Lock Bag"],
    )
    sort_order: int = Field(
        default=0,
        ge=0,
        description="Display order — lower numbers appear first in UI and on check forms",
    )
    als_only: bool = Field(
        default=False,
        description="True for ALS-only compartments (Drug Bag, Narcotic Lock Bag) — hidden on BLS trucks",
    )
    active: bool = Field(default=True)


class CompartmentCreate(CompartmentBase):
    """Request body for POST /inventory/locations/{id}/compartments."""
    location_id: int = Field(..., gt=0, description="Parent inventory location")


class CompartmentRead(CompartmentBase):
    """Response model for compartment endpoints."""

    model_config = ConfigDict(from_attributes=True)

    compartment_id: int
    location_id: int
    created_at: datetime
    updated_at: datetime
