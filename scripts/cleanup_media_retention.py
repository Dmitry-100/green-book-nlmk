#!/usr/bin/env python3
"""Dry-run/apply cleanup for media retention rules."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import settings
from app.database import SessionLocal
from app.models.observation import ObsMedia, Observation, ObservationStatus
from app.services.media import get_s3_client


def _delete_key(client, key: str, *, apply: bool) -> None:
    print(f"{'DELETE' if apply else 'DRY'} {key}")
    if apply:
        client.delete_object(Bucket=settings.minio_bucket, Key=key)


def _iter_storage_keys(client):
    paginator = client.get_paginator("list_objects_v2")
    pages = paginator.paginate(
        Bucket=settings.minio_bucket,
        Prefix="observations/",
    )
    for page in pages:
        for item in page.get("Contents", []):
            key = item.get("Key")
            if key:
                yield key, item.get("LastModified")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="delete objects and DB rows")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    unattached_cutoff = now - timedelta(hours=settings.unattached_media_retention_hours)
    rejected_cutoff = now - timedelta(days=settings.rejected_observation_media_retention_days)
    client = get_s3_client()

    with SessionLocal() as db:
        attached_keys = {
            key
            for row in db.query(ObsMedia.s3_key, ObsMedia.thumbnail_key).all()
            for key in row
            if key
        }
        unattached = []
        for key, last_modified in _iter_storage_keys(client):
            if key in attached_keys:
                continue
            if last_modified is None or last_modified < unattached_cutoff:
                unattached.append(key)

        rejected_media = (
            db.query(ObsMedia)
            .join(Observation, Observation.id == ObsMedia.observation_id)
            .filter(
                Observation.status == ObservationStatus.rejected,
                Observation.reviewed_at.is_not(None),
                Observation.reviewed_at < rejected_cutoff,
            )
            .all()
        )

        for key in unattached:
            _delete_key(client, key, apply=args.apply)
        for media in rejected_media:
            _delete_key(client, media.s3_key, apply=args.apply)
            if media.thumbnail_key:
                _delete_key(client, media.thumbnail_key, apply=args.apply)
            if args.apply:
                db.delete(media)
        if args.apply:
            db.commit()
        print(
            f"SUMMARY unattached={len(unattached)} "
            f"rejected_media={len(rejected_media)} apply={args.apply}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
