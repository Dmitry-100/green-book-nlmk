from datetime import datetime, timedelta, timezone

import orjson
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.gamification import (
    Achievement, UserAchievement, UserPoints, SpeciesFirstDiscovery,
)
from app.models.observation import Observation, ObservationStatus, SensitiveLevel
from app.models.species import Species
from app.models.user import User
from app.services.cache import KeyedTTLCache, RedisKeyedTTLCache

router = APIRouter(prefix="/api/gamification", tags=["gamification"])
_GAMIFICATION_STATS_BASE_MEMORY_CACHE = KeyedTTLCache[str, dict](
    settings.gamification_stats_cache_ttl_seconds
)
_GAMIFICATION_STATS_BASE_CACHE = RedisKeyedTTLCache[str, dict](
    redis_url=settings.redis_url,
    key_prefix="cache:gamification:stats:base",
    ttl_seconds=settings.gamification_stats_cache_ttl_seconds,
    fallback_cache=_GAMIFICATION_STATS_BASE_MEMORY_CACHE,
    enabled=settings.redis_cache_enabled,
    namespace=settings.redis_cache_namespace,
)
_GAMIFICATION_STATS_HEATMAP_MEMORY_CACHE = KeyedTTLCache[int, dict](
    settings.gamification_stats_cache_ttl_seconds,
    max_entries=64,
)
_GAMIFICATION_STATS_HEATMAP_CACHE = RedisKeyedTTLCache[int, dict](
    redis_url=settings.redis_url,
    key_prefix="cache:gamification:stats:heatmap",
    ttl_seconds=settings.gamification_stats_cache_ttl_seconds,
    fallback_cache=_GAMIFICATION_STATS_HEATMAP_MEMORY_CACHE,
    enabled=settings.redis_cache_enabled,
    namespace=settings.redis_cache_namespace,
)


@router.get("/leaderboard")
def leaderboard(
    period: str = Query("all", pattern="^(all|month|quarter|year)$"),
    db: Session = Depends(get_db),
):
    """Top observers by points, optionally filtered by period."""
    query = db.query(
        UserPoints.user_id,
        User.display_name,
        func.sum(UserPoints.points).label("total_points"),
    ).join(User, User.id == UserPoints.user_id)

    if period == "month":
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        query = query.filter(UserPoints.created_at >= cutoff)
    elif period == "quarter":
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        query = query.filter(UserPoints.created_at >= cutoff)
    elif period == "year":
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        query = query.filter(UserPoints.created_at >= cutoff)

    query = query.group_by(UserPoints.user_id, User.display_name).order_by(
        func.sum(UserPoints.points).desc()
    ).limit(20)

    results = query.all()
    leaders = [
        {
            "user_id": user_id,
            "display_name": display_name,
            "total_points": total,
        }
        for user_id, display_name, total in results
    ]
    return {"leaders": leaders, "period": period}


@router.get("/profile")
def my_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Current user's gamification profile."""
    total_points = db.query(func.sum(UserPoints.points)).filter(
        UserPoints.user_id == user.id
    ).scalar() or 0

    obs_count = db.query(Observation).filter(
        Observation.author_id == user.id,
        Observation.status == ObservationStatus.confirmed,
    ).count()

    achievements = db.query(Achievement).join(UserAchievement).filter(
        UserAchievement.user_id == user.id
    ).all()

    discoveries = db.query(SpeciesFirstDiscovery).filter(
        SpeciesFirstDiscovery.user_id == user.id
    ).count()

    # Species collection: unique confirmed species
    species_ids = db.query(Observation.species_id).filter(
        Observation.author_id == user.id,
        Observation.status == ObservationStatus.confirmed,
        Observation.species_id.is_not(None),
    ).distinct().all()

    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "total_points": total_points,
        "confirmed_observations": obs_count,
        "first_discoveries": discoveries,
        "species_collected": len(species_ids),
        "achievements": [
            {"code": a.code, "name": a.name, "icon": a.icon, "description": a.description}
            for a in achievements
        ],
    }


@router.get("/species/{species_id}/discoverer")
def species_discoverer(species_id: int, db: Session = Depends(get_db)):
    """Who first discovered this species."""
    discovery = (
        db.query(SpeciesFirstDiscovery.discovered_at, User.display_name)
        .outerjoin(User, User.id == SpeciesFirstDiscovery.user_id)
        .filter(SpeciesFirstDiscovery.species_id == species_id)
        .first()
    )
    if discovery is None:
        return {"discoverer": None}
    discovered_at, display_name = discovery
    return {
        "discoverer": {
            "display_name": display_name or "Unknown",
            "discovered_at": discovered_at.isoformat(),
        }
    }


def _build_biodiversity_base_payload(db: Session) -> dict:
    """Ecological passport aggregate stats (without heatmap)."""
    import math
    from sqlalchemy import extract

    total_species = db.query(Species).count()

    by_group = db.query(Species.group, func.count(Species.id)).group_by(Species.group).all()

    total_obs = (
        db.query(Observation)
        .filter(Observation.status == ObservationStatus.confirmed)
        .count()
    )

    species_counts: list[tuple[int, int]] = []
    confirmed_species = 0
    # Shannon Diversity Index
    shannon_index = 0.0
    if total_obs > 0:
        species_counts = (
            db.query(Observation.species_id, func.count(Observation.id))
            .filter(
                Observation.status == ObservationStatus.confirmed,
                Observation.species_id.is_not(None),
            )
            .group_by(Observation.species_id)
            .all()
        )
        confirmed_species = len(species_counts)
        for _, count in species_counts:
            pi = count / total_obs
            if pi > 0:
                shannon_index -= pi * math.log(pi)

    seasonal_data: list[dict] = []
    if confirmed_species > 0:
        month_expr = extract("month", Observation.observed_at)
        seasonal_pairs_subquery = (
            db.query(
                month_expr.label("month"),
                Observation.species_id.label("species_id"),
            )
            .filter(
                Observation.status == ObservationStatus.confirmed,
                Observation.species_id.is_not(None),
            )
            .group_by(month_expr, Observation.species_id)
            .subquery()
        )
        seasonal = (
            db.query(
                seasonal_pairs_subquery.c.month,
                func.count().label("species_count"),
            )
            .group_by(seasonal_pairs_subquery.c.month)
            .order_by(seasonal_pairs_subquery.c.month)
            .all()
        )
        seasonal_data = [
            {"month": int(month), "species_count": count}
            for month, count in seasonal
        ]

    return {
        "total_species_in_catalog": total_species,
        "confirmed_species": confirmed_species,
        "total_confirmed_observations": total_obs,
        "species_by_group": {
            group.value if hasattr(group, "value") else str(group): count
            for group, count in by_group
        },
        "biodiversity_coverage": (
            round(confirmed_species / total_species * 100, 1) if total_species else 0
        ),
        "shannon_index": round(shannon_index, 3),
        "seasonal_dynamics": seasonal_data,
    }


def _build_biodiversity_heatmap_payload(db: Session, *, heatmap_limit: int) -> dict:
    """Heatmap payload with bounded points and sensitivity controls."""
    from geoalchemy2.functions import ST_X, ST_Y

    visible_filter = Observation.sensitive_level.in_(
        [SensitiveLevel.open, SensitiveLevel.blurred]
    )
    heatmap_total = (
        db.query(Observation.id)
        .filter(
            Observation.status == ObservationStatus.confirmed,
            visible_filter,
        )
        .count()
    )
    if heatmap_total == 0:
        return {
            "heatmap": [],
            "heatmap_total": 0,
            "heatmap_limit": heatmap_limit,
            "heatmap_limited": False,
        }

    heatmap_rows = (
        db.query(
            ST_Y(Observation.location_point).label("lat"),
            ST_X(Observation.location_point).label("lon"),
            Observation.group,
            Observation.sensitive_level,
        )
        .filter(
            Observation.status == ObservationStatus.confirmed,
            visible_filter,
        )
        .order_by(Observation.observed_at.desc())
        .limit(heatmap_limit)
        .all()
    )

    heatmap: list[dict] = []
    for row in heatmap_rows:
        lat = float(row.lat)
        lon = float(row.lon)
        if row.sensitive_level == SensitiveLevel.blurred:
            lat = round(lat, 2)
            lon = round(lon, 2)
        heatmap.append({"lat": lat, "lon": lon, "group": row.group})

    return {
        "heatmap": heatmap,
        "heatmap_total": heatmap_total,
        "heatmap_limit": heatmap_limit,
        "heatmap_limited": heatmap_total > len(heatmap),
    }


@router.get("/stats")
def biodiversity_stats(
    include_heatmap: bool = Query(default=True),
    heatmap_limit: int = Query(default=1500, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    if settings.gamification_stats_cache_ttl_seconds > 0:
        base_payload = _GAMIFICATION_STATS_BASE_CACHE.get_or_set(
            "base",
            lambda: _build_biodiversity_base_payload(db),
        )
    else:
        base_payload = _build_biodiversity_base_payload(db)

    if include_heatmap:
        if settings.gamification_stats_cache_ttl_seconds > 0:
            heatmap_payload = _GAMIFICATION_STATS_HEATMAP_CACHE.get_or_set(
                heatmap_limit,
                lambda: _build_biodiversity_heatmap_payload(
                    db,
                    heatmap_limit=heatmap_limit,
                ),
            )
        else:
            heatmap_payload = _build_biodiversity_heatmap_payload(
                db,
                heatmap_limit=heatmap_limit,
            )
    else:
        heatmap_payload = {
            "heatmap": [],
            "heatmap_total": 0,
            "heatmap_limit": 0,
            "heatmap_limited": False,
        }

    payload = {**base_payload, **heatmap_payload}
    return Response(
        content=orjson.dumps(payload),
        media_type="application/json",
        headers={
            "Cache-Control": (
                f"private, max-age={settings.gamification_stats_cache_ttl_seconds}"
            )
        },
    )


@router.get("/fact-of-day")
def fact_of_day(db: Session = Depends(get_db)):
    """Random interesting species fact."""
    eligible_species_query = (
        db.query(Species)
        .filter(Species.description.is_not(None), Species.description != "")
        .order_by(Species.id.asc())
    )
    eligible_count = eligible_species_query.count()
    if eligible_count == 0:
        return {"fact": None}

    day_index = datetime.now(timezone.utc).timetuple().tm_yday % eligible_count
    species = eligible_species_query.offset(day_index).limit(1).first()
    if not species:
        return {"fact": None}
    return {
        "species_id": species.id,
        "name_ru": species.name_ru,
        "name_latin": species.name_latin,
        "description": species.description,
        "photo_url": species.photo_urls[0] if species.photo_urls else None,
        "is_poisonous": species.is_poisonous,
        "conservation_status": species.conservation_status,
    }


@router.get("/challenge")
def monthly_challenge(db: Session = Depends(get_db)):
    """Current month's species challenge. First to find it gets a special badge."""
    now = datetime.now(timezone.utc)
    month = now.month
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        month_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        month_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

    eligible_species_query = (
        db.query(Species)
        .filter(
            Species.photo_urls.is_not(None),
            func.array_length(Species.photo_urls, 1) > 0,
            Species.conservation_status.is_not(None),
        )
        .order_by(Species.id.asc())
    )
    eligible_count = eligible_species_query.count()
    if eligible_count == 0:
        return {"challenge": None}

    target = eligible_species_query.offset(month % eligible_count).limit(1).first()
    if target is None:
        return {"challenge": None}

    # Check if anyone found it this month
    found = (
        db.query(Observation, User.display_name)
        .outerjoin(User, User.id == Observation.author_id)
        .filter(
            Observation.species_id == target.id,
            Observation.status == ObservationStatus.confirmed,
            Observation.observed_at >= month_start,
            Observation.observed_at < month_end,
        )
        .first()
    )

    finder = None
    if found is not None:
        found_obs, finder_name = found
        finder = {
            "display_name": finder_name or "Unknown",
            "found_at": found_obs.observed_at.isoformat(),
        }

    month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

    return {
        "month": month_names[month - 1],
        "year": now.year,
        "species": {
            "id": target.id,
            "name_ru": target.name_ru,
            "name_latin": target.name_latin,
            "photo_url": target.photo_urls[0] if target.photo_urls else None,
            "conservation_status": target.conservation_status,
        },
        "found": found is not None,
        "finder": finder,
    }


@router.get("/quiz")
def quiz_question(db: Session = Depends(get_db)):
    """Generate a quiz question: show a photo, guess the species name."""
    # Pick a random species that has a photo
    correct = db.query(Species).filter(
        Species.photo_urls.is_not(None),
        func.array_length(Species.photo_urls, 1) > 0,
    ).order_by(func.random()).first()

    if not correct:
        return {"question": None}

    # Pick 3 wrong answers from same group
    wrong = db.query(Species).filter(
        Species.id != correct.id,
        Species.group == correct.group,
    ).order_by(func.random()).limit(3).all()

    # If not enough from same group, fill from others
    if len(wrong) < 3:
        extra = db.query(Species).filter(
            Species.id != correct.id,
            Species.id.not_in([w.id for w in wrong]),
        ).order_by(func.random()).limit(3 - len(wrong)).all()
        wrong.extend(extra)

    import random
    options = [{"id": correct.id, "name_ru": correct.name_ru, "name_latin": correct.name_latin}]
    for w in wrong:
        options.append({"id": w.id, "name_ru": w.name_ru, "name_latin": w.name_latin})
    random.shuffle(options)

    return {
        "photo_url": correct.photo_urls[0] if correct.photo_urls else None,
        "correct_id": correct.id,
        "group": correct.group,
        "options": options,
    }
