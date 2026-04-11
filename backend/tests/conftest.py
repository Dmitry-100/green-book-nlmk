import pytest
import redis
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app

base_db_url = make_url(settings.database_url)
if not base_db_url.database:
    raise RuntimeError("DATABASE_URL must include a database name")

if base_db_url.database.endswith("_test"):
    TEST_DATABASE_NAME = base_db_url.database
else:
    TEST_DATABASE_NAME = f"{base_db_url.database}_test"

TEST_DATABASE_URL = base_db_url.set(database=TEST_DATABASE_NAME)
ADMIN_DATABASE_URL = base_db_url.set(database="postgres")

engine = create_engine(TEST_DATABASE_URL)
TestSession = sessionmaker(bind=engine)


def clear_rate_limit_keys() -> None:
    try:
        client = redis.from_url(settings.redis_url)
        keys = list(client.scan_iter(match="ratelimit:*", count=200))
        if keys:
            client.delete(*keys)
    except Exception:
        # Tests should still run when Redis is unavailable.
        return


def ensure_test_db_exists():
    admin_engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": TEST_DATABASE_NAME},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    ensure_test_db_exists()
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSession()
    try:
        clear_rate_limit_keys()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_token(
    external_id: str = "test-user-001",
    name: str = "Test User",
    email: str = "test@nlmk.com",
    role: str = "employee",
) -> str:
    payload = {"sub": external_id, "name": name, "email": email, "role": role}
    return jwt.encode(
        payload, settings.auth_secret_key, algorithm=settings.auth_algorithm
    )


@pytest.fixture
def employee_token():
    return make_token()


@pytest.fixture
def ecologist_token():
    return make_token(
        external_id="eco-001",
        name="Ecologist",
        email="eco@nlmk.com",
        role="ecologist",
    )


@pytest.fixture
def admin_token():
    return make_token(
        external_id="admin-001",
        name="Admin",
        email="admin@nlmk.com",
        role="admin",
    )
