"""
schemas/item.py
Pydantic schemas for Item request validation and response serialization.

Design decisions:
- name uniqueness is enforced at the DB level (unique=True on the column).
  The router catches IntegrityError and converts it to a 409 Conflict.
- controlled_substance defaults to False — must be explicitly set to True
  for medications tracked under the dual-signature CS workflow.
- unit_of_measure is free-form string (e.g. "mg", "mL", "each", "pair")
  rather than an enum — the domain has too many valid values to enumerate
  and a lookup table would be over-engineering for Phase 2.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ems_readykit.models.item import ItemCategory


class ItemBase(BaseModel):
    """Fields supplied by the caller on create."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Unique item name",
        examples=["Epinephrine 1mg/mL", "Gauze 4x4 Sterile"],
    )
    category: ItemCategory = Field(
        ...,
        description="Medication | Consumable | Equipment",
    )
    controlled_substance: bool = Field(
        default=False,
        description="True for medications under dual-signature CS tracking (ALS only)",
    )
    unit_of_measure: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Unit of measure (e.g. 'mg', 'mL', 'each', 'pair')",
        examples=["mL", "each", "mg"],
    )
    active: bool = Field(
        default=True,
        description="Inactive items are hidden from operational views but retained for audit history",
    )

    @field_validator("name", "unit_of_measure", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("Field must not be blank or whitespace only.")
            return stripped
        return v


class ItemCreate(ItemBase):
    """Request body for POST /items."""
    pass


class ItemRead(ItemBase):
    """Response model for item endpoints."""

    model_config = ConfigDict(from_attributes=True)

    item_id: int
    created_at: datetime
    updated_at: datetime
