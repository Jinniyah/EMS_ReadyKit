"""
models/__init__.py
Import all models here so that:
  1. Alembic's env.py can import this module and see every table.
  2. SQLAlchemy's relationship resolution works at startup.
"""

from ems_readykit.models.station import Station
from ems_readykit.models.vehicle import Vehicle, VehicleType
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.item import Item, ItemCategory, ItemCheckType
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.daily_inventory_check import DailyInventoryCheck, CheckStatus
from ems_readykit.models.check_line_item import CheckLineItem, LineItemStatus
from ems_readykit.models.controlled_substance_check import ControlledSubstanceCheck
from ems_readykit.models.audit_event import AuditEvent
from ems_readykit.models.repair_request import RepairRequest, RepairSeverity, RepairStatus

__all__ = [
    "Station",
    "Vehicle",
    "VehicleType",
    "InventoryLocation",
    "LocationType",
    "Compartment",
    "Item",
    "ItemCategory",
    "ItemCheckType",
    "StockLot",
    "ParLevel",
    "DailyInventoryCheck",
    "CheckStatus",
    "CheckLineItem",
    "LineItemStatus",
    "ControlledSubstanceCheck",
    "AuditEvent",
    "RepairRequest",
    "RepairSeverity",
    "RepairStatus",
]
