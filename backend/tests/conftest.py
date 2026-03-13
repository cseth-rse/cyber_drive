# tests/conftest.py
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use SQLite in-memory for tests (no Postgres needed)
TEST_DATABASE_URL = "sqlite:///:memory:"

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET", "test-secret-key-at-least-16-chars")
os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh-secret-key-16-chars")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_USER", "test")
os.environ.setdefault("EMAIL_PASS", "test")
os.environ.setdefault("UPLOAD_DIR", "/tmp/cyber_drive_test_uploads")

from app.database import Base
from app.config import get_settings

get_settings.cache_clear()


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def settings():
    get_settings.cache_clear()
    return get_settings()
