import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.user import UserRole

# Use a separate test database (same server, different DB name)
TEST_DATABASE_URL = settings.database_url.replace("/greenbook", "/greenbook_test")

engine = create_engine(TEST_DATABASE_URL)
TestSession = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSession()
    try:
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
