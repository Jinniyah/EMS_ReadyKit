"""
schemas/par_level.py
Pydantic schemas for ParLevel request validation and response serialization.

Design decisions:
- min_quantity must be > 0 — a par level of zero provides no operational signal.
- max_quantity must be > min_quantity — enforced at the schema layer so the
  DB constraint (which doesn't validate this relationship) is never reached
  with logically invalid data.
- The item_id + location_id UniqueConstraint on the DB means POST returns
  409 Conflict if a par level already exists. The router handles this and
  directs callers to use PUT to update.
- No ParLevelUpdate schema — the full record is small enough that a replace
  operation (delete + create) is the correct pattern for Phase 2.
  A PATCH endpoint can be added in Phase 3 if needed.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ParLevelBase(BaseModel):
    """Fields supplied by the caller on create."""

    item_id: int = Field(..., gt=0, description="ID of the item this par level applies to")
    location_id: int = Field(..., gt=0, description="ID of the location this par level applies to")
    min_quantity: int = Field(
        ...,
        gt=0,
        description="Minimum acceptable quantity on hand. Below this triggers a low-stock flag.",
    )
    max_quantity: int = Field(
        ...,
        gt=0,
        description="Target maximum quantity for restocking. Must be greater than min_quantity.",
    )

    @model_validator(mode="after")
    def max_must_exceed_min(self) -> "ParLevelBase":
        """
        Ensures max_quantity > min_quantity.
        A par level where max <= min is operationally meaningless and would
        cause restocking logic to behave incorrectly.
        """
        if self.max_quantity <= self.min_quantity:
            raise ValueError(
                f"max_quantity ({self.max_quantity}) must be greater than "
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
