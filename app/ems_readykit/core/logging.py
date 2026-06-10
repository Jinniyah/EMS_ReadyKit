"""
core/logging.py
Configures structured JSON logging for production and readable console
logging for local development.

## Two-layer logging strategy

### Layer 1 — Python structured logger (this file)
Handles: operational visibility, debugging, request tracing, security events.
In production: JSON to stdout → App Service → Log Analytics → KQL queries.
In development: human-readable console output.

### Layer 2 — AuditEvent database table (models/audit_event.py)
Handles: compliance accountability, role-gated audit queries, CSV export.
These are written explicitly at the service layer for every material action.
They are the authoritative record for "who did what and when."

## JSON log format (production)
Every log line is a JSON object with these guaranteed fields:
  timestamp   — ISO 8601 UTC (e.g. "2026-05-15T09:42:11")
  logger      — dotted module path (e.g. "ems_readykit.routers.checks")
  level       — DEBUG | INFO | WARNING | ERROR | CRITICAL
  message     — human-readable description

High-signal log lines also include structured extra fields:
  action      — audit action code (e.g. "CHECK_COMPLETED")
  entity_type — affected entity (e.g. "DailyInventoryCheck")
  entity_id   — affected record ID
  severity    — INFO | WARNING | HIGH
  actor       — authenticated user name
  vehicle_id  — vehicle context (where applicable)
  station_id  — station context (where applicable)
  request_id  — correlation ID linking all logs for one request
  duration_ms — request duration in milliseconds (on request logger)
  status_code — HTTP response code (on request logger)

## KQL query examples (Log Analytics)
All FAIL checks in last 7 days:
  AppServiceConsoleLogs
  | where TimeGenerated > ago(7d)
  | extend log = parse_json(ResultDescription)
  | where log.action == "CHECK_COMPLETED" and log.severity == "HIGH"
  | project TimeGenerated, actor=log.actor, vehicle_id=log.vehicle_id

CS discrepancy trend by week:
  AppServiceConsoleLogs
  | extend log = parse_json(ResultDescription)
  | where log.action == "CS_DISCREPANCY"
  | summarize count() by week=bin(TimeGenerated, 7d)
  | render timechart

## Silenced loggers (cost control)
The following noisy third-party loggers are set to WARNING so we don't pay
to store SQL query chatter or Azure SDK heartbeats:
  sqlalchemy.engine  — individual SQL statements (very high volume)
  azure              — Azure SDK retries and heartbeats
  urllib3            — HTTP connection pool chatter

## Retention strategy
  Runtime logs (Log Analytics):  30 days  — debugging window only
  HIGH severity events:           90 days  — investigation window
  AuditEvent DB rows:             indefinite — compliance record; tiny row count
  Monthly archive:                Blob Storage cold tier via Log Analytics export
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

from pythonjsonlogger import jsonlogger

from ems_readykit.core.config import get_settings

# ── Request correlation ID ────────────────────────────────────────────────────
# Set at the start of each request; flows through all log lines in that request.
# Allows grouping all log output for one API call in Log Analytics.
_request_id: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the current request correlation ID, or empty string if not set."""
    return _request_id.get()


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set the request correlation ID for this request context."""
    rid = request_id or str(uuid.uuid4())
    _request_id.set(rid)
    return rid


# ── Custom JSON formatter with guaranteed field names ─────────────────────────


class _EmsJsonFormatter(jsonlogger.JsonFormatter):
    """
    Extends JsonFormatter to:
    1. Rename fields to our standard schema (timestamp, logger, level).
    2. Inject the request correlation ID into every log line.
    3. Ensure extra fields from logger.info(..., extra={}) are included.
    """

    def add_fields(
        self,
        log_record: dict,
        record: logging.LogRecord,
        message_dict: dict,
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Normalise field names to our schema
        log_record["timestamp"] = log_record.pop("asctime", "")
        log_record["logger"] = log_record.pop("name", record.name)
        log_record["level"] = log_record.pop("levelname", record.levelname)

        # Inject correlation ID — always present, even if empty
        log_record["request_id"] = get_request_id()

        # Remove fields that add noise with no value in our schema
        for key in ("taskName", "thread", "process"):
            log_record.pop(key, None)


# ── Logging configuration ─────────────────────────────────────────────────────


def configure_logging() -> None:
    """
    Configure root logger. Call once at application startup (in main.py).

    Production:   structured JSON → stdout → Log Analytics
    Development:  human-readable → stdout
    """
    settings = get_settings()
    level = getattr(logging, settings.log_level, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove any handlers already attached (e.g. by uvicorn on import)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if settings.is_production:
        formatter = _EmsJsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
            rename_fields={},  # handled in add_fields
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # ── Silence high-volume third-party loggers ───────────────────────────────
    # These are set to WARNING to avoid paying Log Analytics ingestion costs
    # for SQL query text and Azure SDK heartbeats. Each SQL statement at INFO
    # would add ~10x log volume with near-zero investigative value.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
