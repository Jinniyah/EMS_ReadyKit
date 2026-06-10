"""
schemas/station_member.py
Pydantic schemas for StationMember request validation and response serialization.

Roles accepted:
    Administrator — assigned by Admin only
    Supervisor    — assigned by Admin or Supervisor
    Responder     — assigned by Admin or Supervisor

user_id is the Azure AD preferred_username (email). For guest users this is
their clean email (e.g. jinniyah@gmail.com), not the EXT UPN form — the JWT
preferred_username claim is used directly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

VALID_ROLES = {"Administrator", "Supervisor", "Responder"}


def _to_utc_str(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class StationMemberCreate(BaseModel):
    """Body for POST /stations/{id}/members"""

    user_id: str = Field(..., description="Azure AD preferred_username (email)")
    preferred_name: Optional[str] = Field(
        None, max_length=100, description="Display name shown in the UI"
    )
    role: str = Field(..., description="Administrator | Supervisor | Responder")

    model_config = ConfigDict(str_strip_whitespace=True)

    @property
    def role_is_valid(self) -> bool:
        return self.role in VALID_ROLES


class StationMemberUpdate(BaseModel):
    """Body for PATCH /stations/{id}/members/{user_id}"""

    preferred_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(
        None, description="Administrator | Supervisor | Responder"
    )
    active: Optional[bool] = None

    model_config = ConfigDict(str_strip_whitespace=True)


class StationMemberRead(BaseModel):
    """Response model"""

    model_config = ConfigDict(from_attributes=True)

    member_id: int
    station_id: int
    user_id: str
    preferred_name: Optional[str]
    role: str
    assigned_by: str
    assigned_at: datetime
    active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("assigned_at", "created_at", "updated_at")
    def serialize_utc(self, dt: Optional[datetime]) -> Optional[str]:
        return _to_utc_str(dt)
