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
    # Deduplicate due to joinedload
    seen = set()
    unique_items = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            unique_items.append(item)
    return ObservationListResponse(items=unique_items, total=total)


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
    seen = set()
    unique_items = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            unique_items.append(item)
    return ObservationListResponse(items=unique_items, total=total)


@router.get("/{obs_id}", response_model=ObservationResponse)
def get_observation(obs_id: int, db: Session = Depends(get_db)):
    from geoalchemy2.functions import ST_X, ST_Y
    obs = (
        db.query(Observation)
        .options(joinedload(Observation.media))
        .filter(Observation.id == obs_id)
        .first()
    )
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    # Extract lat/lon from geometry
    coords = db.query(
        ST_Y(Observation.location_point).label("lat"),
        ST_X(Observation.location_point).label("lon"),
    ).filter(Observation.id == obs_id).first()
    result = ObservationResponse.model_validate(obs)
    if coords and coords.lat is not None:
        result.lat = float(coords.lat)
        result.lon = float(coords.lon)
    return result


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


# --- Comments & Likes ---
from app.models.gamification import ObservationComment, ObservationLike
from pydantic import BaseModel as PydanticBaseModel


class CommentCreate(PydanticBaseModel):
    text: str


@router.get("/{obs_id}/comments")
def list_comments(obs_id: int, db: Session = Depends(get_db)):
    comments = db.query(ObservationComment).filter(
        ObservationComment.observation_id == obs_id
    ).order_by(ObservationComment.created_at.asc()).all()
    result = []
    for c in comments:
        user = db.query(User).filter(User.id == c.user_id).first()
        result.append({
            "id": c.id,
            "text": c.text,
            "user_name": user.display_name if user else "Unknown",
            "created_at": c.created_at.isoformat(),
        })
    return {"comments": result}


@router.post("/{obs_id}/comments")
def add_comment(
    obs_id: int,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == obs_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    comment = ObservationComment(
        observation_id=obs_id,
        user_id=user.id,
        text=data.text,
    )
    db.add(comment)
    db.commit()
    return {"id": comment.id, "text": comment.text, "user_name": user.display_name, "created_at": comment.created_at.isoformat()}


@router.get("/{obs_id}/likes")
def get_likes(obs_id: int, db: Session = Depends(get_db)):
    count = db.query(ObservationLike).filter(ObservationLike.observation_id == obs_id).count()
    return {"count": count, "observation_id": obs_id}


@router.post("/{obs_id}/likes")
def toggle_like(
    obs_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == obs_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    existing = db.query(ObservationLike).filter(
        ObservationLike.observation_id == obs_id,
        ObservationLike.user_id == user.id,
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        liked = False
    else:
        db.add(ObservationLike(observation_id=obs_id, user_id=user.id))
        db.commit()
        liked = True
    count = db.query(ObservationLike).filter(ObservationLike.observation_id == obs_id).count()
    return {"liked": liked, "count": count}


@router.get("/{obs_id}/likes/me")
def my_like_status(
    obs_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(ObservationLike).filter(
        ObservationLike.observation_id == obs_id,
        ObservationLike.user_id == user.id,
    ).first()
    count = db.query(ObservationLike).filter(ObservationLike.observation_id == obs_id).count()
    return {"liked": existing is not None, "count": count}
