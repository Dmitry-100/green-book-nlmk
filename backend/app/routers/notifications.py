from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationListResponse
from app.services.cache import KeyedTTLCache

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
_UNREAD_COUNT_CACHE = KeyedTTLCache[int, int](
    settings.notification_unread_cache_ttl_seconds,
    max_entries=2048,
)


def invalidate_unread_count_cache(user_id: int | None = None) -> None:
    _UNREAD_COUNT_CACHE.invalidate(user_id)


def _query_unread_count(*, user_id: int, db: Session) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .count()
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    include_total: bool = Query(True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.user_id == user.id)
    total = query.count() if include_total else None
    items = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return NotificationListResponse(items=items, total=total)


@router.patch("/{notif_id}/read")
def mark_read(
    notif_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == user.id).first()
    if notif:
        notif.is_read = True
        db.commit()
        invalidate_unread_count_cache(user.id)
    return {"ok": True}


@router.get("/unread-count")
def unread_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if settings.notification_unread_cache_ttl_seconds > 0:
        count = _UNREAD_COUNT_CACHE.get_or_set(
            user.id,
            lambda: _query_unread_count(user_id=user.id, db=db),
        )
    else:
        count = _query_unread_count(user_id=user.id, db=db)
    return {"count": count}
