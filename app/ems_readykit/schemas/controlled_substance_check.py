"""
schemas/controlled_substance_check.py
Pydantic schemas for ControlledSubstanceCheck request validation and response serialization.

Phase 3 change: primary_signer is now Optional in the Create schema.
The router overwrites it with current_user.name from the JWT, so callers
do not need to supply it. secondary_signer is still required — the dual-
signature requirement means a second person must explicitly attest.

The same-signer validation is still present in the schema for the read path,
but the router also validates that current_user.name != secondary_signer
before persisting.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ControlledSubstanceCheckBase(BaseModel):
    """Fields common to create and read schemas."""

    vehicle_id: int = Field(..., gt=0, description="ALS vehicle being checked")
    primary_signer: Optional[str] = Field(
        default=None,
        max_length=100,
        description=(
            "Name of the primary signer. "
            "Set automatically from the authenticated user's identity on create."
        ),
    )
    secondary_signer: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the secondary signer (witness). Must differ from primary_signer.",
        examples=["M. Johnson"],
    )
    timestamp: datetime = Field(
        ...,
        description="Exact UTC timestamp when the check was completed",
    )
    discrepancy_flag: bool = Field(
        default=False,
        description=(
            "Set to True if any controlled substance count does not match expected. "
            "Triggers a HIGH severity audit event automatically."
        ),
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Free-text notes. Strongly encouraged when discrepancy_flag=True.",
    )


class ControlledSubstanceCheckCreate(ControlledSubstanceCheckBase):
    """Request body for POST /checks/controlled-substance."""

    pass


class ControlledSubstanceCheckRead(ControlledSubstanceCheckBase):
    """Response model for controlled substance check endpoints."""

    model_config = ConfigDict(from_attributes=True)

    cs_check_id: int
    created_at: datetime
    updated_at: datetime
