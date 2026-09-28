import os
from collections.abc import Iterator

os.environ.setdefault("MF_DATABASE_URL", "postgresql+psycopg://mf:mf@localhost:5432/mf_test")
os.environ.setdefault("MF_LOG_JSON", "false")
os.environ.setdefault("MF_SECRET_KEY", "test-secret")

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import engine, get_session
from app.main import create_app
from app.services import auth
from app.services.content import seed
from app.services.users import current_user, get_or_create_learner


@pytest.fixture(scope="session")
def connection() -> Iterator[Connection]:
    with engine.connect() as conn:
        cfg = Config("alembic.ini")
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
        conn.commit()
        yield conn


@pytest.fixture
def session(connection: Connection) -> Iterator[Session]:
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()


@pytest.fixture
def anon_client(session: Session) -> Iterator[TestClient]:
    auth._attempts.clear()
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """A client already signed in as the learner."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_user] = lambda: get_or_create_learner(session)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeded(session: Session) -> Session:
    seed(session, get_settings().content_dir)
    return session
