import os
import tempfile
from collections.abc import Generator
from pathlib import Path

from cryptography.fernet import Fernet

_root = Path(tempfile.mkdtemp(prefix="aegis-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_root / 'test.db').as_posix()}"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["AUTH_RATE_LIMIT_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "test"
os.environ["COOKIE_SECURE"] = "false"

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, engine, get_db
from app.main import app
from app.models import Base

get_settings.cache_clear()
PRESERVED_TABLES = {"industries", "alembic_version"}


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "head")


@pytest.fixture
def db_session(migrated_database: None) -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_db():
        try:
            yield db_session
        finally:
            pass

    from app.engine.seed import ensure_platform_content

    ensure_platform_content(db_session)
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    db_session.close()
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name not in PRESERVED_TABLES:
                connection.execute(table.delete())
