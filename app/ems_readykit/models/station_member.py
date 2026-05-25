"""
models/station_member.py
StationMember — many-to-many join between stations and users.

A user (identified by their Azure AD preferred_username / email) can be
assigned to multiple stations. The role stored here mirrors their Azure AD
role for that station context.

preferred_name is optional display text set by the admin — replaces the raw
UPN in the UI (e.g. "Cindy Smith" instead of the EXT UPN form).

Design decisions (see B-ACCESS1):
  - user_id is the Azure AD preferred_username (email). Stable, unique,
    and present in every JWT — no MS Graph call needed to assign users.
  - active flag allows soft-removal without losing assignment history.
  - assigned_by records the UPN of whoever created the assignment (audit trail).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.station import Station


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StationMember(TimestampMixin, Base):
    __tablename__ = "station_members"

    # One row per user per station. Soft-deleted rows kept for audit history.
    __table_args__ = (
        UniqueConstraint(
            "station_id", "user_id",
            name="uq_station_members_station_user",
        ),
    )

    member_id:      Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    station_id:     Mapped[int]           = mapped_column(ForeignKey("stations.station_id"), nullable=False, index=True)
    user_id:        Mapped[str]           = mapped_column(String(255), nullable=False, index=True)
    preferred_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    role:           Mapped[str]           = mapped_column(String(50),  nullable=False)
    assigned_by:    Mapped[str]           = mapped_column(String(255), nullable=False)
    assigned_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    active:         Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    station: Mapped["Station"] = relationship("Station", back_populates="members")

    def __repr__(self) -> str:
        return (
            f"<StationMember id={self.member_id} "
            f"station_id={self.station_id} "
            f"user_id={self.user_id!r} "
            f"role={self.role!r} "
            f"active={self.active}>"
        )
