"""
main.py
FastAPI application factory and startup lifecycle.

## Security headers (SEC-3)
Every API response carries:
  X-Content-Type-Options: nosniff      -- prevents MIME sniffing
  X-XSS-Protection: 1; mode=block     -- legacy XSS filter for older browsers
  Referrer-Policy: strict-origin-when-cross-origin

NOTE: X-Frame-Options is intentionally NOT set on the backend API.
  - The backend serves JSON, never HTML displayed in a browser frame.
  - Setting X-Frame-Options: DENY here caused MSAL's auth iframe/popup to be
    blocked when it redirected back to the SWA origin, producing:
      BrowserAuthError: hash_empty_error
    X-Frame-Options for the SWA frontend is set in staticwebapp.config.json.

## OpenAPI docs (SEC-2)
/docs, /redoc, and /openapi.json are disabled unless ENABLE_API_DOCS=true.
This is deliberately decoupled from APP_ENV/is_production -- see the
ENABLE_API_DOCS docstring in core/config.py for why (SEC-03).

## Admin routers (CQ-B5)
The monolithic admin.py was split into three sub-routers:
  admin_items.py    -- item catalog, par levels, CSV import
  admin_vehicles.py -- vehicle color and details
  admin_stations.py -- station creation, location rename, retired list
All three share the /admin prefix and admin tag.
"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from ems_readykit.core.config import get_settings
from ems_readykit.core.limiter import limiter
from ems_readykit.core.logging import configure_logging, set_request_id
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

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

API_PREFIX = "/api/v1"

_LOG_EXCLUDED_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}


def create_app() -> FastAPI:
    # -- SEC-4: Fail loud at startup if secret_key is still the default --------
    if settings.is_production:
        assert settings.secret_key != "change-me-in-production", (
            "SECRET_KEY must be set to a strong random value in production. "
            "Set the SECRET_KEY environment variable or Key Vault secret."
        )

    # -- SEC-2 / SEC-03: Disable OpenAPI docs unless explicitly enabled --------
    # Gated on ENABLE_API_DOCS, NOT settings.is_production. This deployed App
    # Service intentionally runs with APP_ENV=development for resource-naming
    # and cost purposes, so gating on is_production left /docs, /redoc, and
    # /openapi.json publicly reachable on the live UAT app. ENABLE_API_DOCS
    # defaults to False (secure by default) regardless of APP_ENV -- see the
    # docstring in core/config.py.
    _docs_url = "/docs" if settings.enable_api_docs else None
    _redoc_url = "/redoc" if settings.enable_api_docs else None
    _openapi_url = "/openapi.json" if settings.enable_api_docs else None

    app = FastAPI(
        title="EMS ReadyKit API",
        description=(
            "Vehicle readiness and inventory management platform for Fire and EMS. "
            "Non-production technical demonstration. Does not process patient data."
        ),
        version="0.2.0",
        docs_url=_docs_url,
        redoc_url=_redoc_url,
        openapi_url=_openapi_url,
    )

    # -- Rate limiter state (required by slowapi) -------------------------------
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # -- SEC-3: Security response headers (OWASP A05) --------------------------
    # X-Frame-Options is deliberately EXCLUDED -- see module docstring above.
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

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
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None,
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

    # -- API Routers -----------------------------------------------------------
    # Route ordering matters:
    #   1. station_members BEFORE stations -- /stations/my must resolve before
    #      /stations/{station_id} or FastAPI matches "my" as an integer and 422s.
    #   2. check_history BEFORE checks -- /checks/daily/my-history must resolve
    #      before /checks/daily/{check_id}.
    app.include_router(station_members.router, prefix=API_PREFIX)
    app.include_router(stations.router, prefix=API_PREFIX)
    app.include_router(vehicles.router, prefix=API_PREFIX)
    app.include_router(repair_requests.router, prefix=API_PREFIX)
    app.include_router(check_history.router, prefix=API_PREFIX)
    app.include_router(usage.router, prefix=API_PREFIX)
    app.include_router(checks.router, prefix=API_PREFIX)
    app.include_router(items.router, prefix=API_PREFIX)
    app.include_router(inventory.router, prefix=API_PREFIX)
    app.include_router(admin_items.router, prefix=API_PREFIX)
    app.include_router(admin_vehicles.router, prefix=API_PREFIX)
    app.include_router(admin_stations.router, prefix=API_PREFIX)
    app.include_router(audit.router, prefix=API_PREFIX)

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    logger.info(
        "EMS ReadyKit application created",
        extra={
            "env": settings.app_env,
            "db_is_sqlite": settings.is_sqlite,
            "auth_tenant_id": settings.azure_ad_tenant_id or "NOT SET",
            "auth_client_id": settings.azure_ad_client_id or "NOT SET",
            "auth_audience": settings.azure_ad_audience or "NOT SET",
        },
    )

    return app


app = create_app()
