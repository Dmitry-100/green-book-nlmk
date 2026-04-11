from datetime import datetime, timedelta, timezone

from geoalchemy2.elements import WKTElement

from app.models.observation import Observation, ObservationStatus, SensitiveLevel
from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.models.user import User, UserRole
from app.routers.gamification import (
    _GAMIFICATION_STATS_BASE_CACHE,
    _GAMIFICATION_STATS_HEATMAP_CACHE,
)


def _reset_gamification_caches() -> None:
    _GAMIFICATION_STATS_BASE_CACHE.invalidate()
    _GAMIFICATION_STATS_HEATMAP_CACHE.invalidate()


def _create_user(db) -> User:
    user = User(
        external_id="stats-user-001",
        display_name="Stats User",
        email="stats-user-001@nlmk.com",
        role=UserRole.employee,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_species(db, *, name_suffix: str, group: SpeciesGroup) -> Species:
    species = Species(
        name_ru=f"Вид {name_suffix}",
        name_latin=f"Species {name_suffix}",
        group=group,
        category=SpeciesCategory.typical,
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
    lat: float,
    lon: float,
    sensitive_level: SensitiveLevel,
    observed_at: datetime,
) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=species_id,
        group=group,
        observed_at=observed_at,
        location_point=WKTElement(f"POINT({lon} {lat})", srid=4326),
        status=ObservationStatus.confirmed,
        comment="stats test",
        is_incident=False,
        sensitive_level=sensitive_level,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_gamification_stats_heatmap_limits_and_sensitivity(client, db):
    _reset_gamification_caches()
    user = _create_user(db)
    open_species = _create_species(db, name_suffix="Open", group=SpeciesGroup.birds)
    blurred_species = _create_species(db, name_suffix="Blurred", group=SpeciesGroup.plants)
    hidden_species = _create_species(db, name_suffix="Hidden", group=SpeciesGroup.insects)

    now = datetime.now(timezone.utc)
    _create_observation(
        db,
        author_id=user.id,
        species_id=open_species.id,
        group=SpeciesGroup.birds.value,
        lat=52.5911,
        lon=39.6011,
        sensitive_level=SensitiveLevel.open,
        observed_at=now - timedelta(minutes=2),
    )
    _create_observation(
        db,
        author_id=user.id,
        species_id=blurred_species.id,
        group=SpeciesGroup.plants.value,
        lat=52.5944,
        lon=39.6044,
        sensitive_level=SensitiveLevel.blurred,
        observed_at=now - timedelta(minutes=1),
    )
    _create_observation(
        db,
        author_id=user.id,
        species_id=hidden_species.id,
        group=SpeciesGroup.insects.value,
        lat=52.5966,
        lon=39.6066,
        sensitive_level=SensitiveLevel.hidden,
        observed_at=now,
    )

    limited_response = client.get("/api/gamification/stats?heatmap_limit=1777")
    assert limited_response.status_code == 200
    assert "private" in limited_response.headers.get("cache-control", "")
    limited_payload = limited_response.json()

    assert limited_payload["heatmap_total"] == 2
    assert limited_payload["heatmap_limited"] is False
    assert len(limited_payload["heatmap"]) == 2
    assert all(point["group"] != SpeciesGroup.insects.value for point in limited_payload["heatmap"])
    assert any(
        point["group"] == SpeciesGroup.plants.value
        and point["lat"] == 52.59
        and point["lon"] == 39.6
        for point in limited_payload["heatmap"]
    )

    truncated_response = client.get("/api/gamification/stats?heatmap_limit=1")
    assert truncated_response.status_code == 200
    truncated_payload = truncated_response.json()
    assert truncated_payload["heatmap_limited"] is True
    assert len(truncated_payload["heatmap"]) == 1


def test_gamification_stats_can_skip_heatmap(client, db):
    _reset_gamification_caches()
    user = _create_user(db)
    species = _create_species(db, name_suffix="NoHeatmap", group=SpeciesGroup.birds)
    now = datetime.now(timezone.utc)
    _create_observation(
        db,
        author_id=user.id,
        species_id=species.id,
        group=SpeciesGroup.birds.value,
        lat=52.5911,
        lon=39.6011,
        sensitive_level=SensitiveLevel.open,
        observed_at=now,
    )

    response = client.get("/api/gamification/stats?include_heatmap=false")
    assert response.status_code == 200
    assert "private" in response.headers.get("cache-control", "")
    payload = response.json()
    assert payload["heatmap"] == []
    assert payload["heatmap_total"] == 0
    assert payload["heatmap_limit"] == 0
    assert payload["heatmap_limited"] is False


def test_gamification_stats_seasonal_dynamics_uses_distinct_species(client, db):
    _reset_gamification_caches()
    user = _create_user(db)
    species_a = _create_species(db, name_suffix="SeasonA", group=SpeciesGroup.birds)
    species_b = _create_species(db, name_suffix="SeasonB", group=SpeciesGroup.mammals)

    _create_observation(
        db,
        author_id=user.id,
        species_id=species_a.id,
        group=SpeciesGroup.birds.value,
        lat=52.5911,
        lon=39.6011,
        sensitive_level=SensitiveLevel.open,
        observed_at=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
    )
    _create_observation(
        db,
        author_id=user.id,
        species_id=species_a.id,
        group=SpeciesGroup.birds.value,
        lat=52.5912,
        lon=39.6012,
        sensitive_level=SensitiveLevel.open,
        observed_at=datetime(2026, 1, 20, 11, 0, tzinfo=timezone.utc),
    )
    _create_observation(
        db,
        author_id=user.id,
        species_id=species_a.id,
        group=SpeciesGroup.birds.value,
        lat=52.5913,
        lon=39.6013,
        sensitive_level=SensitiveLevel.open,
        observed_at=datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc),
    )
    _create_observation(
        db,
        author_id=user.id,
        species_id=species_b.id,
        group=SpeciesGroup.mammals.value,
        lat=52.5914,
        lon=39.6014,
        sensitive_level=SensitiveLevel.open,
        observed_at=datetime(2026, 2, 5, 15, 0, tzinfo=timezone.utc),
    )

    response = client.get("/api/gamification/stats?include_heatmap=false")
    assert response.status_code == 200
    payload = response.json()

    assert payload["confirmed_species"] == 2
    seasonal = {row["month"]: row["species_count"] for row in payload["seasonal_dynamics"]}
    assert seasonal[1] == 1
    assert seasonal[2] == 2
