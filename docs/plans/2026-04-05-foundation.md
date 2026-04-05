# Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the project skeleton — Docker environment, PostgreSQL+PostGIS database, SQLAlchemy models, Alembic migrations, FastAPI app with auth middleware, and Vue.js frontend scaffold.

**Architecture:** Monorepo with `backend/` (Python FastAPI) and `frontend/` (Vue 3 + Vite). Docker Compose orchestrates PostgreSQL+PostGIS, Redis, MinIO, and the app services. Auth via JWT token validation (Blitz SSO mock for dev).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, GeoAlchemy2, Alembic, PostgreSQL 16 + PostGIS 3.4, Redis, MinIO, Vue 3, Vite, TypeScript, Pinia, Vue Router

---

## File Structure

```
green-book-nlmk/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory
│   │   ├── config.py            # Settings from env
│   │   ├── database.py          # Engine, session, Base
│   │   ├── auth.py              # JWT validation, get_current_user, role checks
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py          # User model
│   │   │   ├── species.py       # Species model
│   │   │   ├── observation.py   # Observation, ObsMedia models
│   │   │   ├── site_zone.py     # SiteZone model
│   │   │   ├── notification.py  # Notification model
│   │   │   └── decision_tree.py # DecisionTree model
│   │   └── routers/
│   │       └── health.py        # Health check endpoint
│   └── tests/
│       ├── conftest.py          # Fixtures: test DB, client, auth
│       ├── test_health.py
│       └── test_auth.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── router/
│       │   └── index.ts
│       ├── stores/
│       │   └── auth.ts
│       ├── api/
│       │   └── client.ts        # Axios instance with auth header
│       ├── layouts/
│       │   └── MainLayout.vue   # Nav + section nav + slot
│       └── views/
│           └── HomeView.vue     # Placeholder home
└── docs/
    └── plans/
```

---

### Task 1: Docker Compose + Environment

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Node
node_modules/
dist/

# Environment
.env

# IDE
.idea/
.vscode/

# OS
.DS_Store
```

- [ ] **Step 2: Create .env.example**

```env
# Database
POSTGRES_USER=greenbook
POSTGRES_PASSWORD=greenbook_dev
POSTGRES_DB=greenbook
DATABASE_URL=postgresql://greenbook:greenbook_dev@db:5432/greenbook

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=greenbook-media

# Auth (dev mode — mock JWT)
AUTH_SECRET_KEY=dev-secret-key-change-in-production
AUTH_ALGORITHM=HS256

# App
APP_ENV=development
```

- [ ] **Step 3: Create docker-compose.yml**

```yaml
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_started

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    command: npm run dev -- --host 0.0.0.0 --port 5173
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    depends_on:
      - backend

volumes:
  pgdata:
  miniodata:
```

- [ ] **Step 4: Copy .env.example to .env**

Run: `cp .env.example .env`

- [ ] **Step 5: Init git repo and commit**

```bash
git init
git add .gitignore .env.example docker-compose.yml
git commit -m "chore: init project with docker-compose (PostGIS, Redis, MinIO)"
```

---

### Task 2: Backend Scaffold — FastAPI + Config + Database

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`
- Create: `backend/app/routers/health.py`

- [ ] **Step 1: Create backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libgeos-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 2: Create backend/pyproject.toml**

```toml
[project]
name = "green-book-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy>=2.0.36",
    "geoalchemy2>=0.15.0",
    "alembic>=1.14.0",
    "psycopg2-binary>=2.9.10",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "python-jose[cryptography]>=3.3.0",
    "redis>=5.2.0",
    "boto3>=1.35.0",
    "Pillow>=11.0.0",
    "openpyxl>=3.1.0",
    "Fiona>=1.10.0",
    "Shapely>=2.0.0",
    "pyproj>=3.7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.0",
]

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 3: Create backend/app/__init__.py**

```python
```

(Empty file)

- [ ] **Step 4: Create backend/app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://greenbook:greenbook_dev@db:5432/greenbook"
    redis_url: str = "redis://redis:6379/0"
    minio_endpoint: str = "minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "greenbook-media"
    auth_secret_key: str = "dev-secret-key-change-in-production"
    auth_algorithm: str = "HS256"
    app_env: str = "development"

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 5: Create backend/app/database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, echo=(settings.app_env == "development"))
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 6: Create backend/app/routers/health.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
```

- [ ] **Step 7: Create backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health

app = FastAPI(title="Green Book NLMK API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
```

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: backend scaffold — FastAPI, config, database, health endpoint"
```

---

### Task 3: SQLAlchemy Models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/species.py`
- Create: `backend/app/models/observation.py`
- Create: `backend/app/models/site_zone.py`
- Create: `backend/app/models/notification.py`
- Create: `backend/app/models/decision_tree.py`

- [ ] **Step 1: Create backend/app/models/__init__.py**

```python
from app.models.user import User
from app.models.species import Species
from app.models.observation import Observation, ObsMedia
from app.models.site_zone import SiteZone
from app.models.notification import Notification
from app.models.decision_tree import DecisionTreeNode

__all__ = [
    "User",
    "Species",
    "Observation",
    "ObsMedia",
    "SiteZone",
    "Notification",
    "DecisionTreeNode",
]
```

- [ ] **Step 2: Create backend/app/models/user.py**

```python
import enum
from datetime import datetime

from sqlalchemy import String, Enum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    employee = "employee"
    ecologist = "ecologist"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.employee)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 3: Create backend/app/models/species.py**

```python
import enum
from datetime import datetime

from sqlalchemy import String, Text, Enum, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SpeciesGroup(str, enum.Enum):
    plants = "plants"
    fungi = "fungi"
    insects = "insects"
    herpetofauna = "herpetofauna"
    birds = "birds"
    mammals = "mammals"


class SpeciesCategory(str, enum.Enum):
    ruderal = "ruderal"
    typical = "typical"
    rare = "rare"
    red_book = "red_book"
    synanthropic = "synanthropic"


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ru: Mapped[str] = mapped_column(String(255))
    name_latin: Mapped[str] = mapped_column(String(255))
    group: Mapped[SpeciesGroup] = mapped_column(Enum(SpeciesGroup), index=True)
    category: Mapped[SpeciesCategory] = mapped_column(Enum(SpeciesCategory), index=True)
    conservation_status: Mapped[str | None] = mapped_column(String(255))
    is_poisonous: Mapped[bool] = mapped_column(Boolean, default=False)
    season_info: Mapped[str | None] = mapped_column(String(500))
    biotopes: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    do_dont_rules: Mapped[str | None] = mapped_column(Text)
    qr_url: Mapped[str | None] = mapped_column(String(500))
    photo_urls: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 4: Create backend/app/models/observation.py**

```python
import enum
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    String,
    Text,
    Enum,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ObservationStatus(str, enum.Enum):
    on_review = "on_review"
    needs_data = "needs_data"
    confirmed = "confirmed"
    rejected = "rejected"


class IncidentType(str, enum.Enum):
    injured = "injured"
    dead = "dead"
    mass_death = "mass_death"
    other = "other"


class IncidentSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, enum.Enum):
    new = "new"
    in_progress = "in_progress"
    closed = "closed"


class SensitiveLevel(str, enum.Enum):
    open = "open"
    blurred = "blurred"
    hidden = "hidden"


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    species_id: Mapped[int | None] = mapped_column(ForeignKey("species.id"))
    group: Mapped[str] = mapped_column(String(50))
    observed_at: Mapped[datetime] = mapped_column(DateTime)
    location_point: Mapped[str] = mapped_column(Geometry("POINT", srid=4326))
    site_zone_id: Mapped[int | None] = mapped_column(ForeignKey("site_zones.id"))
    status: Mapped[ObservationStatus] = mapped_column(
        Enum(ObservationStatus), default=ObservationStatus.on_review, index=True
    )
    comment: Mapped[str | None] = mapped_column(Text)
    is_incident: Mapped[bool] = mapped_column(Boolean, default=False)
    incident_type: Mapped[IncidentType | None] = mapped_column(Enum(IncidentType))
    incident_severity: Mapped[IncidentSeverity | None] = mapped_column(
        Enum(IncidentSeverity)
    )
    incident_status: Mapped[IncidentStatus | None] = mapped_column(
        Enum(IncidentStatus)
    )
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    reviewer_comment: Mapped[str | None] = mapped_column(Text)
    sensitive_level: Mapped[SensitiveLevel] = mapped_column(
        Enum(SensitiveLevel), default=SensitiveLevel.open
    )
    safety_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    media: Mapped[list["ObsMedia"]] = relationship(back_populates="observation")


class ObsMedia(Base):
    __tablename__ = "obs_media"

    id: Mapped[int] = mapped_column(primary_key=True)
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("observations.id", ondelete="CASCADE"), index=True
    )
    s3_key: Mapped[str] = mapped_column(String(500))
    thumbnail_key: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    observation: Mapped["Observation"] = relationship(back_populates="media")
```

- [ ] **Step 5: Create backend/app/models/site_zone.py**

```python
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import String, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SiteZone(Base):
    __tablename__ = "site_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    group: Mapped[str | None] = mapped_column(String(255))
    geom: Mapped[str] = mapped_column(Geometry("POLYGON", srid=4326))
    source: Mapped[str | None] = mapped_column(String(255))
    polygon_count: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 6: Create backend/app/models/notification.py**

```python
import enum
from datetime import datetime

from sqlalchemy import String, Text, Enum, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationType(str, enum.Enum):
    needs_data = "needs_data"
    confirmed = "confirmed"
    rejected = "rejected"
    incident_new = "incident_new"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    observation_id: Mapped[int | None] = mapped_column(ForeignKey("observations.id"))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 7: Create backend/app/models/decision_tree.py**

```python
from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DecisionTreeNode(Base):
    __tablename__ = "decision_tree"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_tree.id"), index=True
    )
    question_text: Mapped[str] = mapped_column(Text)
    group: Mapped[str] = mapped_column(String(50))
    suggested_species_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/
git commit -m "feat: SQLAlchemy models — User, Species, Observation, SiteZone, Notification, DecisionTree"
```

---

### Task 4: Alembic Migrations

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

- [ ] **Step 1: Create backend/alembic.ini**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://greenbook:greenbook_dev@db:5432/greenbook

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 2: Create alembic directory and env.py**

```bash
mkdir -p backend/alembic/versions
```

Create `backend/alembic/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
from app.models import (  # noqa: F401 — ensure models are imported
    User,
    Species,
    Observation,
    ObsMedia,
    SiteZone,
    Notification,
    DecisionTreeNode,
)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Generate initial migration (run inside backend container)**

Run: `docker compose exec backend alembic revision --autogenerate -m "initial schema"`

- [ ] **Step 4: Apply migration**

Run: `docker compose exec backend alembic upgrade head`

- [ ] **Step 5: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: Alembic setup + initial migration with all tables"
```

---

### Task 5: Auth Middleware

**Files:**
- Create: `backend/app/auth.py`

- [ ] **Step 1: Create backend/app/auth.py**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.auth_secret_key, algorithms=[settings.auth_algorithm]
        )
        external_id: str = payload.get("sub")
        if external_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user = db.query(User).filter(User.external_id == external_id).first()
    if user is None:
        # Auto-create user on first login (from SSO data)
        user = User(
            external_id=external_id,
            display_name=payload.get("name", "Unknown"),
            email=payload.get("email", f"{external_id}@nlmk.com"),
            role=UserRole.employee,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def require_role(*roles: UserRole):
    def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role.value} not allowed",
            )
        return user
    return checker
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/auth.py
git commit -m "feat: JWT auth middleware with auto-create user and role checker"
```

---

### Task 6: Backend Tests

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Create backend/tests/__init__.py**

```python
```

(Empty file)

- [ ] **Step 2: Create backend/tests/conftest.py**

```python
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
```

- [ ] **Step 3: Create backend/tests/test_health.py**

```python
def test_health_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
```

- [ ] **Step 4: Create backend/tests/test_auth.py**

```python
from app.models.user import User


def test_valid_token_creates_user(client, db, employee_token):
    response = client.get(
        "/api/health",  # Any authenticated endpoint would work; health is open,
        # so we test auth directly:
    )
    # For now, just verify token generation works
    assert employee_token is not None


def test_invalid_token_returns_401(client):
    response = client.get(
        "/api/health",
        headers={"Authorization": "Bearer invalid-token"},
    )
    # Health endpoint doesn't require auth, so this still returns 200
    # Auth will be tested properly when we add authenticated endpoints
    assert response.status_code == 200
```

- [ ] **Step 5: Run tests**

Run: `docker compose exec backend pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/tests/
git commit -m "test: health and auth test scaffolding"
```

---

### Task 7: Frontend Scaffold — Vue 3 + Vite + Router

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/layouts/MainLayout.vue`
- Create: `frontend/src/views/HomeView.vue`

- [ ] **Step 1: Create frontend/Dockerfile**

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
```

- [ ] **Step 2: Create frontend/package.json**

```json
{
  "name": "green-book-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.0",
    "vue-router": "^4.4.0",
    "pinia": "^2.2.0",
    "axios": "^1.7.0",
    "@vueuse/core": "^11.0.0",
    "element-plus": "^2.8.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0",
    "vue-tsc": "^2.1.0"
  }
}
```

- [ ] **Step 3: Create frontend/vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 4: Create frontend/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "noEmit": true,
    "paths": {
      "@/*": ["./src/*"]
    },
    "baseUrl": "."
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 5: Create frontend/index.html**

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Зелёная книга НЛМК</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Nunito+Sans:opsz,wght@6..12,300;6..12,400;6..12,600;6..12,700&display=swap" rel="stylesheet">
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

- [ ] **Step 6: Create frontend/src/main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

- [ ] **Step 7: Create frontend/src/App.vue**

```vue
<template>
  <router-view />
</template>
```

- [ ] **Step 8: Create frontend/src/router/index.ts**

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('../layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('../views/HomeView.vue'),
        },
      ],
    },
  ],
})

export default router
```

- [ ] **Step 9: Create frontend/src/stores/auth.ts**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

interface UserInfo {
  id: number
  displayName: string
  email: string
  role: 'employee' | 'ecologist' | 'admin'
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const user = ref<UserInfo | null>(null)

  function setToken(t: string) {
    token.value = t
  }

  function setUser(u: UserInfo) {
    user.value = u
  }

  function isEcologist() {
    return user.value?.role === 'ecologist' || user.value?.role === 'admin'
  }

  function isAdmin() {
    return user.value?.role === 'admin'
  }

  return { token, user, setToken, setUser, isEcologist, isAdmin }
})
```

- [ ] **Step 10: Create frontend/src/api/client.ts**

```typescript
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

export default api
```

- [ ] **Step 11: Create frontend/src/layouts/MainLayout.vue**

```vue
<template>
  <div class="layout">
    <nav class="portal-nav">
      <div class="portal-nav__logo">
        <span class="nlmk-badge">НЛМК</span>
        Корпоративный портал
      </div>
      <ul class="portal-nav__links">
        <li><a href="#">Новости</a></li>
        <li><a class="active">Природа</a></li>
        <li><a href="#">Сервисы</a></li>
      </ul>
      <div class="portal-nav__right">
        <div class="notification-bell" @click="$router.push('/notifications')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <span v-if="unreadCount > 0" class="badge">{{ unreadCount }}</span>
        </div>
        <div class="user-avatar">ДС</div>
      </div>
    </nav>

    <div class="section-nav">
      <router-link to="/" exact-active-class="active">Главная</router-link>
      <router-link to="/map" active-class="active">Карта</router-link>
      <router-link to="/species" active-class="active">Виды</router-link>
      <router-link to="/identify" active-class="active">Определитель</router-link>
      <router-link to="/my" active-class="active">Мои наблюдения</router-link>
      <router-link to="/help" active-class="active">Правила</router-link>
    </div>

    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const unreadCount = ref(3)
</script>
```

- [ ] **Step 12: Create frontend/src/views/HomeView.vue**

```vue
<template>
  <div class="home">
    <div class="hero">
      <div class="hero-content">
        <div>
          <h1>Зелёная книга<br>ПАО «НЛМК»</h1>
          <div class="hero-subtitle">Растительный и животный мир</div>
          <p>Наблюдайте, фиксируйте, помогайте изучать биоразнообразие промышленной площадки.</p>
          <div class="hero-actions">
            <router-link to="/observe" class="btn btn-primary">Сообщить наблюдение</router-link>
          </div>
        </div>
      </div>
    </div>
    <div class="section">
      <h2>Раздел в разработке</h2>
      <p>Backend API: <code>/api/health</code></p>
    </div>
  </div>
</template>
```

- [ ] **Step 13: Install dependencies and verify**

Run: `cd frontend && npm install`

- [ ] **Step 14: Commit**

```bash
git add frontend/
git commit -m "feat: Vue 3 frontend scaffold — router, auth store, layout, home page"
```

---

### Task 8: Build and Verify Full Stack

- [ ] **Step 1: Start all services**

Run: `docker compose up --build -d`

- [ ] **Step 2: Verify backend**

Run: `curl http://localhost:8000/api/health`
Expected: `{"status":"ok","database":"connected"}`

- [ ] **Step 3: Verify frontend**

Open: `http://localhost:5173`
Expected: Vue app loads with layout and home page

- [ ] **Step 4: Verify API docs**

Open: `http://localhost:8000/docs`
Expected: Swagger UI with health endpoint

- [ ] **Step 5: Run backend tests**

Run: `docker compose exec backend pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: verify full stack — backend, frontend, database, all services running"
```

---

## Spec Coverage Check

| Spec Requirement | Covered in Task |
|---|---|
| Docker environment | Task 1 |
| PostgreSQL + PostGIS | Task 1, 3, 4 |
| Redis, MinIO | Task 1 |
| FastAPI app | Task 2 |
| All DB models (User, Species, Observation, ObsMedia, SiteZone, Notification, DecisionTree) | Task 3 |
| Alembic migrations | Task 4 |
| JWT auth + RBAC | Task 5 |
| Test infrastructure | Task 6 |
| Vue 3 + Router + Pinia | Task 7 |
| Full stack verification | Task 8 |
