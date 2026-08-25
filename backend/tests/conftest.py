import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cloudhide.db")
os.environ.setdefault("STORAGE_ROOT", str(BACKEND_DIR.parent / "storage"))
os.environ.setdefault("MASTER_KEY_BASE64", "BDg5A3MHzndhtHeMFr5l2viRRkuLc6gafv/KvmuR2YI=")

# Start each test run from a clean database so state doesn't accumulate.
_test_db_path = BACKEND_DIR / "test_cloudhide.db"
if _test_db_path.exists():
    _test_db_path.unlink()

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, init_db
from app.main import app

init_db()


@pytest.fixture(autouse=True)
def _reset_database():
    """Every test starts against empty tables, regardless of which fixture it uses.

    Tests run against a single persistent SQLite file (not per-test in-memory
    DBs) because both the `client` fixture (via the app's engine) and the
    `db_session` fixture must see the same data. Without this, carriers/
    transfers/etc. created in one test leak into the next.
    """
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
