from datetime import datetime, timedelta, timezone

from geoalchemy2.elements import WKTElement

from app.models.gamification import (
    Achievement,
    SpeciesFirstDiscovery,
    UserAchievement,
    UserPoints,
)
from app.models.observation import Observation, ObservationStatus, SensitiveLevel
from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.models.user import User, UserRole
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


def _create_species(
    db,
    *,
    suffix: str,
    group: SpeciesGroup = SpeciesGroup.birds,
    with_description: bool = True,
    with_photo: bool = True,
    with_conservation_status: bool = True,
) -> Species:
    species = Species(
        name_ru=f"Species {suffix}",
        name_latin=f"Species {suffix} latin",
        group=group,
        category=SpeciesCategory.typical,
        conservation_status="LC" if with_conservation_status else None,
        description=f"Description {suffix}" if with_description else None,
        photo_urls=[f"/api/media/species/{suffix}.jpg"] if with_photo else [],
    )
    db.add(species)
    db.commit()
    db.refresh(species)
    return species


def _create_observation(
    db,
    *,
    author_id: int,
    species_id: int,
    group: str,
    status: ObservationStatus = ObservationStatus.confirmed,
    observed_at: datetime | None = None,
) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=species_id,
        group=group,
        observed_at=observed_at or datetime.now(timezone.utc),
        location_point=WKTElement("POINT(39.60 52.59)", srid=4326),
        status=status,
        comment="gamification endpoint test",
        is_incident=False,
        sensitive_level=SensitiveLevel.open,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_leaderboard_filters_by_period(client, db):
    now = datetime.now(timezone.utc)
    recent_user = _create_user(db, external_id="gm-leader-recent")
    old_user = _create_user(db, external_id="gm-leader-old")

    db.add_all(
        [
            UserPoints(
                user_id=recent_user.id,
                observation_id=None,
                points=12,
                reason="recent points",
                created_at=now - timedelta(days=5),
            ),
            UserPoints(
                user_id=old_user.id,
                observation_id=None,
                points=50,
                reason="old points",
                created_at=now - timedelta(days=120),
            ),
        ]
    )
    db.commit()

    month_response = client.get("/api/gamification/leaderboard?period=month")
    assert month_response.status_code == 200
    month_payload = month_response.json()
    assert month_payload["period"] == "month"
    assert [leader["display_name"] for leader in month_payload["leaders"]] == [
        recent_user.display_name
    ]

    all_response = client.get("/api/gamification/leaderboard?period=all")
    assert all_response.status_code == 200
    all_payload = all_response.json()
    assert [leader["display_name"] for leader in all_payload["leaders"]] == [
        old_user.display_name,
        recent_user.display_name,
    ]


def test_profile_aggregates_points_achievements_and_discoveries(client, db):
    user = _create_user(db, external_id="test-user-001")
    species_primary = _create_species(db, suffix="ProfileA", group=SpeciesGroup.birds)
    species_secondary = _create_species(db, suffix="ProfileB", group=SpeciesGroup.plants)
    obs_primary = _create_observation(
        db,
        author_id=user.id,
        species_id=species_primary.id,
        group=SpeciesGroup.birds.value,
    )
    _create_observation(
        db,
        author_id=user.id,
        species_id=species_secondary.id,
        group=SpeciesGroup.plants.value,
    )

    db.add_all(
        [
            UserPoints(
                user_id=user.id,
                observation_id=obs_primary.id,
                points=10,
                reason="points A",
            ),
            UserPoints(
                user_id=user.id,
                observation_id=None,
                points=5,
                reason="points B",
            ),
        ]
    )
    achievement = Achievement(
        code="profile-achievement",
        name="Profile Achievement",
        description="Profile test achievement",
        icon="🏅",
        points_reward=25,
        condition_type="obs_count",
        condition_value=1,
    )
    db.add(achievement)
    db.commit()
    db.refresh(achievement)
    db.add(UserAchievement(user_id=user.id, achievement_id=achievement.id))
    db.add(
        SpeciesFirstDiscovery(
            species_id=species_primary.id,
            user_id=user.id,
            observation_id=obs_primary.id,
        )
    )
    db.commit()

    token = make_token(
        external_id=user.external_id,
        name=user.display_name,
        email=user.email,
        role=user.role.value,
    )
    response = client.get(
        "/api/gamification/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == user.id
    assert payload["total_points"] == 15
    assert payload["confirmed_observations"] == 2
    assert payload["first_discoveries"] == 1
    assert payload["species_collected"] == 2
    assert payload["achievements"][0]["code"] == "profile-achievement"


def test_species_discoverer_returns_none_and_discoverer_payload(client, db):
    species = _create_species(db, suffix="Discoverer", group=SpeciesGroup.mammals)
    none_response = client.get(f"/api/gamification/species/{species.id}/discoverer")
    assert none_response.status_code == 200
    assert none_response.json() == {"discoverer": None}

    user = _create_user(db, external_id="gm-discoverer-user")
    obs = _create_observation(
        db,
        author_id=user.id,
        species_id=species.id,
        group=SpeciesGroup.mammals.value,
    )
    db.add(
        SpeciesFirstDiscovery(
            species_id=species.id,
            user_id=user.id,
            observation_id=obs.id,
        )
    )
    db.commit()

    response = client.get(f"/api/gamification/species/{species.id}/discoverer")
    assert response.status_code == 200
    payload = response.json()
    assert payload["discoverer"] is not None
    assert payload["discoverer"]["display_name"] == user.display_name
    assert payload["discoverer"]["discovered_at"]


def test_fact_of_day_handles_empty_and_single_eligible_species(client, db):
    empty_species = _create_species(
        db,
        suffix="NoDescription",
        with_description=False,
    )
    response_empty = client.get("/api/gamification/fact-of-day")
    assert response_empty.status_code == 200
    assert response_empty.json() == {"fact": None}

    fact_species = _create_species(
        db,
        suffix="FactOne",
        group=SpeciesGroup.fungi,
    )
    response = client.get("/api/gamification/fact-of-day")
    assert response.status_code == 200
    payload = response.json()
    assert payload["species_id"] == fact_species.id
    assert payload["name_ru"] == fact_species.name_ru
    assert payload["description"] == fact_species.description
    assert payload["photo_url"] == fact_species.photo_urls[0]

    assert empty_species.id != fact_species.id


def test_monthly_challenge_handles_empty_and_found_paths(client, db):
    no_challenge_species = _create_species(
        db,
        suffix="NoChallenge",
        with_photo=False,
        with_conservation_status=False,
    )
    no_challenge_response = client.get("/api/gamification/challenge")
    assert no_challenge_response.status_code == 200
    assert no_challenge_response.json() == {"challenge": None}

    user = _create_user(db, external_id="gm-challenge-user")
    target_species = _create_species(
        db,
        suffix="ChallengeTarget",
        group=SpeciesGroup.birds,
        with_photo=True,
        with_conservation_status=True,
    )
    _create_observation(
        db,
        author_id=user.id,
        species_id=target_species.id,
        group=SpeciesGroup.birds.value,
        observed_at=datetime.now(timezone.utc),
    )

    response = client.get("/api/gamification/challenge")
    assert response.status_code == 200
    payload = response.json()
    assert payload["species"]["id"] == target_species.id
    assert payload["found"] is True
    assert payload["finder"] is not None
    assert payload["finder"]["display_name"] == user.display_name

    assert no_challenge_species.id != target_species.id


def test_quiz_returns_null_without_photos_and_valid_question_with_candidates(client, db):
    _create_species(
        db,
        suffix="QuizNoPhoto",
        group=SpeciesGroup.insects,
        with_photo=False,
    )
    empty_response = client.get("/api/gamification/quiz")
    assert empty_response.status_code == 200
    assert empty_response.json() == {"question": None}

    species_rows = [
        _create_species(db, suffix="QuizA", group=SpeciesGroup.herpetofauna, with_photo=True),
        _create_species(db, suffix="QuizB", group=SpeciesGroup.herpetofauna, with_photo=True),
        _create_species(db, suffix="QuizC", group=SpeciesGroup.herpetofauna, with_photo=True),
        _create_species(db, suffix="QuizD", group=SpeciesGroup.herpetofauna, with_photo=True),
    ]
    response = client.get("/api/gamification/quiz")
    assert response.status_code == 200
    payload = response.json()
    option_ids = [option["id"] for option in payload["options"]]

    assert payload["photo_url"] is not None
    assert payload["group"] == SpeciesGroup.herpetofauna.value
    assert payload["correct_id"] in option_ids
    assert len(option_ids) == 4
    assert len(set(option_ids)) == 4
    assert set(option_ids).issubset({species.id for species in species_rows})
