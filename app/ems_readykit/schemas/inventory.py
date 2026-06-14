"""
schemas/inventory.py
Pydantic schemas for inventory patch operations that don't fit cleanly
into the existing stock/par/location schema files.

ItemStatusPatch -- request body for PATCH /inventory/items/{id}/status (DMG-B1).
  Marks or clears a par level as damaged at a specific compartment.
"""

from __future__ import annotations

from pydantic import BaseModel


class ItemStatusPatch(BaseModel):
    """Request body for PATCH /inventory/items/{id}/status."""

    compartment_id: int
    is_damaged: bool
