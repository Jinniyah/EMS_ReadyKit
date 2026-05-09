"""
core/database.py
SQLAlchemy engine and session factory.

SQLite is used for local development (no driver dependencies).
PostgreSQL (via psycopg2) is used in production — the connection string
is injected from Key Vault at startup via resolve_database_url().

The same ORM models work against both backends because we avoid
dialect-specific column types in the model definitions. All enum columns
use native_enum=False (VARCHAR storage) so no PostgreSQL CREATE TYPE
statements are needed.

Note on onupdate:
    TimestampMixin.updated_at uses SQLAlchemy's onupdate hook, which fires
    only when the ORM flushes individual UPDATE statements.  Bulk updates
    executed via session.execute(update(...)) will NOT trigger the hook and
    must set updated_at explicitly if timestamp freshness matters.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ems_readykit.core.config import get_settings, resolve_database_url


def _build_engine():
    settings = get_settings()
    db_url = resolve_database_url(settings)

    connect_args = {}
    if settings.is_sqlite:
        # SQLite requires check_same_thread=False when used with FastAPI
        connect_args["check_same_thread"] = False

    # pool_size and max_overflow are not valid for SQLite's StaticPool and
    # will raise a TypeError at startup.  Only pass them for real DBAPI-backed
    # engines (PostgreSQL, etc.).
    engine_kwargs: dict = dict(
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=not settings.is_production,   # SQL query logging in dev only
    )
    if not settings.is_sqlite:
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10

    engine = create_engine(db_url, **engine_kwargs)

    if settings.is_sqlite:
        # Enable foreign key enforcement in SQLite (off by default)
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────

def get_db():
    """
    Yield a database session per request and ensure it is closed afterward.
    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
