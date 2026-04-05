# Observations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Build the observations system — create observation form with media upload, auto-detect site zone, list/filter observations, "My observations" page.

**Architecture:** FastAPI router for observations CRUD. MinIO presigned URLs for media upload. PostGIS ST_Contains for auto zone detection. Vue.js form with map placeholder, media upload, and group selector.

**Tech Stack:** FastAPI, SQLAlchemy, GeoAlchemy2, boto3/MinIO, Pillow, Vue 3, Element Plus

---

## File Structure

```
backend/app/
├── schemas/
│   └── observation.py
├── routers/
│   └── observations.py
├── services/
│   ├── __init__.py
│   ├── media.py          # MinIO presigned URL + thumbnail
│   └── geo.py            # Zone detection (ST_Contains)
frontend/src/
├── views/
│   ├── ObserveView.vue       # Create observation form
│   └── MyObservationsView.vue
```

---

### Task 1: Backend Services — Media + Geo

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/media.py`
- Create: `backend/app/services/geo.py`

- [ ] **Step 1: Create backend/app/services/__init__.py** (empty)

- [ ] **Step 2: Create backend/app/services/media.py**

```python
import io
import uuid

import boto3
from PIL import Image

from app.config import settings

THUMBNAIL_SIZE = (400, 400)


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
    )


def ensure_bucket():
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.minio_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.minio_bucket)


def generate_upload_url(filename: str, content_type: str) -> dict:
    """Generate a presigned PUT URL for direct upload from frontend."""
    ensure_bucket()
    client = get_s3_client()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    key = f"observations/{uuid.uuid4().hex}.{ext}"
    url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.minio_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=600,
    )
    return {"upload_url": url, "s3_key": key}


def create_thumbnail(s3_key: str) -> str | None:
    """Download image from S3, create thumbnail, upload back."""
    try:
        client = get_s3_client()
        response = client.get_object(Bucket=settings.minio_bucket, Key=s3_key)
        img = Image.open(response["Body"])
        img.thumbnail(THUMBNAIL_SIZE)
        thumb_key = s3_key.replace("observations/", "thumbnails/")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)
        client.put_object(
            Bucket=settings.minio_bucket,
            Key=thumb_key,
            Body=buf,
            ContentType="image/jpeg",
        )
        return thumb_key
    except Exception:
        return None


def get_media_url(s3_key: str) -> str:
    """Generate a presigned GET URL for viewing."""
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": s3_key},
        ExpiresIn=3600,
    )
```

- [ ] **Step 3: Create backend/app/services/geo.py**

```python
from geoalchemy2.functions import ST_Contains, ST_SetSRID, ST_MakePoint
from sqlalchemy.orm import Session

from app.models.site_zone import SiteZone


def detect_zone(db: Session, lat: float, lon: float) -> int | None:
    """Find the site zone containing the given point. Returns zone ID or None."""
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    zone = db.query(SiteZone).filter(ST_Contains(SiteZone.geom, point)).first()
    return zone.id if zone else None


def detect_zones(db: Session, lat: float, lon: float) -> list[dict]:
    """Find all zones containing the point (for overlap cases)."""
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    zones = db.query(SiteZone).filter(ST_Contains(SiteZone.geom, point)).all()
    return [{"id": z.id, "name": z.name} for z in zones]
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/
git commit -m "feat: media service (MinIO presigned URLs, thumbnails) and geo service (zone detection)"
```

---

### Task 2: Observation Schemas

**Files:**
- Create: `backend/app/schemas/observation.py`

- [ ] **Step 1: Create backend/app/schemas/observation.py**

```python
from datetime import datetime
from pydantic import BaseModel
from app.models.observation import (
    ObservationStatus, IncidentType, IncidentSeverity, IncidentStatus, SensitiveLevel,
)


class ObservationCreate(BaseModel):
    group: str
    observed_at: datetime
    lat: float
    lon: float
    species_id: int | None = None
    comment: str | None = None
    is_incident: bool = False
    incident_type: IncidentType | None = None
    incident_severity: IncidentSeverity | None = None
    safety_checked: bool = False


class MediaAttach(BaseModel):
    s3_key: str
    mime_type: str
    thumbnail_key: str | None = None


class ObservationUpdate(BaseModel):
    comment: str | None = None
    species_id: int | None = None


class MediaInfo(BaseModel):
    id: int
    s3_key: str
    thumbnail_key: str | None
    mime_type: str
    model_config = {"from_attributes": True}


class ObservationResponse(BaseModel):
    id: int
    author_id: int
    species_id: int | None
    group: str
    observed_at: datetime
    site_zone_id: int | None
    status: ObservationStatus
    comment: str | None
    is_incident: bool
    incident_type: IncidentType | None
    incident_severity: IncidentSeverity | None
    incident_status: IncidentStatus | None
    sensitive_level: SensitiveLevel
    safety_checked: bool
    created_at: datetime
    media: list[MediaInfo] = []
    model_config = {"from_attributes": True}


class ObservationListResponse(BaseModel):
    items: list[ObservationResponse]
    total: int


class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str


class UploadUrlResponse(BaseModel):
    upload_url: str
    s3_key: str
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/observation.py
git commit -m "feat: Pydantic schemas for observations and media upload"
```

---

### Task 3: Observations API Router

**Files:**
- Create: `backend/app/routers/observations.py`
- Modify: `backend/app/main.py` — register router

- [ ] **Step 1: Create backend/app/routers/observations.py**

```python
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.observation import Observation, ObsMedia, ObservationStatus
from app.models.user import User
from app.schemas.observation import (
    MediaAttach,
    ObservationCreate,
    ObservationListResponse,
    ObservationResponse,
    ObservationUpdate,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.geo import detect_zone
from app.services.media import generate_upload_url

router = APIRouter(prefix="/api/observations", tags=["observations"])


@router.post("", response_model=ObservationResponse, status_code=201)
def create_observation(
    data: ObservationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    site_zone_id = detect_zone(db, data.lat, data.lon)
    point = WKTElement(f"POINT({data.lon} {data.lat})", srid=4326)
    obs = Observation(
        author_id=user.id,
        species_id=data.species_id,
        group=data.group,
        observed_at=data.observed_at,
        location_point=point,
        site_zone_id=site_zone_id,
        status=ObservationStatus.on_review,
        comment=data.comment,
        is_incident=data.is_incident,
        incident_type=data.incident_type,
        incident_severity=data.incident_severity,
        incident_status="new" if data.is_incident else None,
        safety_checked=data.safety_checked,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


@router.post("/{obs_id}/media", response_model=ObservationResponse)
def attach_media(
    obs_id: int,
    media: list[MediaAttach],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == obs_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    if obs.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not your observation")
    for m in media:
        db.add(ObsMedia(
            observation_id=obs_id,
            s3_key=m.s3_key,
            thumbnail_key=m.thumbnail_key,
            mime_type=m.mime_type,
        ))
    db.commit()
    db.refresh(obs)
    return obs


@router.get("", response_model=ObservationListResponse)
def list_observations(
    group: str | None = None,
    status: ObservationStatus | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Observation).options(joinedload(Observation.media))
    if group:
        query = query.filter(Observation.group == group)
    if status:
        query = query.filter(Observation.status == status)
    total = query.count()
    items = query.order_by(Observation.created_at.desc()).offset(skip).limit(limit).all()
    return ObservationListResponse(items=items, total=total)


@router.get("/my", response_model=ObservationListResponse)
def my_observations(
    status: ObservationStatus | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Observation).options(joinedload(Observation.media)).filter(
        Observation.author_id == user.id
    )
    if status:
        query = query.filter(Observation.status == status)
    total = query.count()
    items = query.order_by(Observation.created_at.desc()).offset(skip).limit(limit).all()
    return ObservationListResponse(items=items, total=total)


@router.get("/{obs_id}", response_model=ObservationResponse)
def get_observation(obs_id: int, db: Session = Depends(get_db)):
    obs = (
        db.query(Observation)
        .options(joinedload(Observation.media))
        .filter(Observation.id == obs_id)
        .first()
    )
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    return obs


@router.patch("/{obs_id}", response_model=ObservationResponse)
def update_observation(
    obs_id: int,
    data: ObservationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == obs_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    if obs.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not your observation")
    if obs.status != ObservationStatus.needs_data:
        raise HTTPException(status_code=400, detail="Can only update when status is needs_data")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obs, key, value)
    db.commit()
    db.refresh(obs)
    return obs


@router.post("/upload-url", response_model=UploadUrlResponse)
def get_upload_url(
    data: UploadUrlRequest,
    user: User = Depends(get_current_user),
):
    result = generate_upload_url(data.filename, data.content_type)
    return UploadUrlResponse(**result)
```

- [ ] **Step 2: Register router in main.py**

Add `observations` to imports and `app.include_router(observations.router)`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/observations.py backend/app/main.py
git commit -m "feat: Observations API — create, list, my, detail, media attach, upload URL"
```

---

### Task 4: Frontend — Observation Form + My Observations

**Files:**
- Create: `frontend/src/views/ObserveView.vue`
- Create: `frontend/src/views/MyObservationsView.vue`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Create ObserveView.vue**

Full observation form: group selector (6 icons), date/time, species autocomplete (optional), map placeholder, media upload area, safety checkbox, submit button. On submit, POST to `/api/observations`.

- [ ] **Step 2: Create MyObservationsView.vue**

List of user's observations with status badges, filters by status. Each item shows species name, date, status, thumbnail.

- [ ] **Step 3: Add routes**

```typescript
{ path: 'observe', name: 'observe', component: () => import('../views/ObserveView.vue') },
{ path: 'my', name: 'my-observations', component: () => import('../views/MyObservationsView.vue') },
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/ObserveView.vue frontend/src/views/MyObservationsView.vue frontend/src/router/index.ts
git commit -m "feat: Observation form and My Observations page"
```
