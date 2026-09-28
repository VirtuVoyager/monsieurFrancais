import os
from collections.abc import Iterator

os.environ.setdefault("MF_DATABASE_URL", "postgresql+psycopg://mf:mf@localhost:5432/mf_test")
os.environ.setdefault("MF_LOG_JSON", "false")

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from app.db import engine, get_session
from app.main import create_app


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
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
