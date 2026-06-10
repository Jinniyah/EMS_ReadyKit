"""
schemas/repair_request.py
Pydantic schemas for RepairRequest endpoints.

RepairRequestCreate  — body for POST /vehicles/{id}/repair-requests (all roles)
RepairRequestUpdate  — body for PATCH /vehicles/{id}/repair-requests/{rid} (Supervisor+)
RepairRequestOut     — response model for all repair request endpoints
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ems_readykit.models.repair_request import RepairSeverity, RepairStatus


class RepairRequestCreate(BaseModel):
    """Filed by any authenticated role against a vehicle."""

    severity: RepairSeverity = Field(
        default=RepairSeverity.ROUTINE,
        description="ROUTINE — schedule at next opportunity; URGENT — safety-affecting, take out of service",
    )
    description: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Description of the issue",
    )


class RepairRequestUpdate(BaseModel):
    """Status update filed by Supervisor+ — advances the repair lifecycle."""

    status: RepairStatus = Field(..., description="New status: IN_PROGRESS or RESOLVED")
    resolution_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Required when status is RESOLVED",
    )


class RepairRequestOut(BaseModel):
    """Full repair request — returned by all read and write endpoints."""

    model_config = ConfigDict(from_attributes=True)

    repair_id: int
    vehicle_id: int
    station_id: int
    reported_by: str
    reported_at: datetime
    severity: RepairSeverity
    description: str
    status: RepairStatus
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
