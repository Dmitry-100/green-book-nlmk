from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement

from app.models.gamification import SpeciesFirstDiscovery, UserPoints
from app.models.observation import Observation, ObservationStatus
from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.models.user import User, UserRole
from app.services.gamification import award_gamification


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


def _create_species(
    db,
    *,
    latin: str,
    category: SpeciesCategory,
    season_info: str | None = None,
) -> Species:
    species = Species(
        name_ru=f"Species {latin}",
        name_latin=latin,
        group=SpeciesGroup.birds,
        category=category,
        season_info=season_info,
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
    observed_at: datetime,
    status: ObservationStatus = ObservationStatus.confirmed,
) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=species_id,
        group=SpeciesGroup.birds.value,
        observed_at=observed_at,
        location_point=WKTElement("POINT(39.60 52.59)", srid=4326),
        status=status,
        comment="gamification test",
        is_incident=False,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_award_gamification_first_discovery_multiplier(db):
    user = _create_user(db, external_id="gm-user-001", email="gm-user-001@nlmk.com")
    species = _create_species(
        db,
        latin="GmRedBook",
        category=SpeciesCategory.red_book,
    )
    obs = _create_observation(
        db,
        author_id=user.id,
        species_id=species.id,
        observed_at=datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc),
    )

    result = award_gamification(obs.id, db)

    assert result["is_first_discovery"] is True
    assert result["points"] == 30
    assert "x3" in result["reason"]
    assert (
        db.query(SpeciesFirstDiscovery)
        .filter(SpeciesFirstDiscovery.species_id == species.id)
        .count()
        == 1
    )


def test_award_gamification_applies_season_bonus_when_not_first(db):
    initial_user = _create_user(db, external_id="gm-user-002", email="gm-user-002@nlmk.com")
    target_user = _create_user(db, external_id="gm-user-003", email="gm-user-003@nlmk.com")
    species = _create_species(
        db,
        latin="GmRare",
        category=SpeciesCategory.rare,
        season_info="апрель-май",
    )
    first_obs = _create_observation(
        db,
        author_id=initial_user.id,
        species_id=species.id,
        observed_at=datetime(2026, 3, 15, 9, 0, tzinfo=timezone.utc),
    )
    db.add(
        SpeciesFirstDiscovery(
            species_id=species.id,
            user_id=initial_user.id,
            observation_id=first_obs.id,
        )
    )
    db.commit()

    target_obs = _create_observation(
        db,
        author_id=target_user.id,
        species_id=species.id,
        observed_at=datetime(2026, 4, 20, 8, 30, tzinfo=timezone.utc),
    )
    result = award_gamification(target_obs.id, db)

    assert result["is_first_discovery"] is False
    assert result["points"] == 10
    assert "сезонный бонус x2" in result["reason"]


def test_award_gamification_is_idempotent(db):
    user = _create_user(db, external_id="gm-user-004", email="gm-user-004@nlmk.com")
    species = _create_species(
        db,
        latin="GmIdempotent",
        category=SpeciesCategory.typical,
    )
    obs = _create_observation(
        db,
        author_id=user.id,
        species_id=species.id,
        observed_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
    )

    first = award_gamification(obs.id, db)
    second = award_gamification(obs.id, db)

    assert first["points"] == second["points"]
    assert (
        db.query(UserPoints)
        .filter(UserPoints.observation_id == obs.id)
        .count()
        == 1
    )
