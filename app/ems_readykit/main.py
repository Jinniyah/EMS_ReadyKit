"""
main.py
FastAPI application factory and startup lifecycle.

## Request logging middleware
Every HTTP request is logged with:
  method, path, status_code, duration_ms, request_id, actor (if authenticated)

This provides the operational baseline for:
  - Endpoint performance monitoring
  - 404/422/500 spike detection
  - Audit trail cross-referencing via request_id

## Log volume discipline
Request logs are INFO level. They are NOT emitted for:
  - GET /health  (excluded to avoid health-check noise)
  - Static assets (none in this API)

Third-party library logging is silenced at WARNING in core/logging.py.
"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from ems_readykit.core.config import get_settings
from ems_readykit.core.logging import configure_logging, set_request_id
from ems_readykit.routers import audit, checks, inventory, items, stations, vehicles
from ems_readykit.routers import check_history, repair_requests, station_members

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

API_PREFIX = "/api/v1"

_LOG_EXCLUDED_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}


def create_app() -> FastAPI:
    app = FastAPI(
        title="EMS ReadyKit API",
        description=(
            "Vehicle readiness and inventory management platform for Fire and EMS. "
            "Non-production technical demonstration. Does not process patient data."
        ),
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        request_id = set_request_id(request.headers.get("X-Request-ID"))
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)
        path = request.url.path
        if path not in _LOG_EXCLUDED_PATHS:
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            logger.log(
                log_level,
                "%s %s %s",
                request.method,
                path,
                response.status_code,
                extra={
                    "request_id":  request_id,
                    "method":      request.method,
                    "path":        path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip":   request.client.host if request.client else None,
                },
            )
        response.headers["X-Request-ID"] = request_id
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routers ────────────────────────────────────────────────────────────
    # Route ordering matters:
    #   1. station_members BEFORE stations — /stations/my must resolve before
    #      /stations/{station_id} or FastAPI matches "my" as an integer and 422s.
    #   2. check_history BEFORE checks — /checks/daily/my-history must resolve
    #      before /checks/daily/{check_id}.
    app.include_router(station_members.router, prefix=API_PREFIX)
    app.include_router(stations.router,        prefix=API_PREFIX)
    app.include_router(vehicles.router,        prefix=API_PREFIX)
    app.include_router(repair_requests.router, prefix=API_PREFIX)
    app.include_router(check_history.router,   prefix=API_PREFIX)
    app.include_router(checks.router,          prefix=API_PREFIX)
    app.include_router(items.router,           prefix=API_PREFIX)
    app.include_router(inventory.router,       prefix=API_PREFIX)
    app.include_router(audit.router,           prefix=API_PREFIX)

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok", "env": settings.app_env}

    logger.info(
        "EMS ReadyKit application created",
        extra={
            "env":             settings.app_env,
            "db_is_sqlite":    settings.is_sqlite,
            "auth_tenant_id":  settings.azure_ad_tenant_id or "NOT SET",
            "auth_client_id":  settings.azure_ad_client_id or "NOT SET",
            "auth_audience":   settings.azure_ad_audience  or "NOT SET",
        },
    )

    return app


app = create_app()
