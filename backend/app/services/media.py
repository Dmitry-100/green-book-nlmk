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
    ensure_bucket()
    client = get_s3_client()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    key = f"observations/{uuid.uuid4().hex}.{ext}"
    url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.minio_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=600,
    )
    return {"upload_url": url, "s3_key": key}


def create_thumbnail(s3_key: str) -> str | None:
    try:
        client = get_s3_client()
        response = client.get_object(Bucket=settings.minio_bucket, Key=s3_key)
        img = Image.open(response["Body"])
        img.thumbnail(THUMBNAIL_SIZE)
        thumb_key = s3_key.replace("observations/", "thumbnails/")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)
        client.put_object(Bucket=settings.minio_bucket, Key=thumb_key, Body=buf, ContentType="image/jpeg")
        return thumb_key
    except Exception:
        return None


def get_media_url(s3_key: str) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": s3_key},
        ExpiresIn=3600,
    )
