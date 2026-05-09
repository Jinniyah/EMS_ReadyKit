"""
routers/__init__.py

FastAPI route handlers for the EMS ReadyKit API.

Phase 2 will add routers for:
  - stations   — GET /stations, POST /stations, GET /stations/{id}
  - vehicles   — GET /vehicles, POST /vehicles, GET /vehicles/{id}
  - items      — GET /items, POST /items, GET /items/{id}
  - inventory  — GET /inventory/{location_id}, stock lot CRUD
  - checks     — POST /checks/daily, POST /checks/controlled-substance
  - audit      — GET /audit (read-only audit log query)

All routers will be registered in main.py under the /api/v1 prefix.
Authentication and RBAC middleware will be added in Phase 3.
"""
