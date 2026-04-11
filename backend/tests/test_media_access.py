from datetime import datetime, timezone

from fastapi.responses import PlainTextResponse
from geoalchemy2.elements import WKTElement

import app.routers.media_serve as media_serve_router
from app.models.observation import ObsMedia, Observation, ObservationStatus
from app.models.user import User, UserRole
from tests.conftest import make_token


def _create_user(db, external_id: str, email: str, role: UserRole = UserRole.employee) -> User:
    user = User(
        external_id=external_id,
        display_name=external_id,
        email=email,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_observation_with_media(
    db,
    *,
    author_id: int,
    status: ObservationStatus,
    media_key: str,
    thumbnail_key: str | None = None,
) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=None,
        group="birds",
        observed_at=datetime.now(timezone.utc),
        location_point=WKTElement("POINT(39.60 52.59)", srid=4326),
        status=status,
        comment="media access test",
        is_incident=False,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)

    db.add(
        ObsMedia(
            observation_id=obs.id,
            s3_key=media_key,
            thumbnail_key=thumbnail_key,
            mime_type="image/jpeg",
        )
    )
    db.commit()
    return obs


def _mock_media_response(*_args, **_kwargs):
    return PlainTextResponse("ok", media_type="text/plain")


def test_private_observation_media_is_hidden_for_public(client, db, monkeypatch):
    monkeypatch.setattr(media_serve_router, "_serve_from_minio_or_disk", _mock_media_response)

    author = _create_user(db, external_id="media-author-001", email="media-author-001@nlmk.com")
    _create_user(db, external_id="media-other-001", email="media-other-001@nlmk.com")

    _create_observation_with_media(
        db,
        author_id=author.id,
        status=ObservationStatus.on_review,
        media_key="observations/private-observation.jpg",
        thumbnail_key="thumbnails/private-observation.jpg",
    )

    anonymous_response = client.get("/api/media/observations/private-observation.jpg")
    assert anonymous_response.status_code == 404
    anonymous_thumb_response = client.get("/api/media/thumbnails/private-observation.jpg")
    assert anonymous_thumb_response.status_code == 404

    other_token = make_token(
        external_id="media-other-001",
        name="Media Other",
        email="media-other-001@nlmk.com",
        role="employee",
    )
    other_response = client.get(
        "/api/media/observations/private-observation.jpg",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_response.status_code == 404
    other_thumb_response = client.get(
        "/api/media/thumbnails/private-observation.jpg",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_thumb_response.status_code == 404

    author_token = make_token(
        external_id="media-author-001",
        name="Media Author",
        email="media-author-001@nlmk.com",
        role="employee",
    )
    author_response = client.get(
        "/api/media/observations/private-observation.jpg",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert author_response.status_code == 200
    author_thumb_response = client.get(
        "/api/media/thumbnails/private-observation.jpg",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert author_thumb_response.status_code == 200

    ecologist_token = make_token(
        external_id="media-eco-001",
        name="Media Eco",
        email="media-eco-001@nlmk.com",
        role="ecologist",
    )
    eco_response = client.get(
        "/api/media/observations/private-observation.jpg",
        headers={"Authorization": f"Bearer {ecologist_token}"},
    )
    assert eco_response.status_code == 200
    eco_thumb_response = client.get(
        "/api/media/thumbnails/private-observation.jpg",
        headers={"Authorization": f"Bearer {ecologist_token}"},
    )
    assert eco_thumb_response.status_code == 200


def test_confirmed_observation_media_is_public(client, db, monkeypatch):
    monkeypatch.setattr(media_serve_router, "_serve_from_minio_or_disk", _mock_media_response)

    author = _create_user(db, external_id="media-author-002", email="media-author-002@nlmk.com")
    _create_observation_with_media(
        db,
        author_id=author.id,
        status=ObservationStatus.confirmed,
        media_key="observations/public-observation.jpg",
        thumbnail_key="thumbnails/public-observation.jpg",
    )

    response = client.get("/api/media/observations/public-observation.jpg")
    assert response.status_code == 200
    thumbnail_response = client.get("/api/media/thumbnails/public-observation.jpg")
    assert thumbnail_response.status_code == 200
