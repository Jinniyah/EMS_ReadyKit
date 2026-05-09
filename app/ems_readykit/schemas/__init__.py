"""
schemas/__init__.py

Pydantic request/response models for the EMS ReadyKit API.

Phase 2 will add schemas for:
  - Station (StationCreate, StationRead)
  - Vehicle (VehicleCreate, VehicleRead)
  - InventoryLocation (LocationRead)
  - Item (ItemCreate, ItemRead)
  - StockLot (StockLotCreate, StockLotRead)
  - ParLevel (ParLevelCreate, ParLevelRead)
  - DailyInventoryCheck (CheckCreate, CheckRead)
  - ControlledSubstanceCheck (CSCheckCreate, CSCheckRead)
  - AuditEvent (AuditEventRead — read-only, no Create schema exposed via API)

All schemas use Pydantic v2 model_config with from_attributes=True
to support ORM-to-schema serialization via FastAPI's response_model.
"""
