from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.observation import MediaProcessingStatus, ObsMedia
from app.services.media import create_thumbnail_from_image, optimize_image_object

MAX_PROCESSING_ERROR_LENGTH = 1000


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _next_retry_at(attempt_number: int) -> datetime:
    delay_seconds = settings.media_processing_retry_backoff_seconds * max(1, attempt_number)
    return _utcnow() + timedelta(seconds=delay_seconds)


def _claim_next_pending_media(db: Session) -> ObsMedia | None:
    now = _utcnow()
    media = (
        db.query(ObsMedia)
        .filter(
            ObsMedia.processing_status == MediaProcessingStatus.pending,
            or_(ObsMedia.next_retry_at.is_(None), ObsMedia.next_retry_at <= now),
        )
        .order_by(ObsMedia.created_at.asc(), ObsMedia.id.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if media is None:
        return None

    media.processing_status = MediaProcessingStatus.processing
    media.processing_error = None
    db.commit()
    db.refresh(media)
    return media


def _process_claimed_media(db: Session, media: ObsMedia) -> str:
    attempt_number = media.processing_attempts + 1
    processed_image = None

    try:
        processed_image = optimize_image_object(media.s3_key, media.mime_type)
        if processed_image is None:
            raise RuntimeError("Unsupported media type for processing")

        thumbnail_key = create_thumbnail_from_image(media.s3_key, processed_image)
        if thumbnail_key is None:
            raise RuntimeError("Failed to create thumbnail")

        media.thumbnail_key = thumbnail_key
        media.processing_status = MediaProcessingStatus.ready
        media.processing_attempts = attempt_number
        media.processing_error = None
        media.next_retry_at = None
        media.processed_at = _utcnow()
        db.commit()
        return "ready"
    except Exception as exc:
        media.processing_attempts = attempt_number
        media.processed_at = None
        media.processing_error = str(exc)[:MAX_PROCESSING_ERROR_LENGTH]
        if attempt_number >= settings.media_processing_max_attempts:
            media.processing_status = MediaProcessingStatus.failed
            media.next_retry_at = None
            db.commit()
            return "failed"

        media.processing_status = MediaProcessingStatus.pending
        media.next_retry_at = _next_retry_at(attempt_number)
        db.commit()
        return "requeued"
    finally:
        if processed_image is not None:
            processed_image.close()


def run_media_processing_batch(db: Session, *, batch_size: int | None = None) -> dict:
    effective_batch_size = batch_size or settings.media_processing_batch_size
    stats = {
        "claimed": 0,
        "ready": 0,
        "requeued": 0,
        "failed": 0,
    }

    for _ in range(effective_batch_size):
        media = _claim_next_pending_media(db)
        if media is None:
            break
        stats["claimed"] += 1

        result = _process_claimed_media(db, media)
        if result == "ready":
            stats["ready"] += 1
        elif result == "requeued":
            stats["requeued"] += 1
        elif result == "failed":
            stats["failed"] += 1

    return stats
