from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session, selectinload

from app.auth import require_role
from app.config import settings
from app.database import get_db
from app.models.notification import Notification, NotificationType
from app.models.observation import Observation, ObservationStatus, SensitiveLevel
from app.models.species import Species
from app.models.user import User, UserRole
from app.schemas.observation import ObservationListResponse, ObservationResponse
from app.services.audit import audit_event
from app.services.cache import KeyedTTLCache, RedisKeyedTTLCache

router = APIRouter(prefix="/api/validation", tags=["validation"])
_VALIDATION_QUEUE_CACHE = KeyedTTLCache[tuple[str | None, int, int, bool], dict](
    settings.validation_queue_cache_ttl_seconds,
    max_entries=64,
)
_VALIDATION_QUEUE_REDIS_CACHE = RedisKeyedTTLCache[tuple[str | None, int, int, bool], dict](
    redis_url=settings.redis_url,
    key_prefix="cache:validation:queue",
    ttl_seconds=settings.validation_queue_cache_ttl_seconds,
    fallback_cache=_VALIDATION_QUEUE_CACHE,
    enabled=settings.redis_cache_enabled,
    namespace=settings.redis_cache_namespace,
)


def invalidate_validation_queue_cache() -> None:
    _VALIDATION_QUEUE_REDIS_CACHE.invalidate()


def _invalidate_unread_count_cache(user_id: int) -> None:
    from app.routers.notifications import invalidate_unread_count_cache

    invalidate_unread_count_cache(user_id)


def _build_validation_queue_payload(
    *,
    db: Session,
    status: ObservationStatus | None,
    skip: int,
    limit: int,
    include_total: bool,
) -> dict:
    query = db.query(Observation).options(selectinload(Observation.media))
    if status:
        query = query.filter(Observation.status == status)
    total = query.count() if include_total else None
    items = query.order_by(Observation.created_at.asc()).offset(skip).limit(limit).all()
    return {
        "items": [
            ObservationResponse.model_validate(item).model_dump(mode="json")
            for item in items
        ],
        "total": total,
    }


class ConfirmRequest(BaseModel):
    species_id: int | None = Field(default=None, gt=0)
    comment: str | None = Field(default=None, max_length=2000)
    sensitive_level: SensitiveLevel = SensitiveLevel.open

    @field_validator("comment", mode="before")
    @classmethod
    def _normalize_optional_comment(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class RejectRequest(BaseModel):
    comment: str = Field(min_length=3, max_length=2000)

    @field_validator("comment", mode="before")
    @classmethod
    def _normalize_comment(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Comment must not be blank")
        return value


class RequestDataRequest(BaseModel):
    comment: str = Field(min_length=3, max_length=2000)

    @field_validator("comment", mode="before")
    @classmethod
    def _normalize_comment(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Comment must not be blank")
        return value


def _get_observation_or_404(obs_id: int, db: Session) -> Observation:
    obs = (
        db.query(Observation)
        .options(selectinload(Observation.media))
        .filter(Observation.id == obs_id)
        .first()
    )
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    return obs


def _require_status(obs: Observation, allowed: tuple[ObservationStatus, ...], action: str):
    if obs.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot {action} observation in status {obs.status.value}",
        )


def _get_species_or_404(species_id: int, db: Session) -> Species:
    species = db.query(Species).filter(Species.id == species_id).first()
    if not species:
        raise HTTPException(status_code=404, detail="Species not found")
    return species


@router.get("/queue", response_model=ObservationListResponse)
def validation_queue(
    status: ObservationStatus | None = Query(ObservationStatus.on_review),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_total: bool = Query(True),
    user: User = Depends(require_role(UserRole.ecologist, UserRole.admin)),
    db: Session = Depends(get_db),
):
    if settings.validation_queue_cache_ttl_seconds > 0:
        cache_key = (status.value if status else None, skip, limit, include_total)
        return _VALIDATION_QUEUE_REDIS_CACHE.get_or_set(
            cache_key,
            lambda: _build_validation_queue_payload(
                db=db,
                status=status,
                skip=skip,
                limit=limit,
                include_total=include_total,
            ),
        )
    return _build_validation_queue_payload(
        db=db,
        status=status,
        skip=skip,
        limit=limit,
        include_total=include_total,
    )


@router.post("/{obs_id}/confirm", response_model=ObservationResponse)
def confirm_observation(
    obs_id: int,
    data: ConfirmRequest,
    user: User = Depends(require_role(UserRole.ecologist, UserRole.admin)),
    db: Session = Depends(get_db),
):
    obs = _get_observation_or_404(obs_id, db)
    if obs.status == ObservationStatus.confirmed:
        audit_event(
            action="validation.confirm",
            actor=user,
            target_type="observation",
            target_id=obs.id,
            outcome="noop",
            details={"reason": "already_confirmed"},
            db=db,
        )
        return obs
    previous_status = obs.status.value
    _require_status(
        obs,
        allowed=(ObservationStatus.on_review, ObservationStatus.needs_data),
        action="confirm",
    )

    species = None
    if data.species_id is not None:
        species = _get_species_or_404(data.species_id, db)
        obs.species_id = species.id
    elif obs.species_id:
        species = _get_species_or_404(obs.species_id, db)

    if species:
        obs.group = species.group.value

    obs.status = ObservationStatus.confirmed
    obs.reviewer_id = user.id
    obs.reviewer_comment = data.comment
    obs.sensitive_level = data.sensitive_level
    obs.reviewed_at = datetime.now(timezone.utc)
    db.add(Notification(
        user_id=obs.author_id,
        observation_id=obs.id,
        type=NotificationType.confirmed,
        message=f"Ваше наблюдение #{obs.id} подтверждено экологом.",
    ))

    # Award gamification in the same DB transaction as the status change.
    from app.services.gamification import award_gamification
    award_gamification(obs.id, db, commit=False)

    db.commit()
    db.refresh(obs)
    invalidate_validation_queue_cache()
    _invalidate_unread_count_cache(obs.author_id)
    audit_event(
        action="validation.confirm",
        actor=user,
        target_type="observation",
        target_id=obs.id,
        details={
            "previous_status": previous_status,
            "new_status": obs.status.value,
            "species_id": obs.species_id,
            "sensitive_level": obs.sensitive_level.value,
        },
        db=db,
    )
    return obs


@router.post("/{obs_id}/reject", response_model=ObservationResponse)
def reject_observation(
    obs_id: int,
    data: RejectRequest,
    user: User = Depends(require_role(UserRole.ecologist, UserRole.admin)),
    db: Session = Depends(get_db),
):
    obs = _get_observation_or_404(obs_id, db)
    if obs.status == ObservationStatus.rejected:
        audit_event(
            action="validation.reject",
            actor=user,
            target_type="observation",
            target_id=obs.id,
            outcome="noop",
            details={"reason": "already_rejected"},
            db=db,
        )
        return obs
    previous_status = obs.status.value
    _require_status(
        obs,
        allowed=(ObservationStatus.on_review, ObservationStatus.needs_data),
        action="reject",
    )
    obs.status = ObservationStatus.rejected
    obs.reviewer_id = user.id
    obs.reviewer_comment = data.comment
    obs.reviewed_at = datetime.now(timezone.utc)
    db.add(Notification(
        user_id=obs.author_id,
        observation_id=obs.id,
        type=NotificationType.rejected,
        message=f"Ваше наблюдение #{obs.id} отклонено. Причина: {data.comment}",
    ))
    db.commit()
    db.refresh(obs)
    invalidate_validation_queue_cache()
    _invalidate_unread_count_cache(obs.author_id)
    audit_event(
        action="validation.reject",
        actor=user,
        target_type="observation",
        target_id=obs.id,
        details={
            "previous_status": previous_status,
            "new_status": obs.status.value,
            "comment": data.comment,
        },
        db=db,
    )
    return obs


@router.post("/{obs_id}/request-data", response_model=ObservationResponse)
def request_data(
    obs_id: int,
    data: RequestDataRequest,
    user: User = Depends(require_role(UserRole.ecologist, UserRole.admin)),
    db: Session = Depends(get_db),
):
    obs = _get_observation_or_404(obs_id, db)
    if obs.status == ObservationStatus.needs_data:
        audit_event(
            action="validation.request_data",
            actor=user,
            target_type="observation",
            target_id=obs.id,
            outcome="noop",
            details={"reason": "already_needs_data"},
            db=db,
        )
        return obs
    previous_status = obs.status.value
    _require_status(
        obs,
        allowed=(ObservationStatus.on_review,),
        action="request additional data for",
    )
    obs.status = ObservationStatus.needs_data
    obs.reviewer_id = user.id
    obs.reviewer_comment = data.comment
    obs.reviewed_at = datetime.now(timezone.utc)
    db.add(Notification(
        user_id=obs.author_id,
        observation_id=obs.id,
        type=NotificationType.needs_data,
        message=f"Эколог запросил уточнения к наблюдению #{obs.id}: {data.comment}",
    ))
    db.commit()
    db.refresh(obs)
    invalidate_validation_queue_cache()
    _invalidate_unread_count_cache(obs.author_id)
    audit_event(
        action="validation.request_data",
        actor=user,
        target_type="observation",
        target_id=obs.id,
        details={
            "previous_status": previous_status,
            "new_status": obs.status.value,
            "comment": data.comment,
        },
        db=db,
    )
    return obs
