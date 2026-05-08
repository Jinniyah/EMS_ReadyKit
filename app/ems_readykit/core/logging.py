"""
core/logging.py
Configures structured JSON logging for production and readable console
logging for local development. All audit events are emitted through the
standard Python logger so they flow to Log Analytics via the App Service
diagnostic settings wired up in Terraform.
"""

from __future__ import annotations

import logging
import sys

from pythonjsonlogger import jsonlogger

from ems_readykit.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove any handlers already attached (e.g. by uvicorn)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if settings.is_production:
        # Structured JSON — parsed by Log Analytics
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        # Human-readable for local development
        formatter = logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_audit_logger() -> logging.Logger:
    """Return the dedicated audit event logger."""
    return logging.getLogger("ems_readykit.audit")
