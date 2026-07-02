"""
tests/conftest.py
Shared pytest fixtures.
Uses an in-memory SQLite database so tests have zero external dependencies.

Transaction isolation pattern:
    A single connection is opened per test. The outer transaction is begun
    before the session is created. join_transaction_mode="create_savepoint"
    instructs SQLAlchemy to use SAVEPOINT for nested transactions so that
    IntegrityError tests can roll back to the savepoint without poisoning
    the outer connection transaction. The outer transaction is rolled back
    after each test, leaving the schema intact for the next test.

Auth fixtures:
    Three header fixtures are provided for RBAC testing:
        auth_admin       — Bearer test-administrator (all access)
        auth_supervisor  — Bearer test-supervisor
        auth_responder   — Bearer test-responder
    Pass as headers= to client.get/post/put/delete calls.
    Most existing tests use auth_admin to avoid permission failures.
    RBAC-specific tests use the appropriate role to verify enforcement.

    These fake tokens only work because REQUIRE_REAL_AUTH is explicitly set
    to "false" below, before ems_readykit.main is imported. Settings.
    require_real_auth defaults to True everywhere else (including the
    deployed App Service) — see core/config.py and core/auth.py.
"""

from __future__ import annotations

import os

# Must be set BEFORE importing ems_readykit.main:
#   TESTING           — the rate limiter singleton reads this at module load
#                        time and configures a very high limit for tests.
#   REQUIRE_REAL_AUTH — Settings.require_real_auth defaults to True (secure
#                        by default); the test suite explicitly opts out so
#                        the fake test-{role} bearer tokens above work.
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("REQUIRE_REAL_AUTH", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import ems_readykit.models  # noqa: F401 — ensure all tables are registered
from ems_readykit.core.database import Base, get_db
from ems_readykit.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """
    Session-scoped engine with FK enforcement enabled.
    Schema is created once and torn down after all tests complete.
    """
    eng = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

    # Enable FK enforcement for SQLite (off by default)
    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="function")
def db(engine):
    """
    Provide a transaction-scoped session that rolls back after each test.

    join_transaction_mode="create_savepoint" ensures that when a test
    triggers an IntegrityError (and SQLAlchemy rolls back to the savepoint),
    the outer connection transaction remains usable. Without this, any flush
    that raises an IntegrityError would poison the entire connection for the
    remainder of the test.
    """
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionFactory = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )
    session = TestingSessionFactory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """FastAPI test client with DB dependency overridden to use the test session."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Auth header fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def auth_admin():
    """Authorization headers for an Administrator — full access to all endpoints."""
    return {"Authorization": "Bearer test-administrator"}


@pytest.fixture
def auth_supervisor():
    """Authorization headers for a Supervisor — station-level management access."""
    return {"Authorization": "Bearer test-supervisor"}


@pytest.fixture
def auth_responder():
    """Authorization headers for a Responder — submit checks and read own vehicle."""
    return {"Authorization": "Bearer test-responder"}


# ── Seeded dev DB fixture ───────────────────────────────────────────────────────────────────

# Path to the seeded dev database. Resolved relative to the app/ directory.
_DEV_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "ems_readykit_dev.db")
_DEV_DB_URL = f"sqlite:///{os.path.abspath(_DEV_DB_PATH)}"


@pytest.fixture(scope="session")
def seeded_engine():
    """
    Session-scoped engine connected to the seeded dev database (ems_readykit_dev.db).
    Used exclusively by test_seed_integrity.py to verify that seed.py produced
    the correct operational data. Read-only by convention — tests must not write.

    If the dev DB does not exist, all seed integrity tests are skipped with a
    clear message rather than failing with a cryptic SQLAlchemy error.
    """
    dev_db = os.path.abspath(_DEV_DB_PATH)
    if not os.path.exists(dev_db):
        pytest.skip(
            f"Dev database not found at {dev_db}. "
            "Run: cd app && alembic upgrade head && python seed.py",
            allow_module_level=True,
        )
    eng = create_engine(
        _DEV_DB_URL,
        connect_args={"check_same_thread": False},
    )
    yield eng
    eng.dispose()


@pytest.fixture(scope="function")
def seeded_db(seeded_engine):
    """
    Read-only session against the seeded dev database.
    No transaction rollback — tests must only query, never write.
    """
    SessionFactory = sessionmaker(bind=seeded_engine, autocommit=False, autoflush=False)
    session = SessionFactory()
    yield session
    session.close()
