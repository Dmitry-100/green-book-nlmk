from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.auth import require_role
from app.database import get_db
from app.models.notification import Notification, NotificationType
from app.models.observation import Observation, ObservationStatus, SensitiveLevel
from app.models.user import User, UserRole
from app.schemas.observation import ObservationListResponse, ObservationResponse

router = APIRouter(prefix="/api/validation", tags=["validation"])


class ConfirmRequest(BaseModel):
    species_id: int | None = None
    comment: str | None = None
    sensitive_level: SensitiveLevel = SensitiveLevel.open


class RejectRequest(BaseModel):
    comment: str


class RequestDataRequest(BaseModel):
    comment: str


@router.get("/queue", response_model=ObservationListResponse)
def validation_queue(
    status: ObservationStatus | None = Query(ObservationStatus.on_review),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_role(UserRole.ecologist, UserRole.admin)),
    db: Session = Depends(get_db),
):
    query = db.query(Observation).options(joinedload(Observation.media))
    if status:
        query = query.filter(Observation.status == status)
    total = query.count()
    items = query.order_by(Observation.created_at.asc()).offset(skip).limit(limit).all()
    seen = set()
    unique = [x for x in items if x.id not in seen and not seen.add(x.id)]
    return ObservationListResponse(items=unique, total=total)


@router.post("/{obs_id}/confirm", response_model=ObservationResponse)
def confirm_observation(
    obs_id: int,
    data: ConfirmRequest,
    user: User = Depends(require_role(UserRole.ecologist, UserRole.admin)),
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).options(joinedload(Observation.media)).filter(Observation.id == obs_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    obs.status = ObservationStatus.confirmed
    obs.reviewer_id = user.id
    obs.reviewer_comment = data.comment
    obs.sensitive_level = data.sensitive_level
    if data.species_id:
        obs.species_id = data.species_id
    from datetime import datetime
    obs.reviewed_at = datetime.utcnow()
    db.add(Notification(
        user_id=obs.author_id,
        observation_id=obs.id,
        type=NotificationType.confirmed,
        message=f"Ваше наблюдение #{obs.id} подтверждено экологом.",
    ))
    db.commit()

    # Award gamification (points, achievements, first discovery)
    from app.services.gamification import award_gamification
    award_gamification(obs.id, db)

    db.refresh(obs)
    return obs


@router.post("/{obs_id}/reject", response_model=ObservationResponse)
def reject_observation(
    obs_id: int,
    data: RejectRequest,
    user: User = Depends(require_role(UserRole.ecologist, UserRole.admin)),
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).options(joinedload(Observation.media)).filter(Observation.id == obs_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    obs.status = ObservationStatus.rejected
    obs.reviewer_id = user.id
    obs.reviewer_comment = data.comment
    from datetime import datetime
    obs.reviewed_at = datetime.utcnow()
    db.add(Notification(
        user_id=obs.author_id,
        observation_id=obs.id,
        type=NotificationType.rejected,
        message=f"Ваше наблюдение #{obs.id} отклонено. Причина: {data.comment}",
    ))
    db.commit()
    db.refresh(obs)
    return obs


@router.post("/{obs_id}/request-data", response_model=ObservationResponse)
def request_data(
    obs_id: int,
    data: RequestDataRequest,
    user: User = Depends(require_role(UserRole.ecologist, UserRole.admin)),
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).options(joinedload(Observation.media)).filter(Observation.id == obs_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    obs.status = ObservationStatus.needs_data
    obs.reviewer_id = user.id
    obs.reviewer_comment = data.comment
    db.add(Notification(
        user_id=obs.author_id,
        observation_id=obs.id,
        type=NotificationType.needs_data,
        message=f"Эколог запросил уточнения к наблюдению #{obs.id}: {data.comment}",
    ))
    db.commit()
    db.refresh(obs)
    return obs
