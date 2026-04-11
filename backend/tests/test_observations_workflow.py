from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement

import app.routers.observations as observations_router
from app.config import settings
from app.models.observation import (
    MediaProcessingStatus,
    ObsMedia,
    Observation,
    ObservationStatus,
)
from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.models.user import User, UserRole
from tests.conftest import make_token


def _create_user(
    db,
    *,
    external_id: str,
    role: UserRole = UserRole.employee,
) -> User:
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


def _create_species(db, *, name_suffix: str, group: SpeciesGroup) -> Species:
    species = Species(
        name_ru=f"Species {name_suffix}",
        name_latin=f"Species {name_suffix} latin",
        group=group,
        category=SpeciesCategory.typical,
        conservation_status=None,
        is_poisonous=False,
        season_info=None,
        biotopes=None,
        description=None,
        do_dont_rules=None,
        qr_url=None,
        photo_urls=[],
    )
    db.add(species)
    db.commit()
    db.refresh(species)
    return species


def _create_observation(
    db,
    *,
    author_id: int,
    status: ObservationStatus,
    group: str,
    species_id: int | None = None,
) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=species_id,
        group=group,
        observed_at=datetime.now(timezone.utc),
        location_point=WKTElement("POINT(39.60 52.59)", srid=4326),
        status=status,
        comment="observation workflow test",
        is_incident=False,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_create_observation_requires_safety_ack(client, employee_token):
    response = client.post(
        "/api/observations",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={
            "group": "birds",
            "observed_at": "2026-04-11T10:00:00Z",
            "lat": 52.59,
            "lon": 39.60,
            "safety_checked": False,
            "is_incident": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Safety rules must be acknowledged before submission"


def test_create_observation_uses_species_group(client, db, employee_token, monkeypatch):
    species = _create_species(db, name_suffix="CreateFlow", group=SpeciesGroup.plants)
    monkeypatch.setattr(observations_router, "detect_zone", lambda *_args, **_kwargs: None)

    response = client.post(
        "/api/observations",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={
            "group": "birds",
            "species_id": species.id,
            "observed_at": "2026-04-11T10:30:00Z",
            "lat": 52.59,
            "lon": 39.60,
            "safety_checked": True,
            "comment": "created via API",
            "is_incident": False,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["species_id"] == species.id
    assert payload["group"] == SpeciesGroup.plants.value
    assert payload["site_zone_id"] is None
    assert payload["status"] == ObservationStatus.on_review.value


def test_create_observation_validates_incident_fields(client, employee_token):
    response = client.post(
        "/api/observations",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={
            "group": "birds",
            "observed_at": "2026-04-11T11:00:00Z",
            "lat": 52.59,
            "lon": 39.60,
            "safety_checked": True,
            "is_incident": True,
        },
    )

    assert response.status_code == 422
    assert "incident_type and incident_severity are required for incidents" in str(
        response.json()
    )


def test_update_observation_requires_author_and_needs_data_status(client, db, employee_token):
    author = _create_user(db, external_id="test-user-001")
    other_user_token = make_token(
        external_id="obs-update-other-001",
        name="Other User",
        email="obs-update-other-001@nlmk.com",
        role="employee",
    )
    obs = _create_observation(
        db,
        author_id=author.id,
        status=ObservationStatus.on_review,
        group=SpeciesGroup.birds.value,
    )

    forbidden = client.patch(
        f"/api/observations/{obs.id}",
        headers={"Authorization": f"Bearer {other_user_token}"},
        json={"comment": "updated"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Not your observation"

    invalid_status = client.patch(
        f"/api/observations/{obs.id}",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"comment": "updated"},
    )
    assert invalid_status.status_code == 400
    assert invalid_status.json()["detail"] == "Can only update when status is needs_data"


def test_update_observation_applies_species_and_comment(client, db, employee_token):
    author = _create_user(db, external_id="test-user-001")
    source_species = _create_species(db, name_suffix="Source", group=SpeciesGroup.birds)
    target_species = _create_species(db, name_suffix="Target", group=SpeciesGroup.mammals)
    obs = _create_observation(
        db,
        author_id=author.id,
        status=ObservationStatus.needs_data,
        group=source_species.group.value,
        species_id=source_species.id,
    )

    response = client.patch(
        f"/api/observations/{obs.id}",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"comment": "updated comment", "species_id": target_species.id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["comment"] == "updated comment"
    assert payload["species_id"] == target_species.id
    assert payload["group"] == target_species.group.value

    db.refresh(obs)
    assert obs.comment == "updated comment"
    assert obs.species_id == target_species.id
    assert obs.group == target_species.group.value


def test_comments_and_likes_flow_for_confirmed_observation(client, db):
    author = _create_user(db, external_id="obs-comment-author-001")
    obs = _create_observation(
        db,
        author_id=author.id,
        status=ObservationStatus.confirmed,
        group=SpeciesGroup.birds.value,
    )
    viewer_token = make_token(
        external_id="obs-viewer-777",
        name="Obs Viewer",
        email="obs-viewer-777@nlmk.com",
        role="employee",
    )
    headers = {"Authorization": f"Bearer {viewer_token}"}

    comment_response = client.post(
        f"/api/observations/{obs.id}/comments",
        headers=headers,
        json={"text": "Looks great"},
    )
    assert comment_response.status_code == 200
    assert comment_response.json()["text"] == "Looks great"

    comments_response = client.get(f"/api/observations/{obs.id}/comments")
    assert comments_response.status_code == 200
    comments = comments_response.json()["comments"]
    assert len(comments) == 1
    assert comments[0]["text"] == "Looks great"
    assert comments[0]["user_name"] == "Obs Viewer"

    first_like = client.post(f"/api/observations/{obs.id}/likes", headers=headers)
    assert first_like.status_code == 200
    assert first_like.json()["liked"] is True
    assert first_like.json()["count"] == 1

    like_status = client.get(f"/api/observations/{obs.id}/likes/me", headers=headers)
    assert like_status.status_code == 200
    assert like_status.json()["liked"] is True
    assert like_status.json()["count"] == 1

    likes_count = client.get(f"/api/observations/{obs.id}/likes")
    assert likes_count.status_code == 200
    assert likes_count.json()["count"] == 1

    second_like = client.post(f"/api/observations/{obs.id}/likes", headers=headers)
    assert second_like.status_code == 200
    assert second_like.json()["liked"] is False
    assert second_like.json()["count"] == 0


def test_attach_media_rejects_duplicates_and_respects_max_limit(
    client, db, employee_token, monkeypatch
):
    monkeypatch.setattr(settings, "media_async_processing_enabled", True)
    monkeypatch.setattr(
        observations_router,
        "validate_uploaded_object",
        lambda s3_key, expected_content_type=None: ("image/jpeg", 1024),
    )

    author = _create_user(db, external_id="test-user-001")
    obs = _create_observation(
        db,
        author_id=author.id,
        status=ObservationStatus.on_review,
        group=SpeciesGroup.birds.value,
    )

    duplicate_payload = [
        {"s3_key": "observations/dup.jpg", "mime_type": "image/jpeg"},
        {"s3_key": "observations/dup.jpg", "mime_type": "image/jpeg"},
    ]
    duplicate_response = client.post(
        f"/api/observations/{obs.id}/media",
        headers={"Authorization": f"Bearer {employee_token}"},
        json=duplicate_payload,
    )
    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"] == "Duplicate media keys are not allowed"

    for index in range(observations_router.MAX_MEDIA_PER_OBSERVATION):
        db.add(
            ObsMedia(
                observation_id=obs.id,
                s3_key=f"observations/existing-{index}.jpg",
                thumbnail_key=f"thumbnails/existing-{index}.jpg",
                mime_type="image/jpeg",
                processing_status=MediaProcessingStatus.ready,
                processing_attempts=1,
            )
        )
    db.commit()

    limit_response = client.post(
        f"/api/observations/{obs.id}/media",
        headers={"Authorization": f"Bearer {employee_token}"},
        json=[{"s3_key": "observations/new-over-limit.jpg", "mime_type": "image/jpeg"}],
    )
    assert limit_response.status_code == 400
    assert "Observation can contain up to" in limit_response.json()["detail"]


def test_attach_media_returns_502_on_storage_runtime_error(
    client, db, employee_token, monkeypatch
):
    monkeypatch.setattr(settings, "media_async_processing_enabled", True)

    def _raise_runtime(*_args, **_kwargs):
        raise RuntimeError("storage backend unavailable")

    monkeypatch.setattr(observations_router, "validate_uploaded_object", _raise_runtime)

    author = _create_user(db, external_id="test-user-001")
    obs = _create_observation(
        db,
        author_id=author.id,
        status=ObservationStatus.on_review,
        group=SpeciesGroup.birds.value,
    )

    response = client.post(
        f"/api/observations/{obs.id}/media",
        headers={"Authorization": f"Bearer {employee_token}"},
        json=[{"s3_key": "observations/runtime-error.jpg", "mime_type": "image/jpeg"}],
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "storage backend unavailable"
