"""
main.py
FastAPI application factory and startup lifecycle.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ems_readykit.core.config import get_settings
from ems_readykit.core.logging import configure_logging
from ems_readykit.routers import audit, checks, inventory, items, stations, vehicles

# Configure logging before anything else
configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler (replaces deprecated on_event hooks)."""
    logger.info(
        "EMS ReadyKit starting up",
        extra={"env": settings.app_env, "db_is_sqlite": settings.is_sqlite},
    )
    yield
    logger.info("EMS ReadyKit shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="EMS ReadyKit API",
        description=(
            "Vehicle readiness and inventory management platform for Fire & EMS. "
            "Non-production technical demonstration."
        ),
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routers ────────────────────────────────────────────────────────────
    # All routes are versioned under /api/v1 for forward compatibility.
    # Phase 3 will add authentication middleware before these registrations.
    app.include_router(stations.router, prefix=API_PREFIX)
    app.include_router(vehicles.router, prefix=API_PREFIX)
    app.include_router(items.router, prefix=API_PREFIX)
    app.include_router(inventory.router, prefix=API_PREFIX)
    app.include_router(checks.router, prefix=API_PREFIX)
    app.include_router(audit.router, prefix=API_PREFIX)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
