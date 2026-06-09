"""
routers/__init__.py
All Phase 2 routers are registered here and imported by main.py.

Router → prefix mapping:
  stations  → /api/v1/stations
  vehicles  → /api/v1/vehicles, /api/v1/stations/{id}/vehicles
  items     → /api/v1/items
  inventory → /api/v1/inventory
  checks    → /api/v1/checks
  audit     → /api/v1/audit

Authentication and RBAC middleware will be added in Phase 3.
"""

from ems_readykit.routers import audit, checks, inventory, items, stations, vehicles

__all__ = ["audit", "checks", "inventory", "items", "stations", "vehicles"]
