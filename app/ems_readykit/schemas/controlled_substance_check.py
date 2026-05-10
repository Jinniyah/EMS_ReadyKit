"""
schemas/controlled_substance_check.py
Pydantic schemas for ControlledSubstanceCheck request validation and response serialization.

Design decisions:
- primary_signer and secondary_signer must be different people.
  This is enforced at the schema layer, not just the DB, so the validation
  error is returned to the caller immediately with a clear message.
- The ALS-only rule (only ALS vehicles may have CS checks) is enforced
  in the router by looking up the vehicle type before persisting.
  It is NOT enforced in the schema because the schema does not have
  DB access — that would violate separation of concerns.
- discrepancy_flag=True automatically triggers a HIGH severity audit event
  in the router. The schema just carries the flag; the side effect is
  the router's responsibility.
- notes are optional but strongly encouraged when discrepancy_flag=True.
  We log a warning if a discrepancy is flagged without notes, but we
  do not reject the request — an operational record with a flag is better
  than no record at all.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ControlledSubstanceCheckBase(BaseModel):
    """Fields supplied by the caller on create."""

    vehicle_id: int = Field(..., gt=0, description="ALS vehicle being checked")
    primary_signer: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the primary signer (typically the medic performing the check)",
        examples=["J. Smith"],
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
        description="Free-text notes. Required context when discrepancy_flag=True.",
    )

    @model_validator(mode="after")
    def signers_must_differ(self) -> "ControlledSubstanceCheckBase":
        """
        The dual-signature workflow requires two different people.
        Accepting identical signers would defeat the entire purpose of the
        dual-signer requirement and is a compliance failure.
        """
        if self.primary_signer.strip().lower() == self.secondary_signer.strip().lower():
            raise ValueError(
                "primary_signer and secondary_signer must be different people. "
                "The dual-signature workflow requires two witnesses."
            )
        return self


class ControlledSubstanceCheckCreate(ControlledSubstanceCheckBase):
    """Request body for POST /checks/controlled-substance."""
    pass


class ControlledSubstanceCheckRead(ControlledSubstanceCheckBase):
    """Response model for controlled substance check endpoints."""

    model_config = ConfigDict(from_attributes=True)

    cs_check_id: int
    created_at: datetime
    updated_at: datetime
