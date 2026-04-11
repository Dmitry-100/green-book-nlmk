"""Gamification trigger logic. Called when an observation is confirmed."""

from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.models.gamification import (
    Achievement, UserAchievement, UserPoints, SpeciesFirstDiscovery,
)
from app.models.observation import Observation, ObservationStatus, ObsMedia
from app.models.species import Species, SpeciesCategory


def _calc_season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def _calc_points(obs: Observation, species: Species | None, is_first_discovery: bool) -> tuple[int, str]:
    """Calculate points and reason string for this observation."""
    if species is None:
        return 1, "Наблюдение без привязки к виду"

    base = 1
    if species.category == SpeciesCategory.rare:
        base = 5
    elif species.category == SpeciesCategory.red_book:
        base = 10

    multiplier = 1
    reason_parts = [f"{species.name_ru}"]

    if is_first_discovery:
        multiplier = 3
        reason_parts.append("первое наблюдение вида x3")
    elif species.season_info and obs.observed_at:
        month = obs.observed_at.month
        season_info_lower = species.season_info.lower()
        month_names = {
            1: "январ", 2: "феврал", 3: "март", 4: "апрел",
            5: "ма", 6: "июн", 7: "июл", 8: "август",
            9: "сентябр", 10: "октябр", 11: "ноябр", 12: "декабр",
        }
        if month_names.get(month, "") and month_names[month] in season_info_lower:
            multiplier = 2
            reason_parts.append("сезонный бонус x2")

    total = base * multiplier
    reason = ", ".join(reason_parts) + f" ({base}x{multiplier}={total})"
    return total, reason


def _record_first_discovery(obs: Observation, db: Session) -> bool:
    """Record first discovery if this species hasn't been observed before. Returns True if new."""
    if not obs.species_id:
        return False
    existing = db.query(SpeciesFirstDiscovery).filter(
        SpeciesFirstDiscovery.species_id == obs.species_id
    ).first()
    if existing:
        return False
    db.add(SpeciesFirstDiscovery(
        species_id=obs.species_id,
        user_id=obs.author_id,
        observation_id=obs.id,
    ))
    return True


def _check_achievements(user_id: int, obs: Observation, db: Session) -> list[str]:
    """Check all unearned achievements and award any that are now satisfied. Returns list of earned codes."""
    earned_ids = {
        row[0] for row in
        db.query(UserAchievement.achievement_id).filter(UserAchievement.user_id == user_id).all()
    }
    all_achievements = db.query(Achievement).all()
    newly_earned = []

    for ach in all_achievements:
        if ach.id in earned_ids:
            continue

        satisfied = False
        ct = ach.condition_type
        cv = ach.condition_value

        if ct == "obs_count":
            count = db.query(Observation).filter(
                Observation.author_id == user_id,
                Observation.status == ObservationStatus.confirmed,
            ).count()
            satisfied = count >= cv

        elif ct == "group_count":
            groups = db.query(Observation.group).filter(
                Observation.author_id == user_id,
                Observation.status == ObservationStatus.confirmed,
            ).distinct().count()
            satisfied = groups >= cv

        elif ct == "rare_find":
            count = db.query(Observation).join(Species).filter(
                Observation.author_id == user_id,
                Observation.status == ObservationStatus.confirmed,
                Species.category == SpeciesCategory.red_book,
            ).count()
            satisfied = count >= cv

        elif ct == "early_bird":
            if obs.observed_at and obs.observed_at.hour < 7:
                satisfied = True

        elif ct == "night_watch":
            if obs.observed_at and obs.observed_at.hour >= 22:
                satisfied = True

        elif ct == "seasons":
            rows = db.query(extract("month", Observation.observed_at)).filter(
                Observation.author_id == user_id,
                Observation.status == ObservationStatus.confirmed,
            ).distinct().all()
            seasons = {_calc_season(int(r[0])) for r in rows if r[0]}
            satisfied = len(seasons) >= cv

        elif ct == "photo_count":
            count = db.query(Observation).join(ObsMedia).filter(
                Observation.author_id == user_id,
                Observation.status == ObservationStatus.confirmed,
            ).distinct().count()
            satisfied = count >= cv

        elif ct == "incident":
            if obs.is_incident:
                satisfied = True

        elif ct == "first_discovery":
            count = db.query(SpeciesFirstDiscovery).filter(
                SpeciesFirstDiscovery.user_id == user_id
            ).count()
            satisfied = count >= cv

        if satisfied:
            db.add(UserAchievement(user_id=user_id, achievement_id=ach.id))
            # Bonus points for achievement
            if ach.points_reward > 0:
                db.add(UserPoints(
                    user_id=user_id,
                    points=ach.points_reward,
                    reason=f"Достижение «{ach.name}»",
                ))
            newly_earned.append(ach.code)

    return newly_earned


def award_gamification(observation_id: int, db: Session, commit: bool = True) -> dict:
    """Main entry point. Call after observation is confirmed.

    Returns dict with points, is_first_discovery, new_achievements for logging/notification.
    """
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        return {}

    # Idempotency guard: do not award base points for the same observation twice.
    existing_points = (
        db.query(UserPoints)
        .filter(UserPoints.observation_id == observation_id)
        .first()
    )
    if existing_points:
        return {
            "points": existing_points.points,
            "reason": existing_points.reason,
            "is_first_discovery": False,
            "new_achievements": [],
        }

    species = db.query(Species).filter(Species.id == obs.species_id).first() if obs.species_id else None

    # 1. First discovery
    is_first = _record_first_discovery(obs, db)

    # 2. Points
    points, reason = _calc_points(obs, species, is_first)
    db.add(UserPoints(
        user_id=obs.author_id,
        observation_id=obs.id,
        points=points,
        reason=reason,
    ))

    # 3. Achievements
    new_achievements = _check_achievements(obs.author_id, obs, db)

    if commit:
        db.commit()

    return {
        "points": points,
        "reason": reason,
        "is_first_discovery": is_first,
        "new_achievements": new_achievements,
    }
