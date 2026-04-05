from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services.media import get_s3_client
from app.config import settings

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("/species/{filename}")
def serve_species_photo(filename: str):
    """Serve species photo from MinIO."""
    s3_key = f"species/{filename}"
    try:
        s3 = get_s3_client()
        obj = s3.get_object(Bucket=settings.minio_bucket, Key=s3_key)
        return StreamingResponse(
            obj["Body"],
            media_type=obj.get("ContentType", "image/jpeg"),
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Photo not found")


@router.get("/species-pdf/{filename}")
def serve_species_pdf_photo(filename: str):
    """Serve species photo extracted from PDF."""
    s3_key = f"species-pdf/{filename}"
    try:
        s3 = get_s3_client()
        obj = s3.get_object(Bucket=settings.minio_bucket, Key=s3_key)
        return StreamingResponse(
            obj["Body"],
            media_type=obj.get("ContentType", "image/png"),
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Photo not found")


@router.get("/observations/{filename}")
def serve_observation_photo(filename: str):
    """Serve observation photo from MinIO."""
    s3_key = f"observations/{filename}"
    try:
        s3 = get_s3_client()
        obj = s3.get_object(Bucket=settings.minio_bucket, Key=s3_key)
        return StreamingResponse(
            obj["Body"],
            media_type=obj.get("ContentType", "image/jpeg"),
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Photo not found")
