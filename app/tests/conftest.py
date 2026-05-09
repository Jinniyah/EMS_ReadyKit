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
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from ems_readykit.core.database import Base, get_db
from ems_readykit.main import app
import ems_readykit.models  # noqa: F401 — ensure all tables are registered


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
