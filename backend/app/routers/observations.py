from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from geoalchemy2.elements import WKTElement
from pydantic import BaseModel as PydanticBaseModel, Field
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user, get_optional_user
from app.config import settings
from app.database import get_db
from app.models.gamification import ObservationComment, ObservationLike
from app.models.observation import (
    Observation,
    ObsMedia,
    ObservationStatus,
    MediaProcessingStatus,
)
from app.models.species import Species, SpeciesGroup
from app.models.user import User, UserRole
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
from app.services.media import (
    create_thumbnail_from_image,
    generate_upload_url,
    optimize_image_object,
    store_uploaded_file,
    validate_uploaded_object,
)

router = APIRouter(prefix="/api/observations", tags=["observations"])
MAX_MEDIA_PER_OBSERVATION = 10


def _invalidate_validation_queue_cache() -> None:
    from app.routers.validation import invalidate_validation_queue_cache

    invalidate_validation_queue_cache()


def _get_species_or_404(species_id: int, db: Session) -> Species:
    species = db.query(Species).filter(Species.id == species_id).first()
    if not species:
        raise HTTPException(status_code=404, detail="Species not found")
    return species


def _can_view_observation(obs: Observation, user: User | None) -> bool:
    if obs.status == ObservationStatus.confirmed:
        return True
    if user is None:
        return False
    if user.role in (UserRole.ecologist, UserRole.admin):
        return True
    return user.id in {obs.author_id, obs.reviewer_id}


def _get_observation_for_read(
    obs_id: int, user: User | None, db: Session, include_media: bool = False
) -> Observation:
    query = db.query(Observation)
    if include_media:
        query = query.options(selectinload(Observation.media))
    obs = query.filter(Observation.id == obs_id).first()
    if not obs or not _can_view_observation(obs, user):
        raise HTTPException(status_code=404, detail="Observation not found")
    return obs


@router.post("", response_model=ObservationResponse, status_code=201)
def create_observation(
    data: ObservationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not data.safety_checked:
        raise HTTPException(
            status_code=400,
            detail="Safety rules must be acknowledged before submission",
        )
    species = None
    if data.species_id:
        species = _get_species_or_404(data.species_id, db)

    site_zone_id = detect_zone(db, data.lat, data.lon)
    point = WKTElement(f"POINT({data.lon} {data.lat})", srid=4326)
    obs = Observation(
        author_id=user.id,
        species_id=data.species_id,
        group=species.group.value if species else data.group.value,
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
    _invalidate_validation_queue_cache()
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
    if not media:
        raise HTTPException(status_code=400, detail="At least one media item is required")
    existing_count = (
        db.query(ObsMedia).filter(ObsMedia.observation_id == obs_id).count()
    )
    if existing_count + len(media) > MAX_MEDIA_PER_OBSERVATION:
        raise HTTPException(
            status_code=400,
            detail=f"Observation can contain up to {MAX_MEDIA_PER_OBSERVATION} media items",
        )

    seen_keys: set[str] = set()
    for m in media:
        if m.s3_key in seen_keys:
            raise HTTPException(status_code=400, detail="Duplicate media keys are not allowed")
        seen_keys.add(m.s3_key)
        try:
            detected_mime, _ = validate_uploaded_object(
                m.s3_key, expected_content_type=m.mime_type
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        if settings.media_async_processing_enabled:
            db.add(ObsMedia(
                observation_id=obs_id,
                s3_key=m.s3_key,
                thumbnail_key=None,
                mime_type=detected_mime,
                processing_status=MediaProcessingStatus.pending,
                processing_attempts=0,
                next_retry_at=None,
                processing_error=None,
                processed_at=None,
            ))
            continue

        try:
            processed_image = None
            if detected_mime.startswith("image/"):
                processed_image = optimize_image_object(m.s3_key, detected_mime)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        thumbnail_key = None
        processed_at = datetime.now(timezone.utc)
        if processed_image is not None:
            try:
                thumbnail_key = create_thumbnail_from_image(m.s3_key, processed_image)
            finally:
                processed_image.close()
        db.add(ObsMedia(
            observation_id=obs_id,
            s3_key=m.s3_key,
            thumbnail_key=thumbnail_key,
            mime_type=detected_mime,
            processing_status=MediaProcessingStatus.ready,
            processing_attempts=1,
            next_retry_at=None,
            processing_error=None,
            processed_at=processed_at,
        ))
    db.commit()
    db.refresh(obs)
    if obs.status in (ObservationStatus.on_review, ObservationStatus.needs_data):
        _invalidate_validation_queue_cache()
    return obs


@router.get("", response_model=ObservationListResponse)
def list_observations(
    group: SpeciesGroup | None = None,
    status: ObservationStatus | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_total: bool = Query(True),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    status_filter = status or ObservationStatus.confirmed
    if status_filter != ObservationStatus.confirmed:
        if user is None or user.role not in (UserRole.ecologist, UserRole.admin):
            raise HTTPException(status_code=403, detail="Not enough permissions")

    query = db.query(Observation).options(selectinload(Observation.media))
    if group:
        query = query.filter(Observation.group == group.value)
    query = query.filter(Observation.status == status_filter)
    total = query.count() if include_total else None
    items = query.order_by(Observation.created_at.desc()).offset(skip).limit(limit).all()
    return ObservationListResponse(items=items, total=total)


@router.get("/my", response_model=ObservationListResponse)
def my_observations(
    status: ObservationStatus | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_total: bool = Query(True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Observation).options(selectinload(Observation.media)).filter(
        Observation.author_id == user.id
    )
    if status:
        query = query.filter(Observation.status == status)
    total = query.count() if include_total else None
    items = query.order_by(Observation.created_at.desc()).offset(skip).limit(limit).all()
    return ObservationListResponse(items=items, total=total)


@router.get("/{obs_id}", response_model=ObservationResponse)
def get_observation(
    obs_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    from geoalchemy2.functions import ST_X, ST_Y
    obs = _get_observation_for_read(obs_id, user, db, include_media=True)
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
    updates = data.model_dump(exclude_unset=True)
    if "comment" in updates:
        obs.comment = updates["comment"]
    if "species_id" in updates:
        if updates["species_id"] is None:
            obs.species_id = None
        else:
            species = _get_species_or_404(updates["species_id"], db)
            obs.species_id = species.id
            obs.group = species.group.value
    db.commit()
    db.refresh(obs)
    if obs.status in (ObservationStatus.on_review, ObservationStatus.needs_data):
        _invalidate_validation_queue_cache()
    return obs


@router.post("/upload")
async def upload_media_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    del user  # Authentication is required; uploaded file ownership is attached later.
    payload = await file.read()
    try:
        return store_uploaded_file(
            file.filename or "upload",
            file.content_type or "",
            payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/upload-url", response_model=UploadUrlResponse)
def get_upload_url(
    data: UploadUrlRequest,
    user: User = Depends(get_current_user),
):
    try:
        result = generate_upload_url(
            data.filename, data.content_type, file_size=data.file_size
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UploadUrlResponse(**result)


# --- Comments & Likes ---
class CommentCreate(PydanticBaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.get("/{obs_id}/comments")
def list_comments(
    obs_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    _get_observation_for_read(obs_id, user, db)
    comments = (
        db.query(ObservationComment, User.display_name)
        .outerjoin(User, User.id == ObservationComment.user_id)
        .filter(ObservationComment.observation_id == obs_id)
        .order_by(ObservationComment.created_at.asc())
        .all()
    )
    result = []
    for c, author_name in comments:
        result.append({
            "id": c.id,
            "text": c.text,
            "user_name": author_name or "Unknown",
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
    _get_observation_for_read(obs_id, user, db)
    comment = ObservationComment(
        observation_id=obs_id,
        user_id=user.id,
        text=data.text,
    )
    db.add(comment)
    db.commit()
    return {"id": comment.id, "text": comment.text, "user_name": user.display_name, "created_at": comment.created_at.isoformat()}


@router.get("/{obs_id}/likes")
def get_likes(
    obs_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    _get_observation_for_read(obs_id, user, db)
    count = db.query(ObservationLike).filter(ObservationLike.observation_id == obs_id).count()
    return {"count": count, "observation_id": obs_id}


@router.post("/{obs_id}/likes")
def toggle_like(
    obs_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_observation_for_read(obs_id, user, db)
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
    _get_observation_for_read(obs_id, user, db)
    existing = db.query(ObservationLike).filter(
        ObservationLike.observation_id == obs_id,
        ObservationLike.user_id == user.id,
    ).first()
    count = db.query(ObservationLike).filter(ObservationLike.observation_id == obs_id).count()
    return {"liked": existing is not None, "count": count}
