from datetime import datetime, timedelta, timezone

from geoalchemy2.elements import WKTElement
from PIL import Image

import app.routers.observations as observations_router
from app.config import settings
from app.models.observation import (
    MediaProcessingStatus,
    ObsMedia,
    Observation,
    ObservationStatus,
)
from app.models.user import User, UserRole
from app.services.media_pipeline import run_media_processing_batch
from tests.conftest import make_token


def _create_user(db, *, external_id: str, role: UserRole = UserRole.employee) -> User:
    user = User(
        external_id=external_id,
        display_name=external_id,
        email=f"{external_id}@nlmk.com",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_observation(db, *, author_id: int) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=None,
        group="birds",
        observed_at=datetime.now(timezone.utc),
        location_point=WKTElement("POINT(39.60 52.59)", srid=4326),
        status=ObservationStatus.on_review,
        comment="media pipeline test",
        is_incident=False,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_attach_media_async_enqueues_pending_processing(client, db, monkeypatch):
    monkeypatch.setattr(settings, "media_async_processing_enabled", True)
    monkeypatch.setattr(
        observations_router,
        "validate_uploaded_object",
        lambda s3_key, expected_content_type=None: ("image/jpeg", 1234),
    )

    def _sync_processing_should_not_run(*_args, **_kwargs):
        raise AssertionError("sync image processing should be disabled in async mode")

    monkeypatch.setattr(
        observations_router,
        "optimize_image_object",
        _sync_processing_should_not_run,
    )

    author = _create_user(db, external_id="media-async-author-001")
    obs = _create_observation(db, author_id=author.id)
    token = make_token(
        external_id=author.external_id,
        name=author.display_name,
        email=author.email,
        role="employee",
    )

    response = client.post(
        f"/api/observations/{obs.id}/media",
        headers={"Authorization": f"Bearer {token}"},
        json=[{"s3_key": "observations/async-queued.jpg", "mime_type": "image/jpeg"}],
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["media"]) == 1
    media_item = payload["media"][0]
    assert media_item["processing_status"] == MediaProcessingStatus.pending.value
    assert media_item["processing_attempts"] == 0
    assert media_item["thumbnail_key"] is None

    media_row = db.query(ObsMedia).filter(ObsMedia.observation_id == obs.id).first()
    assert media_row is not None
    assert media_row.processing_status == MediaProcessingStatus.pending
    assert media_row.processing_attempts == 0


def test_media_pipeline_batch_marks_media_ready(db, monkeypatch):
    monkeypatch.setattr(settings, "media_processing_batch_size", 10)
    monkeypatch.setattr(settings, "media_processing_max_attempts", 3)

    author = _create_user(db, external_id="media-worker-author-001")
    obs = _create_observation(db, author_id=author.id)
    media_row = ObsMedia(
        observation_id=obs.id,
        s3_key="observations/queued-ready.jpg",
        thumbnail_key=None,
        mime_type="image/jpeg",
        processing_status=MediaProcessingStatus.pending,
        processing_attempts=0,
    )
    db.add(media_row)
    db.commit()

    monkeypatch.setattr(
        "app.services.media_pipeline.optimize_image_object",
        lambda s3_key, content_type: Image.new("RGB", (120, 120), color=(10, 90, 140)),
    )
    monkeypatch.setattr(
        "app.services.media_pipeline.create_thumbnail_from_image",
        lambda s3_key, image: s3_key.replace("observations/", "thumbnails/", 1),
    )

    stats = run_media_processing_batch(db, batch_size=10)
    assert stats["claimed"] == 1
    assert stats["ready"] == 1
    assert stats["requeued"] == 0
    assert stats["failed"] == 0

    db.refresh(media_row)
    assert media_row.processing_status == MediaProcessingStatus.ready
    assert media_row.processing_attempts == 1
    assert media_row.thumbnail_key == "thumbnails/queued-ready.jpg"
    assert media_row.processed_at is not None


def test_media_pipeline_retries_then_marks_failed(db, monkeypatch):
    monkeypatch.setattr(settings, "media_processing_batch_size", 10)
    monkeypatch.setattr(settings, "media_processing_max_attempts", 2)
    monkeypatch.setattr(settings, "media_processing_retry_backoff_seconds", 1)

    author = _create_user(db, external_id="media-worker-author-002")
    obs = _create_observation(db, author_id=author.id)
    media_row = ObsMedia(
        observation_id=obs.id,
        s3_key="observations/queued-fail.jpg",
        thumbnail_key=None,
        mime_type="image/jpeg",
        processing_status=MediaProcessingStatus.pending,
        processing_attempts=0,
    )
    db.add(media_row)
    db.commit()

    def _raise_processing_error(*_args, **_kwargs):
        raise RuntimeError("processing failed")

    monkeypatch.setattr(
        "app.services.media_pipeline.optimize_image_object",
        _raise_processing_error,
    )

    first = run_media_processing_batch(db, batch_size=10)
    assert first["claimed"] == 1
    assert first["ready"] == 0
    assert first["requeued"] == 1
    assert first["failed"] == 0

    db.refresh(media_row)
    assert media_row.processing_status == MediaProcessingStatus.pending
    assert media_row.processing_attempts == 1
    assert media_row.next_retry_at is not None
    assert media_row.processing_error is not None

    media_row.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    second = run_media_processing_batch(db, batch_size=10)
    assert second["claimed"] == 1
    assert second["ready"] == 0
    assert second["requeued"] == 0
    assert second["failed"] == 1

    db.refresh(media_row)
    assert media_row.processing_status == MediaProcessingStatus.failed
    assert media_row.processing_attempts == 2
    assert media_row.next_retry_at is None
