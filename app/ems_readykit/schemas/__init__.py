"""
schemas/__init__.py
Exports all Pydantic request/response schemas for the EMS ReadyKit API.

Schema naming convention:
  {Entity}Base   — shared fields used by both create and read
  {Entity}Create — POST request body (no DB-generated fields)
  {Entity}Read   — response model (includes DB-generated fields)

AuditEvent is read-only — no Create schema is exposed via the API.
InventoryLocation is system-managed — only a Read schema exists in Phase 2.
"""

from ems_readykit.schemas.station import StationBase, StationCreate, StationRead
from ems_readykit.schemas.vehicle import VehicleBase, VehicleCreate, VehicleRead
from ems_readykit.schemas.inventory_location import InventoryLocationRead
from ems_readykit.schemas.item import ItemBase, ItemCreate, ItemRead
from ems_readykit.schemas.stock_lot import StockLotBase, StockLotCreate, StockLotRead
from ems_readykit.schemas.par_level import ParLevelBase, ParLevelCreate, ParLevelRead
from ems_readykit.schemas.daily_inventory_check import (
    DailyInventoryCheckBase,
    DailyInventoryCheckCreate,
    DailyInventoryCheckRead,
)
from ems_readykit.schemas.controlled_substance_check import (
    ControlledSubstanceCheckBase,
    ControlledSubstanceCheckCreate,
    ControlledSubstanceCheckRead,
)
from ems_readykit.schemas.audit_event import AuditEventRead

__all__ = [
    # Station
    "StationBase", "StationCreate", "StationRead",
    # Vehicle
    "VehicleBase", "VehicleCreate", "VehicleRead",
    # Inventory Location (read-only)
    "InventoryLocationRead",
    # Item
    "ItemBase", "ItemCreate", "ItemRead",
    # Stock Lot
    "StockLotBase", "StockLotCreate", "StockLotRead",
    # Par Level
    "ParLevelBase", "ParLevelCreate", "ParLevelRead",
    # Daily Inventory Check
    "DailyInventoryCheckBase", "DailyInventoryCheckCreate", "DailyInventoryCheckRead",
    # Controlled Substance Check
    "ControlledSubstanceCheckBase", "ControlledSubstanceCheckCreate", "ControlledSubstanceCheckRead",
    # Audit Event (read-only)
    "AuditEventRead",
]
