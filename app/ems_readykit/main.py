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

# Configure logging before anything else
configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


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
        version="0.1.0",
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

    # ── Routers (registered here as Phase 2 adds them) ────────────────────────
    # from ems_readykit.routers import stations, vehicles, items, inventory
    # app.include_router(stations.router, prefix="/api/v1")
    # app.include_router(vehicles.router, prefix="/api/v1")

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
