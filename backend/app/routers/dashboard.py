from datetime import datetime, timezone

import orjson
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.auth import get_optional_user
from app.config import settings
from app.database import get_db
from app.models.observation import Observation, ObservationStatus
from app.models.species import Species
from app.models.user import User, UserRole
from app.services.cache import KeyedTTLCache, RedisKeyedTTLCache

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
_DASHBOARD_SUMMARY_MEMORY_CACHE = KeyedTTLCache[str, dict](
    settings.dashboard_summary_cache_ttl_seconds,
    max_entries=8,
)
_DASHBOARD_SUMMARY_CACHE = RedisKeyedTTLCache[str, dict](
    redis_url=settings.redis_url,
    key_prefix="cache:dashboard:summary",
    ttl_seconds=settings.dashboard_summary_cache_ttl_seconds,
    fallback_cache=_DASHBOARD_SUMMARY_MEMORY_CACHE,
    enabled=settings.redis_cache_enabled,
    namespace=settings.redis_cache_namespace,
)


def _build_fact_of_day(db: Session) -> dict | None:
    eligible_species_query = (
        db.query(Species)
        .filter(
            Species.description.is_not(None),
            Species.description != "",
        )
        .order_by(Species.id.asc())
    )
    eligible_count = eligible_species_query.count()
    if eligible_count == 0:
        return None

    now = datetime.now(timezone.utc)
    day_index = now.timetuple().tm_yday % eligible_count
    fact_species = eligible_species_query.offset(day_index).limit(1).first()
    if fact_species is None:
        return None

    return {
        "species_id": fact_species.id,
        "name_ru": fact_species.name_ru,
        "name_latin": fact_species.name_latin,
        "description": fact_species.description,
        "photo_url": fact_species.photo_urls[0] if fact_species.photo_urls else None,
        "is_poisonous": fact_species.is_poisonous,
        "conservation_status": fact_species.conservation_status,
    }


def _build_monthly_challenge(db: Session) -> dict | None:
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
        return None

    month_index = month % eligible_count
    target_species = eligible_species_query.offset(month_index).limit(1).first()
    if target_species is None:
        return None

    found_observation = (
        db.query(Observation, User.display_name)
        .outerjoin(User, User.id == Observation.author_id)
        .filter(
            Observation.species_id == target_species.id,
            Observation.status == ObservationStatus.confirmed,
            Observation.observed_at >= month_start,
            Observation.observed_at < month_end,
        )
        .first()
    )

    finder = None
    found = False
    if found_observation:
        observation_row, finder_name = found_observation
        found = True
        finder = {
            "display_name": finder_name or "Unknown",
            "found_at": observation_row.observed_at.isoformat(),
        }

    month_names = [
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ]

    return {
        "month": month_names[month - 1],
        "year": now.year,
        "species": {
            "id": target_species.id,
            "name_ru": target_species.name_ru,
            "name_latin": target_species.name_latin,
            "photo_url": target_species.photo_urls[0] if target_species.photo_urls else None,
            "conservation_status": target_species.conservation_status,
        },
        "found": found,
        "finder": finder,
    }


def _build_summary_payload(db: Session) -> dict:
    species_total = db.query(func.count(Species.id)).scalar() or 0
    species_by_group_rows = (
        db.query(Species.group, func.count(Species.id))
        .group_by(Species.group)
        .all()
    )
    species_by_group = {
        (group.value if hasattr(group, "value") else str(group)): count
        for group, count in species_by_group_rows
    }

    recent_species_rows = (
        db.query(Species)
        .order_by(Species.updated_at.desc(), Species.id.desc())
        .limit(8)
        .all()
    )
    recent_species = [
        {
            "id": species.id,
            "name_ru": species.name_ru,
            "name_latin": species.name_latin,
            "group": species.group.value if species.group else None,
            "category": species.category.value if species.category else None,
            "is_poisonous": species.is_poisonous,
            "photo_urls": species.photo_urls or [],
        }
        for species in recent_species_rows
    ]

    total_observations = db.query(func.count(Observation.id)).scalar() or 0
    confirmed_total = (
        db.query(func.count(Observation.id))
        .filter(Observation.status == ObservationStatus.confirmed)
        .scalar()
        or 0
    )
    recent_observations_rows = (
        db.query(Observation)
        .options(selectinload(Observation.media))
        .filter(Observation.status == ObservationStatus.confirmed)
        .order_by(Observation.created_at.desc())
        .limit(5)
        .all()
    )
    recent_observations = [
        {
            "id": observation.id,
            "group": observation.group,
            "status": observation.status.value if observation.status else None,
            "comment": observation.comment,
            "observed_at": observation.observed_at.isoformat() if observation.observed_at else None,
            "media": [
                {
                    "id": media.id,
                    "s3_key": media.s3_key,
                    "thumbnail_key": media.thumbnail_key,
                    "mime_type": media.mime_type,
                }
                for media in observation.media
            ],
        }
        for observation in recent_observations_rows
    ]

    return {
        "species_total": species_total,
        "total_observations": total_observations,
        "confirmed_total": confirmed_total,
        "species_by_group": species_by_group,
        "recent_species": recent_species,
        "recent_observations": recent_observations,
        "fact_of_day": _build_fact_of_day(db),
        "challenge": _build_monthly_challenge(db),
    }


@router.get("/summary")
def dashboard_summary(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if settings.dashboard_summary_cache_ttl_seconds > 0:
        common_payload = _DASHBOARD_SUMMARY_CACHE.get_or_set(
            "summary",
            lambda: _build_summary_payload(db),
        )
    else:
        common_payload = _build_summary_payload(db)

    my_on_review = 0
    if user is not None:
        my_on_review = (
            db.query(func.count(Observation.id))
            .filter(
                Observation.author_id == user.id,
                Observation.status == ObservationStatus.on_review,
            )
            .scalar()
            or 0
        )

    if user is not None and user.role in (UserRole.ecologist, UserRole.admin):
        visible_total = common_payload["total_observations"]
    else:
        visible_total = common_payload["confirmed_total"]

    payload = {
        "stats": {
            "species": common_payload["species_total"],
            "confirmed": common_payload["confirmed_total"],
            "on_review": my_on_review,
            "total_obs": visible_total,
        },
        "species_by_group": common_payload["species_by_group"],
        "recent_species": common_payload["recent_species"],
        "recent_observations": common_payload["recent_observations"],
        "fact_of_day": common_payload["fact_of_day"],
        "challenge": common_payload["challenge"],
    }
    return Response(
        content=orjson.dumps(payload),
        media_type="application/json",
        headers={
            "Cache-Control": (
                f"private, max-age={settings.dashboard_summary_cache_ttl_seconds}"
            )
        },
    )
