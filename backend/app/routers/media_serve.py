import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

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


@router.get("/species/{filename}")
def serve_species_photo(filename: str):
    return _serve_from_minio_or_disk(f"species/{filename}", "species", filename, "image/jpeg")


@router.get("/species-pdf/{filename}")
def serve_species_pdf_photo(filename: str):
    return _serve_from_minio_or_disk(f"species-pdf/{filename}", "species-pdf", filename, "image/png")


@router.get("/observations/{filename}")
def serve_observation_photo(filename: str):
    return _serve_from_minio_or_disk(f"observations/{filename}", "observations", filename, "image/jpeg", 3600)
