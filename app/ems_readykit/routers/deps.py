"""
routers/deps.py
Shared FastAPI dependencies used across all routers.

Centralizing dependencies here means:
  - A single import point for all routers
  - Easy to extend in Phase 3 (e.g. add current_user dependency for RBAC)
  - No circular imports between routers and core modules

Phase 3 will add:
  - get_current_user — JWT validation via Azure AD
  - require_role(role) — RBAC enforcement
  - get_station_for_user — scope filtering by user's assigned station
"""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db

# Re-export get_db so routers only need to import from deps
__all__ = ["get_db"]
