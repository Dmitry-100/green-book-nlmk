from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_optional_user
from app.database import get_db
from app.models.observation import Observation, ObservationStatus, ObsMedia
from app.models.user import User, UserRole
from app.services.media import get_s3_client
from app.config import settings

router = APIRouter(prefix="/api/media", tags=["media"])

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"


def _serve_from_minio_or_disk(s3_key: str, fallback_dir: str, filename: str, content_type: str, cache_max_age: int = 86400):
    """Try MinIO first, fallback to local media/ directory."""
    # Try MinIO
    try:
        s3 = get_s3_client()
        obj = s3.get_object(Bucket=settings.minio_bucket, Key=s3_key)
        return StreamingResponse(
            obj["Body"],
            media_type=obj.get("ContentType", content_type),
            headers={"Cache-Control": f"public, max-age={cache_max_age}"},
        )
    except Exception:
        pass
    # Fallback to local file
    local_path = MEDIA_DIR / fallback_dir / filename
    if local_path.exists():
        return FileResponse(local_path, media_type=content_type, headers={"Cache-Control": f"public, max-age={cache_max_age}"})
    raise HTTPException(status_code=404, detail="Photo not found")


def _can_view_observation_media(observation: Observation, user: User | None) -> bool:
    if observation.status == ObservationStatus.confirmed:
        return True
    if user is None:
        return False
    if user.role in (UserRole.ecologist, UserRole.admin):
        return True
    return user.id in {observation.author_id, observation.reviewer_id}


def _get_observation_by_media_key(
    *,
    db: Session,
    key_field: str,
    media_key: str,
) -> Observation | None:
    if key_field == "s3_key":
        key_filter = ObsMedia.s3_key == media_key
    elif key_field == "thumbnail_key":
        key_filter = ObsMedia.thumbnail_key == media_key
    else:
        raise ValueError("Unsupported media key field")

    return (
        db.query(Observation)
        .join(ObsMedia, Observation.id == ObsMedia.observation_id)
        .filter(key_filter)
        .first()
    )


@router.get("/species/{filename}")
def serve_species_photo(filename: str):
    return _serve_from_minio_or_disk(f"species/{filename}", "species", filename, "image/jpeg")


@router.get("/species-pdf/{filename}")
def serve_species_pdf_photo(filename: str):
    return _serve_from_minio_or_disk(f"species-pdf/{filename}", "species-pdf", filename, "image/png")


@router.get("/observations/{filename}")
def serve_observation_photo(
    filename: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    s3_key = f"observations/{filename}"
    obs = _get_observation_by_media_key(db=db, key_field="s3_key", media_key=s3_key)
    if obs is None or not _can_view_observation_media(obs, user):
        raise HTTPException(status_code=404, detail="Photo not found")

    return _serve_from_minio_or_disk(s3_key, "observations", filename, "image/jpeg", 3600)


@router.get("/thumbnails/{filename}")
def serve_observation_thumbnail(
    filename: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    thumb_key = f"thumbnails/{filename}"
    obs = _get_observation_by_media_key(
        db=db,
        key_field="thumbnail_key",
        media_key=thumb_key,
    )
    if obs is None or not _can_view_observation_media(obs, user):
        raise HTTPException(status_code=404, detail="Photo not found")
    return _serve_from_minio_or_disk(thumb_key, "thumbnails", filename, "image/jpeg", 3600)
