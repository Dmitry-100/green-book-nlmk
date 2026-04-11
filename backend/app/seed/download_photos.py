"""Download species photos from Wikimedia to MinIO.

Usage: docker compose exec backend python -m app.seed.download_photos
"""
import time
import urllib.request

from app.database import SessionLocal
from app.models.species import Species
from app.services.media import get_s3_client, ensure_bucket
from app.config import settings


def download_photos():
    db = SessionLocal()
    ensure_bucket()
    s3 = get_s3_client()

    species_with_photos = db.query(Species).filter(
        Species.photo_urls.is_not(None)
    ).all()

    updated = 0
    for sp in species_with_photos:
        if not sp.photo_urls:
            continue
        url = sp.photo_urls[0]
        if not url.startswith("https://upload.wikimedia.org"):
            continue  # Already local

        print(f"Downloading: {sp.name_latin}...", end=" ")
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "GreenBookNLMK/1.0 (ecological portal; contact@nlmk.com)"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()

            ext = url.rsplit(".", 1)[-1].lower()
            if ext not in ("jpg", "jpeg", "png"):
                ext = "jpg"
            s3_key = f"species/{sp.id}.{ext}"

            s3.put_object(
                Bucket=settings.minio_bucket,
                Key=s3_key,
                Body=data,
                ContentType=f"image/{ext}",
            )

            # Update to local MinIO URL
            sp.photo_urls = [f"/api/media/species/{sp.id}.{ext}"]
            updated += 1
            print("OK")
            time.sleep(1)  # Rate limit respect
        except Exception as e:
            print(f"FAILED: {e}")

    db.commit()
    db.close()
    print(f"\nDownloaded {updated} photos to MinIO.")


if __name__ == "__main__":
    download_photos()
