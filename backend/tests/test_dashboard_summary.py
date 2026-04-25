from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement

from app.models.gamification import UserPoints
from app.models.observation import Observation, ObservationStatus, ObsMedia
from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.models.user import User, UserRole


def _create_user(db, *, external_id: str, role: UserRole) -> User:
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


def _create_species(
    db,
    *,
    latin: str,
    group: SpeciesGroup,
    audio_url: str | None = None,
) -> Species:
    species = Species(
        name_ru=f"Вид {latin}",
        name_latin=latin,
        group=group,
        category=SpeciesCategory.typical,
        description="Описание вида для факта дня",
        conservation_status="Охраняемый вид",
        photo_urls=[f"/api/media/species/{latin}.jpg"],
        audio_url=audio_url,
    )
    db.add(species)
    db.commit()
    db.refresh(species)
    return species


def _create_observation(
    db,
    *,
    author_id: int,
    species_id: int | None,
    group: str,
    status: ObservationStatus,
) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=species_id,
        group=group,
        observed_at=datetime.now(timezone.utc),
        location_point=WKTElement("POINT(39.60 52.59)", srid=4326),
        status=status,
        comment="dashboard test",
        is_incident=False,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_dashboard_summary_returns_aggregated_data(client, db, employee_token):
    current_user = _create_user(db, external_id="test-user-001", role=UserRole.employee)
    other_user = _create_user(db, external_id="dashboard-other", role=UserRole.employee)
    third_user = _create_user(db, external_id="dashboard-third", role=UserRole.employee)

    species_bird = _create_species(
        db,
        latin="DashBird",
        group=SpeciesGroup.birds,
        audio_url="/api/media/species-audio/dash-bird.ogg",
    )
    _create_species(db, latin="DashPlant", group=SpeciesGroup.plants)

    confirmed_obs = _create_observation(
        db,
        author_id=other_user.id,
        species_id=species_bird.id,
        group=SpeciesGroup.birds.value,
        status=ObservationStatus.confirmed,
    )
    db.add(
        ObsMedia(
            observation_id=confirmed_obs.id,
            s3_key="observations/dash-photo.jpg",
            thumbnail_key="thumbnails/dash-photo.jpg",
            mime_type="image/jpeg",
        )
    )
    db.commit()

    db.add_all(
        [
            UserPoints(
                user_id=other_user.id,
                observation_id=confirmed_obs.id,
                points=15,
                reason="confirmed observation",
            ),
            UserPoints(
                user_id=current_user.id,
                observation_id=None,
                points=30,
                reason="first discovery",
            ),
            UserPoints(
                user_id=third_user.id,
                observation_id=None,
                points=7,
                reason="participation",
            ),
        ]
    )
    db.commit()

    _create_observation(
        db,
        author_id=current_user.id,
        species_id=species_bird.id,
        group=SpeciesGroup.birds.value,
        status=ObservationStatus.on_review,
    )

    response = client.get(
        "/api/dashboard/summary",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert "private" in response.headers.get("cache-control", "")
    payload = response.json()

    assert payload["stats"]["species"] == 2
    assert payload["stats"]["confirmed"] == 1
    assert payload["stats"]["on_review"] == 1
    assert payload["stats"]["total_obs"] == 1
    assert payload["species_by_group"]["birds"] == 1
    assert payload["species_by_group"]["plants"] == 1
    assert len(payload["recent_species"]) == 2
    recent_by_id = {species["id"]: species for species in payload["recent_species"]}
    assert recent_by_id[species_bird.id]["audio_url"] == "/api/media/species-audio/dash-bird.ogg"
    assert payload["recent_observations"][0]["media"][0]["thumbnail_key"] == "thumbnails/dash-photo.jpg"
    assert payload["fact_of_day"] is not None
    assert payload["challenge"] is not None
    assert payload["community"]["active_observers"] == 2
    assert payload["community"]["leaderboard_period"] == "all"
    assert [leader["display_name"] for leader in payload["community"]["leaders"]] == [
        "Test User",
        "dashboard-other",
        "dashboard-third",
    ]
    assert [leader["total_points"] for leader in payload["community"]["leaders"]] == [
        30,
        15,
        7,
    ]
