"""
routers/__init__.py
All routers are registered here and imported by main.py.

Router prefix mapping:
  stations       -> /api/v1/stations
  station_members-> /api/v1/stations/{id}/members
  vehicles       -> /api/v1/vehicles
  items          -> /api/v1/items
  inventory      -> /api/v1/inventory
  checks         -> /api/v1/checks
  check_history  -> /api/v1/checks/daily (history, soft-delete, restore, hard-delete)
  usage          -> /api/v1/checks/usage
  repair_requests-> /api/v1/vehicles/{id}/repair-requests
  admin_items    -> /api/v1/admin (item catalog, par levels, CSV import)
  admin_vehicles -> /api/v1/admin (vehicle color and details)
  admin_stations -> /api/v1/admin (station creation, location rename, retired list)
  audit          -> /api/v1/audit

CQ-B5: admin.py split into admin_items.py, admin_vehicles.py, admin_stations.py.
"""

from ems_readykit.routers import (
    admin_items,
    admin_stations,
    admin_vehicles,
    audit,
    check_history,
    checks,
    inventory,
    items,
    repair_requests,
    station_members,
    stations,
    usage,
    vehicles,
)

__all__ = [
    "admin_items",
    "admin_stations",
    "admin_vehicles",
    "audit",
    "check_history",
    "checks",
    "inventory",
    "items",
    "repair_requests",
    "station_members",
    "stations",
    "usage",
    "vehicles",
]
