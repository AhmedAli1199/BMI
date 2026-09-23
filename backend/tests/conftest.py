"""Shared pytest fixtures for the backend test suite.

Every test runs against a real Postgres database (TEST_DATABASE_URL,
defaulting to the local `bmi_test` db - same schema as `bmi`, migrated
independently via `alembic upgrade head` against it) rather than mocks or
SQLite: this codebase leans on real Postgres features (JSONB columns,
trigram search for dedupe) that SQLite can't stand in for, and the whole
point of testing the API layer is catching the same bugs a real request
would hit (see morning_queue.py's missing-import bug, the motivating case
for this suite existing at all).

Isolation: each test runs inside one outer transaction that is always
rolled back at teardown (the SAVEPOINT-restart trick below), so tests
never see each other's writes and never require any cleanup of their own -
create whatever rows a test needs, then just let it end.
"""
from __future__ import annotations

import os
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/bmi_test")
os.environ.setdefault("API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models import User

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

assert "test" in TEST_DATABASE_URL, (
    "Refusing to run tests against a database whose URL doesn't contain "
    "'test' - this suite creates/rolls back real rows and must never point "
    "at the real bmi database. Set TEST_DATABASE_URL (or DATABASE_URL) to "
    "a dedicated test database."
)

_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)


@pytest.fixture()
def db_session():
    """One Postgres connection + outer transaction per test, with the
    SAVEPOINT-restart trick so code under test (which calls session.commit()
    freely, same as any request handler) never actually commits past this
    test's own rollback."""
    connection = _engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """A TestClient whose every request runs against db_session's
    transaction - every write a test's HTTP calls make is visible to
    later calls in the same test, and is rolled back at teardown."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        c.headers.update({"X-API-Key": settings.api_key})
        yield c
    app.dependency_overrides.pop(get_db, None)


def make_user(db_session, *, role: str = "sales", email: str | None = None, name: str = "Test User") -> User:
    user = User(
        id=uuid.uuid4(),
        email=email or f"{uuid.uuid4().hex[:10]}@example.com",
        name=name,
        hashed_password=hash_password("correct-horse-battery-staple"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def identity_headers(user: User, *, access: list[tuple[str, str | None]] | None = None) -> dict[str, str]:
    """X-BMI-User-* headers matching what backend.ts forwards for a real
    logged-in session - see app/core/identity.py's trust model."""
    import json

    return {
        "X-BMI-User-Id": str(user.id),
        "X-BMI-User-Role": user.role,
        "X-BMI-User-Access": json.dumps(
            [{"source_db": db, "group_id": gid} for db, gid in (access or [])]
        ),
    }
